import os
import time
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.document import Document
from backend.app.models.verification import AuthoritySource, MockRegisterEntry
from backend.app.services.verification.adapters.base import VerificationAdapter, AdapterRegistry
from backend.app.services.verification.schemas import VerificationResultDTO, VerificationStatus
from backend.app.services.verification.comparator import VerificationComparator
from backend.app.services.verification.circuit_breaker import (
    execute_with_resilience,
    CircuitBreakerOpenException,
    SourceUnavailableException,
)

SIMULATED_SOURCE_LABEL = "SIMULATED SOURCE - replace with the authorised integration"


@AdapterRegistry.register("API")
@AdapterRegistry.register("PORTAL")
class APIVerificationAdapter(VerificationAdapter):
    """
    Adapter for querying external authority APIs or official registers.
    Queries issuing authorities (NBA, NAAC, Fire Dept, Pollution Board, Municipal Corp).
    Enforces AuthoritySource configuration, environment credentials only,
    timeouts, 3 retries with backoff, and circuit breaker protection.
    Clearly labels mock sources with SIMULATED SOURCE disclaimer.
    """

    def _resolve_authority_key(self, document: Document) -> str:
        dt = document.document_type
        code = (document.document_type_code or (dt.code if dt else "")).upper()
        authority = (dt.issuing_authority if dt and dt.issuing_authority else "").upper()

        if "NBA" in code or "NBA" in authority:
            return "NBA"
        if "NAAC" in code or "NAAC" in authority:
            return "NAAC"
        if "FIRE" in code or "FIRE" in authority:
            return "FIRE_DEPT"
        if "POLLUTION" in code or "POLLUTION" in authority:
            return "POLLUTION_BOARD"
        if "OCCUPANCY" in code or "BUILDING" in code or "MUNICIPAL" in authority or "TOWN" in authority:
            return "MUNICIPAL_CORP"

        return code or "GENERAL_AUTHORITY"

    def _resolve_authority_source(self, db: Session, authority_key: str) -> Optional[AuthoritySource]:
        # Exact match
        source = (
            db.query(AuthoritySource)
            .filter(func.upper(AuthoritySource.name) == authority_key.upper())
            .first()
        )
        if source:
            return source

        # Partial / fuzzy match on name
        all_sources = db.query(AuthoritySource).all()
        for s in all_sources:
            norm_name = s.name.upper().replace(" ", "_").replace("-", "_")
            if authority_key in norm_name or norm_name in authority_key:
                return s
        return None

    def verify(
        self,
        document: Document,
        extracted_fields: Dict[str, Any],
        db: Session,
    ) -> VerificationResultDTO:
        authority_key = self._resolve_authority_key(document)
        source = self._resolve_authority_source(db, authority_key)

        # 1. Check AuthoritySource configuration and enabled flag
        if not source or not source.enabled:
            return VerificationResultDTO(
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                source_name=authority_key,
                source_ref=f"DOC-{document.id}",
                message=f"Authority source '{authority_key}' is not configured or is currently disabled. Routing to manual review.",
                details={
                    "authority": authority_key,
                    "configured": bool(source),
                    "enabled": bool(source.enabled) if source else False,
                    "disclaimer": SIMULATED_SOURCE_LABEL,
                },
            )

        # 2. Extract certificate number
        sub_cert = VerificationComparator.extract_cert_number_from_fields(extracted_fields)
        if not sub_cert:
            return VerificationResultDTO(
                status=VerificationStatus.MISMATCH_DETECTED,
                source_name=source.name,
                source_ref=f"DOC-{document.id}",
                message="No certificate number could be extracted from submitted document to query authority.",
                mismatched_fields=[{
                    "field": "certificate_number",
                    "submitted": None,
                    "official": "REQUIRED",
                }],
                details={"disclaimer": SIMULATED_SOURCE_LABEL},
            )

        # 3. Resolve credentials from env ONLY
        secret_key = None
        if source.env_secret_key:
            secret_key = os.environ.get(source.env_secret_key)

        headers = {
            "User-Agent": "AICTE-SmartVerify-Core/1.0",
        }
        if source.auth_type == "BEARER" and secret_key:
            headers["Authorization"] = f"Bearer {secret_key}"
        elif source.auth_type == "API_KEY" and secret_key:
            headers["X-API-Key"] = secret_key

        # 4. Construct URL
        base_url = source.base_url.rstrip("/")
        if not base_url.endswith("/verify"):
            endpoint_url = f"{base_url}/{authority_key.lower()}/verify"
        else:
            endpoint_url = base_url

        # Check for test override simulation params in extracted_fields
        sim_error = extracted_fields.get("_simulate_error")

        # 5. Execute with 3 Retries + Backoff + Circuit Breaker
        is_mock_service = endpoint_url.startswith("/") or "mock-authorities" in endpoint_url

        def perform_call():
            if sim_error == "503" or sim_error == "unavailable":
                raise SourceUnavailableException(f"{SIMULATED_SOURCE_LABEL}: Service temporarily unavailable (503).")
            if sim_error == "timeout":
                time.sleep(0.01)
                raise SourceUnavailableException(f"{SIMULATED_SOURCE_LABEL}: Gateway Timeout (504).")

            if is_mock_service:
                from backend.app.api.v1.mock_authorities import _normalize_authority
                auth_key = _normalize_authority(authority_key)
                clean_cert = VerificationComparator.normalize_cert_number(sub_cert)

                entries = db.query(MockRegisterEntry).filter(MockRegisterEntry.authority == auth_key).all()
                matched = None
                for entry in entries:
                    if VerificationComparator.normalize_cert_number(entry.certificate_number) == clean_cert:
                        matched = entry
                        break

                if not matched:
                    # Fallback search
                    all_e = db.query(MockRegisterEntry).all()
                    for entry in all_e:
                        if VerificationComparator.normalize_cert_number(entry.certificate_number) == clean_cert:
                            matched = entry
                            break

                if not matched:
                    return {
                        "status_code": 404,
                        "data": {
                            "status": "NOT_FOUND",
                            "message": f"Certificate '{sub_cert}' not found in official {auth_key} register.",
                            "disclaimer": SIMULATED_SOURCE_LABEL,
                        },
                        "content": json.dumps({"status": "NOT_FOUND"}).encode("utf-8"),
                    }

                record_data = {
                    "certificate_number": matched.certificate_number,
                    "institute_name": matched.institute_name,
                    "issue_date": matched.issue_date,
                    "expiry_date": matched.expiry_date,
                    "status": matched.status,
                    "details": matched.data_json or {},
                }
                full_body = {
                    "authority": auth_key,
                    "disclaimer": SIMULATED_SOURCE_LABEL,
                    "status": "FOUND",
                    "record": record_data,
                }
                return {
                    "status_code": 200,
                    "data": full_body,
                    "content": json.dumps(full_body).encode("utf-8"),
                }
            else:
                import httpx
                params = {"certificate_number": sub_cert}
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(endpoint_url, params=params, headers=headers)
                if resp.status_code >= 500:
                    resp.raise_for_status()
                return {
                    "status_code": resp.status_code,
                    "data": resp.json() if resp.status_code != 404 else {},
                    "content": resp.content,
                }

        try:
            response = execute_with_resilience(
                authority=source.name,
                operation=perform_call,
                max_retries=3,
                backoff_factor=0.05,
                timeout_seconds=5.0,
            )
        except (CircuitBreakerOpenException, SourceUnavailableException) as exc:
            return VerificationResultDTO(
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                source_name=source.name,
                source_ref=sub_cert,
                message=f"Authority source '{source.name}' unavailable ({str(exc)}). Routing to manual review.",
                details={
                    "authority": source.name,
                    "error": str(exc),
                    "disclaimer": SIMULATED_SOURCE_LABEL,
                    "routed_to_manual_review": True,
                },
            )
        except Exception as exc:
            return VerificationResultDTO(
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                source_name=source.name,
                source_ref=sub_cert,
                message=f"Authority connection error: {str(exc)}. Routing to manual review.",
                details={
                    "authority": source.name,
                    "error": str(exc),
                    "disclaimer": SIMULATED_SOURCE_LABEL,
                },
            )

        # 6. Parse Response & Check 404 / NOT FOUND
        status_code = response.get("status_code", 200)
        body = response.get("data", {})
        raw_content = response.get("content", b"")
        raw_hash = hashlib.sha256(raw_content).hexdigest()

        if status_code == 404 or body.get("status") == "NOT_FOUND":
            return VerificationResultDTO(
                status=VerificationStatus.MISMATCH_DETECTED,
                source_name=source.name,
                source_ref=sub_cert,
                raw_response_hash=raw_hash,
                message=f"Certificate '{sub_cert}' not found in official {source.name} statutory register.",
                mismatched_fields=[{
                    "field": "certificate_number",
                    "submitted": sub_cert,
                    "official": "NOT_FOUND",
                }],
                details={
                    "disclaimer": SIMULATED_SOURCE_LABEL,
                    "not_found": True,
                },
            )

        official_record = body.get("record") or {}

        # 7. Compare submitted values with official record
        comp = VerificationComparator.compare(
            submitted_fields=extracted_fields,
            official_record=official_record,
        )

        matched_fields = comp["matched_fields"]
        mismatched_fields = comp["mismatched_fields"]
        is_expired = comp["is_expired"]

        if is_expired:
            status = VerificationStatus.EXPIRED
            message = f"Certificate '{sub_cert}' verified in {source.name} register, but record indicates it is EXPIRED."
        elif mismatched_fields:
            status = VerificationStatus.MISMATCH_DETECTED
            m_names = ", ".join(m["field"] for m in mismatched_fields)
            message = f"Certificate found in {source.name} register, but field mismatch detected: {m_names}."
        else:
            status = VerificationStatus.VERIFIED
            message = f"Certificate '{sub_cert}' successfully verified against {source.name} statutory register."

        return VerificationResultDTO(
            status=status,
            source_name=source.name,
            source_ref=sub_cert,
            checked_at=datetime.now(timezone.utc),
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            raw_response_hash=raw_hash,
            message=message,
            details={
                "disclaimer": SIMULATED_SOURCE_LABEL,
                "authority": source.name,
                "official_record": official_record,
                "all_comparisons": comp["all_comparisons"],
                "http_status": status_code,
            },
        )
