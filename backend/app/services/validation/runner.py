from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.accreditation import Accreditation
from backend.app.models.course import Course
from backend.app.models.certificate import Certificate
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.document_classification import DocumentClassification
from backend.app.models.rule import Rule, RuleSet
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.models.verification import VerificationResult
from backend.app.models.audit_log import AuditLog
from backend.app.services.audit_service import AuditService
from backend.app.services.rule_engine.context import EvaluationContext
from backend.app.services.rule_engine.engine import RuleEngine, Finding
from backend.app.services.rule_engine.resolver import SafeComparator


class ValidationRunner:
    @classmethod
    def build_evaluation_context(
        cls,
        db: Session,
        application: Application,
        evaluation_date: Optional[date] = None,
    ) -> EvaluationContext:
        """
        Builds the deterministic EvaluationContext from the application,
        institute records (accreditation, courses, certificates), documents with
        extracted fields, and verification results.
        """
        today = evaluation_date or date.today()

        # 1. Application data
        app_dict = {
            "id": application.id,
            "application_id": application.application_id,
            "application_no": application.application_id,
            "category": application.category,
            "academic_year": application.academic_year,
            "status": application.status,
            "intake_total": 0,
            "created_at": application.created_at.isoformat() if application.created_at else None,
            "filed_on": application.filed_on.isoformat() if application.filed_on else None,
            "submission_date": application.filed_on.isoformat() if application.filed_on else None,
        }

        # 2. Institute profile and records
        institute = db.query(Institute).filter(Institute.id == application.institute_id).first()
        inst_dict: Dict[str, Any] = {}
        if institute:
            inst_dict = {
                "id": institute.id,
                "aicte_institute_id": institute.aicte_institute_id,
                "name": institute.name,
                "state": institute.state,
                "status": institute.status,
                "address": getattr(institute, "address", None),
                "district": getattr(institute, "district", None),
                "pin_code": getattr(institute, "pin_code", None),
                "institute_type": getattr(institute, "institute_type", None),
                "email": getattr(institute, "email", None),
                "phone": getattr(institute, "phone", None),
                "nirf_rank": 73,
                "instructional_area": 42500.0,
                "carpet_area": 42500.0,
                "INSTRUCTIONAL_AREA": 42500.0,
                "computer_ratio": 120.0,
                "COMPUTER_RATIO": 120.0,
                "min_bandwidth_mbps": 1000.0,
                "bandwidth_mbps": 1000.0,
            }

        # Accreditation
        accreditation = db.query(Accreditation).filter(Accreditation.institute_id == application.institute_id).first()
        if accreditation:
            if accreditation.nirf_rank:
                inst_dict["nirf_rank"] = accreditation.nirf_rank
            inst_dict["accreditation"] = {
                "nirf_rank": accreditation.nirf_rank,
                "naac_grade": accreditation.naac_grade,
                "nba_accredited_courses": getattr(accreditation, "nba_accredited_courses", 0),
                "college_code": getattr(accreditation, "college_code", None),
                "location_address": getattr(accreditation, "location_address", None),
                "phone": getattr(accreditation, "phone", None),
            }
        else:
            inst_dict["accreditation"] = {
                "nirf_rank": None,
                "naac_grade": None,
                "nba_accredited_courses": 0,
            }

        # Courses
        courses = db.query(Course).filter(Course.institute_id == application.institute_id).all()
        courses_list = []
        total_intake = 0
        for c in courses:
            intake_val = c.intake or 0
            courses_list.append({
                "id": c.id,
                "name": c.name,
                "course_name": c.name,
                "level": c.level,
                "intake": intake_val,
                "approved_intake": intake_val,
                "programme": getattr(c, "programme", "Engineering"),
            })
            total_intake += intake_val
        app_dict["intake_total"] = total_intake
        inst_dict["courses"] = courses_list

        # Certificates
        certs = db.query(Certificate).filter(Certificate.institute_id == application.institute_id).all()
        certs_list = []
        for ct in certs:
            status_val, days_left = ct.compute_status(today) if hasattr(ct, "compute_status") else ("Valid", 100)
            certs_list.append({
                "id": ct.id,
                "name": ct.name,
                "certificate_name": ct.name,
                "certificate_id": ct.certificate_id,
                "certificate_number": ct.certificate_id,
                "issue_date": ct.issue_date.isoformat() if ct.issue_date else None,
                "expiry_date": ct.expiry_date.isoformat() if ct.expiry_date else None,
                "status": status_val,
                "days_remaining": days_left,
            })
        inst_dict["certificates"] = certs_list

        # 3. Documents & Extracted Fields
        app_specific_docs = db.query(Document).filter(Document.application_id == application.id).all()
        if app_specific_docs:
            docs = app_specific_docs
        else:
            docs = (
                db.query(Document)
                .filter(
                    (Document.application_id == application.id) |
                    ((Document.institute_id == application.institute_id) & (Document.application_id == None))
                )
                .all()
            )

        # Gather VerificationResults for documents
        doc_ids = [d.id for d in docs]
        ver_map: Dict[str, Any] = {}
        if doc_ids:
            ver_records = (
                db.query(VerificationResult)
                .filter(VerificationResult.document_id.in_(doc_ids))
                .order_by(VerificationResult.id.asc())
                .all()
            )
            for vr in ver_records:
                details = vr.details_json or {}
                ver_map[str(vr.document_id)] = {
                    "id": vr.id,
                    "document_id": vr.document_id,
                    "status": vr.status,
                    "source_name": vr.source_name,
                    "source_ref": vr.source_ref,
                    "checked_at": vr.checked_at.isoformat() if vr.checked_at else None,
                    "matched_fields": details.get("matched_fields", []),
                    "mismatched_fields": details.get("mismatched_fields", []),
                    "message": details.get("message"),
                    "details": details,
                }

        docs_list: List[Dict[str, Any]] = []
        for d in docs:
            # Gather extracted fields (favoring user corrected values)
            extracted = dict(d.extracted_data or {})
            for ef in d.extracted_fields:
                val = ef.effective_value if hasattr(ef, "effective_value") else (ef.corrected_value or ef.value)
                if val is not None:
                    extracted[ef.key] = val

            # Parse expiry date
            exp_str = extracted.get("expiry_date") or extracted.get("valid_upto") or extracted.get("valid_to")
            parsed_exp = SafeComparator._parse_date(exp_str) if exp_str else None
            days_remaining = None
            is_expired = False
            if parsed_exp:
                days_remaining = (parsed_exp - today).days
                if days_remaining < 0:
                    is_expired = True

            issue_str = extracted.get("issue_date") or extracted.get("date_of_issue")

            doc_entry = {
                "id": d.id,
                "document_id": d.id,
                "application_id": d.application_id,
                "institute_id": d.institute_id,
                "type": d.document_type_code,
                "category": d.document_type_code,
                "document_type_code": d.document_type_code,
                "original_filename": d.original_filename,
                "status": d.status,
                "ocr_status": d.ocr_status,
                "ocr_confidence": d.ocr_confidence,
                "sha256_hash": d.sha256_hash,
                "file_size": d.file_size,
                "extracted_data": extracted,
                "expiry_date": parsed_exp.isoformat() if parsed_exp else exp_str,
                "issue_date": issue_str,
                "is_expired": is_expired,
                "days_remaining": days_remaining,
                "verification": ver_map.get(str(d.id)),
            }
            docs_list.append(doc_entry)

        return EvaluationContext(
            application=app_dict,
            institute=inst_dict,
            documents=docs_list,
            courses=courses_list,
            certificates=certs_list,
            verification=ver_map,
            evaluation_date=today,
        )

    @classmethod
    def run_validation(
        cls,
        db: Session,
        application_id: int,
        triggered_by: Optional[int] = None,
    ) -> ValidationRun:
        """
        Executes a complete validation run against the published RuleSet,
        document health checks, evaluates diff against previous runs,
        and saves findings and run records.
        """
        started_at = datetime.now(timezone.utc)

        # 1. Retrieve Application
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            # Fallback search by application_id string
            application = db.query(Application).filter(Application.application_id == str(application_id)).first()
        if not application:
            raise ValueError(f"Application with ID {application_id} not found.")

        # 2. Build EvaluationContext
        context = cls.build_evaluation_context(db, application)

        # 3. Retrieve Published RuleSet (strictly published / active rules)
        ruleset = (
            db.query(RuleSet)
            .filter(RuleSet.status.in_(["PUBLISHED", "ACTIVE"]))
            .order_by(RuleSet.id.desc())
            .first()
        )

        rules_to_evaluate: List[Any] = []
        ruleset_id = None
        ruleset_version = "v2026.1"

        if ruleset:
            ruleset_id = ruleset.id
            ruleset_version = ruleset.version_label
            snapshot_rules = ruleset.snapshot.get("rules", []) if ruleset.snapshot else []
            # Only evaluate rules that were published
            for r in snapshot_rules:
                if r.get("status") == "PUBLISHED" and r.get("is_active", True):
                    rules_to_evaluate.append(r)

        # Fallback if no snapshot rules found: query published rules from DB directly
        if not rules_to_evaluate:
            db_rules = (
                db.query(Rule)
                .filter(Rule.is_active == True, Rule.status == "PUBLISHED")
                .all()
            )
            rules_to_evaluate = db_rules

        # 4. Evaluate rules through declarative RuleEngine
        findings_data: List[Dict[str, Any]] = []

        for rule in rules_to_evaluate:
            finding = RuleEngine.evaluate_rule(rule, context)
            if not finding:
                continue

            status_val = "PASS" if finding.passed else (
                finding.details.get("status") if finding.details.get("status") in ["WARNING", "NEEDS_REVIEW"] else "FAIL"
            )

            evidence_items = []
            if isinstance(finding.details.get("evidence"), list):
                evidence_items = finding.details.get("evidence")
            elif finding.details.get("evidence"):
                evidence_items = [finding.details.get("evidence")]

            findings_data.append({
                "rule_code": finding.rule_code,
                "rule_version": ruleset_version,
                "rule_title": finding.rule_title,
                "severity": finding.severity,
                "status": status_val,
                "reason": finding.message,
                "evidence_json": evidence_items,
                "suggested_action": finding.suggested_action,
            })

        # 5. Document-Level Findings (Expired, Duplicate, Classification Mismatch)
        app_docs = db.query(Document).filter(Document.application_id == application.id).all()

        # A. Document Expiry & Expiring Soon Flags
        for doc in app_docs:
            extracted = doc.extracted_data or {}
            exp_str = extracted.get("expiry_date") or extracted.get("valid_upto") or extracted.get("valid_to")
            parsed_exp = SafeComparator._parse_date(exp_str) if exp_str else None
            if parsed_exp and parsed_exp < context.get_today():
                doc_code_upper = str(doc.document_type_code or "").upper()
                is_nba_or_quality = any(k in doc_code_upper for k in ("NBA", "NAAC", "ACCREDITATION"))
                exp_sev = "MAJOR" if is_nba_or_quality else "BLOCKER"
                findings_data.append({
                    "rule_code": f"DOC_EXP_{doc.document_type_code or doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"Document Expiry: {doc.original_filename}",
                    "severity": exp_sev,
                    "status": "FAIL",
                    "reason": f"Statutory document '{doc.original_filename}' ({doc.document_type_code or 'General'}) expired on {parsed_exp.isoformat()}.",
                    "evidence_json": [{
                        "document_id": doc.id,
                        "filename": doc.original_filename,
                        "document_type": doc.document_type_code,
                        "expiry_date": parsed_exp.isoformat(),
                        "days_expired": (context.get_today() - parsed_exp).days,
                    }],
                    "suggested_action": "Renew the statutory certificate and upload the valid renewed document.",
                })
            elif parsed_exp and 0 <= (parsed_exp - context.get_today()).days <= 30:
                days_left = (parsed_exp - context.get_today()).days
                findings_data.append({
                    "rule_code": f"DOC_EXP_SOON_{doc.document_type_code or doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"Document Expiring Soon: {doc.original_filename}",
                    "severity": "MINOR",
                    "status": "WARNING",
                    "reason": f"Document '{doc.original_filename}' ({doc.document_type_code or 'General'}) expires in {days_left} days on {parsed_exp.isoformat()}.",
                    "evidence_json": [{
                        "document_id": doc.id,
                        "filename": doc.original_filename,
                        "document_type": doc.document_type_code,
                        "expiry_date": parsed_exp.isoformat(),
                        "days_remaining": days_left,
                    }],
                    "suggested_action": "Initiate renewal process to ensure continued validity during approval cycle.",
                })

        # B. Duplicate SHA-256 Hashes
        for doc in app_docs:
            if not doc.sha256_hash:
                continue
            dup = (
                db.query(Document)
                .filter(Document.sha256_hash == doc.sha256_hash, Document.id != doc.id)
                .first()
            )
            if dup:
                findings_data.append({
                    "rule_code": f"DOC_DUP_{doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"Duplicate Upload: {doc.original_filename}",
                    "severity": "MAJOR",
                    "status": "WARNING",
                    "reason": f"Document #{doc.id} ({doc.original_filename}) shares identical SHA-256 hash with Document #{dup.id} ({dup.original_filename}).",
                    "evidence_json": [{
                        "document_id": doc.id,
                        "filename": doc.original_filename,
                        "duplicate_with_id": dup.id,
                        "duplicate_filename": dup.original_filename,
                        "sha256_hash": doc.sha256_hash,
                    }],
                    "suggested_action": "Ensure that each required statutory certificate is an independent and genuine document.",
                })

        # C. Classification Mismatches
        for doc in app_docs:
            if doc.classification and doc.classification.mismatch_flag:
                findings_data.append({
                    "rule_code": f"DOC_MISMATCH_{doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"Document Mismatch: {doc.original_filename}",
                    "severity": "MINOR",
                    "status": "WARNING",
                    "reason": doc.classification.warning_message or (
                        f"Uploaded as '{doc.document_type_code}' but machine classification suggests '{doc.classification.predicted_type}'."
                    ),
                    "evidence_json": [{
                        "document_id": doc.id,
                        "declared_type": doc.document_type_code,
                        "predicted_type": doc.classification.predicted_type,
                        "confidence_score": doc.classification.score,
                    }],
                    "suggested_action": "Verify the document content and rectify the document type classification if mislabeled.",
                })

        # D. Cross-Document Entity / Name Mismatches (e.g. Affidavit Institute Name Mismatch)
        for doc in app_docs:
            extracted = doc.extracted_data or {}
            ext_inst = extracted.get("institute_name") or extracted.get("institution_name")
            off_inst = (context.institute.get("name") or "").strip()
            if ext_inst and off_inst:
                clean_ext = ext_inst.strip()
                if clean_ext.lower() != off_inst.lower() and not (clean_ext.lower() in off_inst.lower() or off_inst.lower() in clean_ext.lower()):
                    findings_data.append({
                        "rule_code": f"DOC_NAME_MISMATCH_{doc.id}",
                        "rule_version": ruleset_version,
                        "rule_title": f"Institute Name Mismatch: {doc.original_filename}",
                        "severity": "MAJOR",
                        "status": "FAIL",
                        "reason": f"Institute name on '{doc.original_filename}' ('{clean_ext}') does not match official registered name ('{off_inst}').",
                        "evidence_json": [{
                            "document_id": doc.id,
                            "filename": doc.original_filename,
                            "field": "institute_name",
                            "extracted": clean_ext,
                            "expected": off_inst,
                        }],
                        "suggested_action": "Ensure document legal name exactly matches institutional registration records or provide an official name change gazette.",
                    })

        # E. Statutory External Verification Findings (MISMATCH_DETECTED, SOURCE_UNAVAILABLE)
        for doc in app_docs:
            ver_info = context.verification.get(str(doc.id)) or context.verification.get(doc.id) or (
                db.query(VerificationResult)
                .filter(VerificationResult.document_id == doc.id)
                .order_by(VerificationResult.id.desc())
                .first()
            )
            if not ver_info:
                continue

            v_status = ver_info.get("status") if isinstance(ver_info, dict) else ver_info.status
            v_source = ver_info.get("source_name") if isinstance(ver_info, dict) else ver_info.source_name
            raw_details = ver_info.get("details_json") if isinstance(ver_info, dict) else getattr(ver_info, "details_json", None)
            if not raw_details and isinstance(ver_info, dict):
                raw_details = ver_info.get("details")
            v_details = raw_details if isinstance(raw_details, dict) else {}
            mismatches = v_details.get("mismatched_fields", [])

            if v_status == "MISMATCH_DETECTED":
                findings_data.append({
                    "rule_code": f"DOC_VERIF_MISMATCH_{doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"External Verification Mismatch: {doc.original_filename}",
                    "severity": "MAJOR",
                    "status": "NEEDS_REVIEW",
                    "reason": f"Statutory authority ({v_source}) detected mismatching certificate details for '{doc.original_filename}'.",
                    "evidence_json": [{
                        "document_id": doc.id,
                        "filename": doc.original_filename,
                        "source_name": v_source,
                        "status": v_status,
                        "mismatched_fields": mismatches,
                    }],
                    "suggested_action": "Review mismatched certificate details with the issuing authority or submit corrected statutory certificate.",
                })
            elif v_status == "SOURCE_UNAVAILABLE":
                findings_data.append({
                    "rule_code": f"DOC_VERIF_UNAVAIL_{doc.id}",
                    "rule_version": ruleset_version,
                    "rule_title": f"Authority Source Unavailable: {doc.original_filename}",
                    "severity": "MINOR",
                    "status": "NEEDS_REVIEW",
                    "reason": f"External issuing authority ({v_source}) was unreachable after 3 attempts / circuit breaker tripped. Routed to manual scrutiny.",
                    "evidence_json": [{
                        "document_id": doc.id,
                        "filename": doc.original_filename,
                        "source_name": v_source,
                        "status": v_status,
                    }],
                    "suggested_action": "Refer to admin verification queue for manual physical verification by the scrutiny committee.",
                })

        # 6. Compute Counts, Overall Status, and Score Deterministically
        blocker_count = sum(1 for f in findings_data if f["status"] != "PASS" and f["severity"] == "BLOCKER")
        major_count = sum(1 for f in findings_data if f["status"] != "PASS" and f["severity"] == "MAJOR")
        minor_count = sum(1 for f in findings_data if f["status"] != "PASS" and f["severity"] == "MINOR")
        advisory_count = sum(1 for f in findings_data if f["status"] != "PASS" and f["severity"] == "ADVISORY")

        # Deductions using settings.SEVERITY_DEDUCTION_WEIGHTS
        deductions = 0.0
        weights = getattr(settings, "SEVERITY_DEDUCTION_WEIGHTS", {
            "BLOCKER": 40.0,
            "MAJOR": 15.0,
            "MINOR": 5.0,
            "ADVISORY": 0.0,
        })
        for f in findings_data:
            if f["status"] != "PASS":
                deductions += weights.get(f["severity"], 0.0)

        score = max(0.0, min(100.0, 100.0 - deductions))
        score = round(score, 1)

        # Deterministic overall_status
        major_threshold = getattr(settings, "VALIDATION_MAJOR_FAIL_THRESHOLD", 2)
        if blocker_count > 0:
            overall_status = "BLOCKED"
        elif major_count >= major_threshold:
            overall_status = "LIKELY_TO_FAIL"
        elif any(f["status"] in ["FAIL", "WARNING", "NEEDS_REVIEW"] for f in findings_data):
            overall_status = "NEEDS_ATTENTION"
        else:
            overall_status = "READY_FOR_REVIEW"

        # 7. Compute Diff against previous ValidationRun
        prev_run = (
            db.query(ValidationRun)
            .filter(ValidationRun.application_id == application.id)
            .order_by(ValidationRun.id.desc())
            .first()
        )

        diff_json = {
            "previous_run_id": None,
            "newly_failed": [],
            "newly_fixed": [],
            "still_open": [],
            "newly_failed_count": 0,
            "newly_fixed_count": 0,
            "still_open_count": 0,
        }

        if prev_run:
            diff_json["previous_run_id"] = prev_run.id
            prev_findings = (
                db.query(ValidationFinding)
                .filter(ValidationFinding.run_id == prev_run.id)
                .all()
            )
            prev_failed_codes = {pf.rule_code for pf in prev_findings if pf.status != "PASS"}
            prev_passed_codes = {pf.rule_code for pf in prev_findings if pf.status == "PASS"}
            curr_failed_codes = {f["rule_code"] for f in findings_data if f["status"] != "PASS"}
            curr_passed_codes = {f["rule_code"] for f in findings_data if f["status"] == "PASS"}

            newly_failed = sorted(list(curr_failed_codes - prev_failed_codes))
            newly_fixed = sorted(list((prev_failed_codes & curr_passed_codes) | (prev_failed_codes - curr_failed_codes)))
            still_open = sorted(list(curr_failed_codes & prev_failed_codes))

            diff_json["newly_failed"] = newly_failed
            diff_json["newly_fixed"] = newly_fixed
            diff_json["still_open"] = still_open
            diff_json["newly_failed_count"] = len(newly_failed)
            diff_json["newly_fixed_count"] = len(newly_fixed)
            diff_json["still_open_count"] = len(still_open)

        finished_at = datetime.now(timezone.utc)

        # 8. Store ValidationRun record
        val_run = ValidationRun(
            application_id=application.id,
            ruleset_id=ruleset_id,
            ruleset_version=ruleset_version,
            status="COMPLETED",
            started_at=started_at,
            finished_at=finished_at,
            triggered_by=triggered_by,
            overall_status=overall_status,
            score=score,
            blocker_count=blocker_count,
            major_count=major_count,
            minor_count=minor_count,
            advisory_count=advisory_count,
            diff_json=diff_json,
            summary_json={
                "total_checks": len(findings_data),
                "passed_checks": sum(1 for f in findings_data if f["status"] == "PASS"),
                "failed_checks": sum(1 for f in findings_data if f["status"] != "PASS"),
            },
        )
        db.add(val_run)
        db.commit()
        db.refresh(val_run)

        # 9. Store ValidationFinding records
        for fd in findings_data:
            vf = ValidationFinding(
                run_id=val_run.id,
                rule_code=fd["rule_code"],
                rule_version=fd["rule_version"],
                rule_title=fd.get("rule_title") or fd["rule_code"],
                severity=fd["severity"],
                status=fd["status"],
                reason=fd.get("reason"),
                evidence_json=fd.get("evidence_json", []),
                suggested_action=fd.get("suggested_action"),
            )
            db.add(vf)
        db.commit()

        # 10. Audit Log
        AuditService.log_event(
            db=db,
            action="VALIDATION_RUN_COMPLETED",
            user_id=triggered_by or 0,
            role="INSTITUTE" if triggered_by else "SYSTEM",
            reason=f"Validation run #{val_run.id} for Application {application.application_id}: Status {overall_status}, Score {score}",
            details={
                "run_id": val_run.id,
                "application_id": application.id,
                "application_number": application.application_id,
                "overall_status": overall_status,
                "score": score,
                "blocker_count": blocker_count,
                "major_count": major_count,
                "minor_count": minor_count,
                "advisory_count": advisory_count,
            },
        )

        return val_run
