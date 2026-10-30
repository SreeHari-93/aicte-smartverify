import re
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.models.institute import Institute
from backend.app.models.verification import MockRegisterEntry
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


class IdentifierDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "IdentifierDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document
        db: Session = context.db
        ext = context.extracted_fields

        cert_num = ext.get("certificate_number") or ext.get("noc_number") or ext.get("certificate_no") or ext.get("accreditation_number")

        # 1. Certificate number format not matching document type pattern
        pattern = None
        if context.doc_type:
            pattern = getattr(context.doc_type, "number_pattern", None)
            if not pattern and context.doc_type.extraction_schema:
                for fld in context.doc_type.extraction_schema:
                    if isinstance(fld, dict) and fld.get("key") in ["certificate_number", "noc_number", "certificate_no"]:
                        pattern = fld.get("pattern")
                        if pattern:
                            break

        if cert_num and pattern:
            try:
                if not re.search(pattern, str(cert_num).strip()):
                    flags.append(
                        AnomalyFlagDTO(
                            detector=self.name,
                            code="IDENTIFIER_PATTERN_MISMATCH",
                            severity="MEDIUM",
                            reason=f"Certificate identifier ('{cert_num}') does not match statutory numbering pattern for {context.doc_type.name or context.doc_type.code}; potential anomaly requiring verification.",
                            evidence=[{
                                "document_id": doc.id,
                                "field": "certificate_number",
                                "value": str(cert_num),
                                "expected_pattern": pattern,
                            }],
                            confidence=0.85,
                            recommended_action="Verify certificate numbering format with issuing authority.",
                        )
                    )
            except Exception:
                pass

        # 2. Same certificate number used by a different institute
        if cert_num:
            clean_num = str(cert_num).strip()
            # Search other documents
            conflict_docs = (
                db.query(Document)
                .filter(
                    Document.id != doc.id,
                    Document.institute_id != doc.institute_id,
                )
                .all()
            )
            conflict_found = False
            for cd in conflict_docs:
                cd_ext = cd.extracted_data or {}
                cd_num = cd_ext.get("certificate_number") or cd_ext.get("noc_number") or cd_ext.get("certificate_no")
                if cd_num and str(cd_num).strip() == clean_num:
                    conflict_found = True
                    conflicting_inst = db.query(Institute).filter(Institute.id == cd.institute_id).first()
                    inst_desc = conflicting_inst.name if conflicting_inst else f"Institute #{cd.institute_id}"
                    flags.append(
                        AnomalyFlagDTO(
                            detector=self.name,
                            code="IDENTIFIER_CROSS_INSTITUTE_REUSE",
                            severity="HIGH",
                            reason=f"Certificate number ('{clean_num}') matches a document uploaded by a different institution ({inst_desc}); potential anomaly requiring verification.",
                            evidence=[{
                                "document_id": doc.id,
                                "field": "certificate_number",
                                "value": clean_num,
                                "conflicting_institute_id": cd.institute_id,
                                "conflicting_document_id": cd.id,
                            }],
                            confidence=0.95,
                            recommended_action="Perform statutory authority register inquiry to confirm institutional ownership.",
                        )
                    )
                    break

            if not conflict_found:
                # Check MockRegisterEntry for cross-institute conflict
                reg_entry = (
                    db.query(MockRegisterEntry)
                    .filter(MockRegisterEntry.certificate_number == clean_num)
                    .first()
                )
                if reg_entry and doc.institute:
                    reg_inst = (reg_entry.institute_name or "").strip().lower()
                    doc_inst = (doc.institute.name or "").strip().lower()
                    if reg_inst and doc_inst and reg_inst not in doc_inst and doc_inst not in reg_inst:
                        flags.append(
                            AnomalyFlagDTO(
                                detector=self.name,
                                code="IDENTIFIER_CROSS_INSTITUTE_REUSE",
                                severity="HIGH",
                                reason=f"Certificate number ('{clean_num}') is officially registered to '{reg_entry.institute_name}'; potential anomaly requiring verification.",
                                evidence=[{
                                    "document_id": doc.id,
                                    "field": "certificate_number",
                                    "value": clean_num,
                                    "official_register_institute": reg_entry.institute_name,
                                    "authority": reg_entry.authority,
                                }],
                                confidence=0.95,
                                recommended_action="Perform statutory authority register inquiry to confirm institutional ownership.",
                            )
                        )

        # 3. Mismatched identifiers across documents / application profile
        doc_inst_name = ext.get("institute_name") or ext.get("institution_name")
        if doc_inst_name and doc.institute:
            clean_doc_name = str(doc_inst_name).strip()
            reg_name = (doc.institute.name or "").strip()
            if clean_doc_name.lower() != reg_name.lower() and not (
                clean_doc_name.lower() in reg_name.lower() or reg_name.lower() in clean_doc_name.lower()
            ):
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="IDENTIFIER_INSTITUTE_NAME_MISMATCH",
                        severity="MEDIUM",
                        reason=f"Extracted institution name ('{clean_doc_name}') deviates from registered institute profile ('{reg_name}'); needs verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "field": "institute_name",
                            "value": clean_doc_name,
                            "expected": reg_name,
                        }],
                        confidence=0.80,
                        recommended_action="Confirm institutional legal name alignment across submitted documents.",
                    )
                )

        doc_aicte_id = ext.get("aicte_institute_id") or ext.get("aicte_id")
        if doc_aicte_id and doc.institute and doc.institute.aicte_institute_id:
            clean_doc_aicte = str(doc_aicte_id).strip()
            reg_aicte = str(doc.institute.aicte_institute_id).strip()
            if clean_doc_aicte.lower() != reg_aicte.lower():
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="IDENTIFIER_AICTE_ID_MISMATCH",
                        severity="HIGH",
                        reason=f"Extracted AICTE identifier ('{clean_doc_aicte}') does not match registered institute AICTE ID ('{reg_aicte}'); needs verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "field": "aicte_id",
                            "value": clean_doc_aicte,
                            "expected": reg_aicte,
                        }],
                        confidence=0.90,
                        recommended_action="Verify AICTE institution identifier recorded on statutory document.",
                    )
                )

        doc_survey = ext.get("survey_number") or ext.get("land_survey_no")
        if doc_survey and doc.application_id:
            # Check other land documents in the application
            clean_survey = str(doc_survey).strip().lower()
            app_docs = (
                db.query(Document)
                .filter(Document.application_id == doc.application_id, Document.id != doc.id)
                .all()
            )
            for ad in app_docs:
                ad_ext = ad.extracted_data or {}
                ad_survey = ad_ext.get("survey_number") or ad_ext.get("land_survey_no")
                if ad_survey and str(ad_survey).strip().lower() != clean_survey:
                    flags.append(
                        AnomalyFlagDTO(
                            detector=self.name,
                            code="IDENTIFIER_SURVEY_NUMBER_MISMATCH",
                            severity="MEDIUM",
                            reason=f"Land survey number ('{doc_survey}') differs from another land record in this application ('{ad_survey}'); needs verification.",
                            evidence=[{
                                "document_id": doc.id,
                                "field": "survey_number",
                                "value": str(doc_survey),
                                "other_document_id": ad.id,
                                "other_survey": str(ad_survey),
                            }],
                            confidence=0.75,
                            recommended_action="Confirm all contiguous parcels and survey numbers in land registration records.",
                        )
                    )
                    break

        return flags
