import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status, Header, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models.verification import MockRegisterEntry
from backend.app.services.verification.comparator import VerificationComparator

SIMULATED_SOURCE_DISCLAIMER = "SIMULATED SOURCE - replace with the authorised integration"

router = APIRouter(tags=["Mock Authorities"])


def _normalize_authority(authority: str) -> str:
    s = authority.upper().replace("-", "_").replace(" ", "_")
    if "NBA" in s:
        return "NBA"
    if "NAAC" in s:
        return "NAAC"
    if "FIRE" in s:
        return "FIRE_DEPT"
    if "POLLUTION" in s:
        return "POLLUTION_BOARD"
    if "MUNICIPAL" in s or "OCCUPANCY" in s or "BUILDING" in s:
        return "MUNICIPAL_CORP"
    return s


@router.api_route("/{authority}/verify", methods=["GET", "POST"])
async def verify_mock_authority(
    authority: str,
    request: Request,
    response: Response,
    certificate_number: Optional[str] = Query(None),
    simulate_error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Simulated Issuing Authority Verification Endpoint.
    Serves synthetic records for NBA, NAAC, Fire Dept, Pollution Board, Municipal Corp.
    Clearly labeled with simulation disclaimer.
    """
    response.headers["X-Simulated-Source"] = SIMULATED_SOURCE_DISCLAIMER

    # Parse certificate number from body if POST and not in query
    if not certificate_number and request.method == "POST":
        try:
            body = await request.json()
            certificate_number = (
                body.get("certificate_number")
                or body.get("noc_number")
                or body.get("approval_number")
                or body.get("accreditation_number")
                or body.get("cert_id")
            )
            if not simulate_error:
                simulate_error = body.get("simulate_error")
        except Exception:
            pass

    # Simulation test hook for resilience / circuit breaker testing
    if simulate_error == "503" or simulate_error == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{SIMULATED_SOURCE_DISCLAIMER}: Service temporarily unavailable.",
            headers={"X-Simulated-Source": SIMULATED_SOURCE_DISCLAIMER},
        )
    if simulate_error == "timeout":
        # Sleep to simulate timeout
        time.sleep(6.0)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{SIMULATED_SOURCE_DISCLAIMER}: Gateway Timeout.",
            headers={"X-Simulated-Source": SIMULATED_SOURCE_DISCLAIMER},
        )

    if not certificate_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="certificate_number parameter is required.",
            headers={"X-Simulated-Source": SIMULATED_SOURCE_DISCLAIMER},
        )

    auth_key = _normalize_authority(authority)
    clean_cert = VerificationComparator.normalize_cert_number(certificate_number)

    # Search in MockRegisterEntry
    entries = (
        db.query(MockRegisterEntry)
        .filter(MockRegisterEntry.authority == auth_key)
        .all()
    )

    matched_entry = None
    for entry in entries:
        if VerificationComparator.normalize_cert_number(entry.certificate_number) == clean_cert:
            matched_entry = entry
            break

    if not matched_entry:
        # Fallback: search across all authorities if exact authority has no match
        all_entries = db.query(MockRegisterEntry).all()
        for entry in all_entries:
            if VerificationComparator.normalize_cert_number(entry.certificate_number) == clean_cert:
                matched_entry = entry
                break

    if not matched_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "authority": auth_key,
                "disclaimer": SIMULATED_SOURCE_DISCLAIMER,
                "status": "NOT_FOUND",
                "certificate_number": certificate_number,
                "message": f"Certificate '{certificate_number}' not found in official {auth_key} register.",
            },
            headers={"X-Simulated-Source": SIMULATED_SOURCE_DISCLAIMER},
        )

    return {
        "authority": auth_key,
        "disclaimer": SIMULATED_SOURCE_DISCLAIMER,
        "status": "FOUND",
        "record": {
            "certificate_number": matched_entry.certificate_number,
            "institute_name": matched_entry.institute_name,
            "issue_date": matched_entry.issue_date,
            "expiry_date": matched_entry.expiry_date,
            "status": matched_entry.status,
            "details": matched_entry.data_json or {},
        },
    }

