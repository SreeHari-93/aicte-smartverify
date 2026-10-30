import difflib
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.document import Document
from backend.app.models.verification import VerificationResult
from backend.app.models.anomaly import AnomalyFlag


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip().lower()
    return re.sub(r"\s+", " ", s)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _sanitize_reason(text: str) -> str:
    """Ensure compliance with preliminary screening terminology guidelines."""
    t = text
    t = re.sub(r"\bforger(y|ies)\b", "potential anomaly", t, flags=re.IGNORECASE)
    t = re.sub(r"\bfraud(ulent)?\b", "potential anomaly", t, flags=re.IGNORECASE)
    t = re.sub(r"\bmisconduct\b", "potential inconsistency", t, flags=re.IGNORECASE)
    if "needs verification" not in t.lower() and "potential anomaly" not in t.lower():
        t = f"{t}; preliminary indicator requiring verification."
    return t


class EvidenceGraphBuilder:
    """
    Builds a multi-entity evidence graph per institutional application.

    Nodes:
      - institute
      - application
      - documents
      - extracted fields
      - verification results
      - anomaly flags

    Edges:
      - institute-submits-application
      - application-includes-document
      - document-contains-field
      - field-conflicts-with-field (across documents: institute name, AICTE ID, address, dates)
      - document-verified-by-source
      - flag-about-document
      - duplicate-of
    """

    INSTITUTE_NAME_KEYS = {"institute_name", "institution_name", "college_name", "name_of_institute"}
    AICTE_ID_KEYS = {"aicte_id", "aicte_institute_id", "permanent_id", "institute_id"}
    ADDRESS_KEYS = {"address", "institute_address", "location", "site_address", "campus_address"}
    DATE_KEYS = {"issue_date", "expiry_date", "valid_till", "valid_upto", "date_of_issue"}

    @classmethod
    def get_document_fields(cls, doc: Document) -> Dict[str, Any]:
        """Collects field dictionary from doc.extracted_data and doc.extracted_fields."""
        fields: Dict[str, Any] = {}
        if doc.extracted_data and isinstance(doc.extracted_data, dict):
            for k, v in doc.extracted_data.items():
                if v is not None and str(v).strip():
                    fields[str(k)] = v

        if doc.extracted_fields:
            for ef in doc.extracted_fields:
                key = getattr(ef, "key", None) or getattr(ef, "field_name", None)
                val = getattr(ef, "effective_value", None) or getattr(ef, "corrected_value", None) or getattr(ef, "value", None) or getattr(ef, "field_value", None)
                if key and val is not None and str(val).strip():
                    fields[str(key)] = val

        return fields

    @classmethod
    def build_graph(
        cls,
        db: Session,
        application_id: int,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application #{application_id} not found.")

        inst = app.institute or db.query(Institute).filter(Institute.id == app.institute_id).first()
        inst_name = inst.name if inst else f"Institute #{app.institute_id}"
        aicte_id = inst.aicte_institute_id if inst else "UNKNOWN-AICTE-ID"

        # Query all documents for this application
        docs = (
            db.query(Document)
            .filter(Document.application_id == app.id)
            .order_by(Document.id.asc())
            .all()
        )

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []
        node_ids: Set[str] = set()

        def add_node(n_id: str, n_type: str, label: str, properties: Dict[str, Any]):
            if n_id in node_ids:
                return
            node_ids.add(n_id)
            nodes.append({
                "id": n_id,
                "type": n_type,
                "label": label,
                "properties": properties,
            })

        def add_edge(e_id: str, source: str, target: str, e_type: str, label: str, properties: Optional[Dict[str, Any]] = None):
            edges.append({
                "id": e_id,
                "source": source,
                "target": target,
                "type": e_type,
                "label": label,
                "properties": properties or {},
            })

        # 1. Institute Node
        inst_node_id = f"inst_{inst.id if inst else app.institute_id}"
        add_node(
            inst_node_id,
            "institute",
            inst_name,
            {
                "id": inst.id if inst else app.institute_id,
                "name": inst_name,
                "aicte_id": aicte_id,
                "state": inst.state if inst else "N/A",
            },
        )

        # 2. Application Node
        app_node_id = f"app_{app.id}"
        add_node(
            app_node_id,
            "application",
            f"Application {app.application_id}",
            {
                "id": app.id,
                "application_id": app.application_id,
                "category": app.category,
                "academic_year": app.academic_year,
                "status": app.status,
            },
        )

        add_edge(
            f"edge_inst_{inst_node_id}_app_{app_node_id}",
            inst_node_id,
            app_node_id,
            "institute-submits-application",
            "Submits",
        )

        # Preload anomaly flags for all docs
        doc_ids = [d.id for d in docs]
        all_flags: List[AnomalyFlag] = []
        if doc_ids:
            all_flags = (
                db.query(AnomalyFlag)
                .filter(AnomalyFlag.document_id.in_(doc_ids))
                .order_by(AnomalyFlag.id.asc())
                .all()
            )

        flags_by_doc: Dict[int, List[AnomalyFlag]] = {}
        for f in all_flags:
            flags_by_doc.setdefault(f.document_id, []).append(f)

        # 3. Document Nodes & Direct Children (Fields, Verification, Flags)
        doc_fields_map: Dict[int, Dict[str, Any]] = {}

        for doc in docs:
            doc_node_id = f"doc_{doc.id}"
            doc_type_code = doc.document_type_code or "DOCUMENT"
            add_node(
                doc_node_id,
                "document",
                f"{doc_type_code}: {doc.original_filename}",
                {
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "document_type": doc_type_code,
                    "sha256": doc.sha256_hash,
                    "status": doc.status,
                    "verification_status": doc.verification_status,
                },
            )

            add_edge(
                f"edge_app_{app.id}_doc_{doc.id}",
                app_node_id,
                doc_node_id,
                "application-includes-document",
                "Includes document",
            )

            # Extracted Fields
            fields = cls.get_document_fields(doc)
            doc_fields_map[doc.id] = fields

            for f_key, f_val in fields.items():
                field_node_id = f"field_{doc.id}_{f_key}"
                val_str = str(f_val)
                label_display = f"{f_key.replace('_', ' ').title()}: {val_str[:24]}{'...' if len(val_str) > 24 else ''}"
                add_node(
                    field_node_id,
                    "field",
                    label_display,
                    {
                        "document_id": doc.id,
                        "document_filename": doc.original_filename,
                        "key": f_key,
                        "value": f_val,
                    },
                )
                add_edge(
                    f"edge_doc_{doc.id}_field_{f_key}",
                    doc_node_id,
                    field_node_id,
                    "document-contains-field",
                    "Contains field",
                )

            # Verification Results
            for ver in doc.verification_results:
                ver_node_id = f"ver_{ver.id}"
                ver_status_clean = ver.status.replace("_", " ")
                add_node(
                    ver_node_id,
                    "verification",
                    f"{ver.source_name}: {ver_status_clean}",
                    {
                        "id": ver.id,
                        "document_id": doc.id,
                        "status": ver.status,
                        "source_name": ver.source_name,
                        "checked_at": ver.checked_at.isoformat() if ver.checked_at else None,
                        "is_simulated": "simulated" in (ver.source_name or "").lower(),
                    },
                )
                add_edge(
                    f"edge_doc_{doc.id}_ver_{ver.id}",
                    doc_node_id,
                    ver_node_id,
                    "document-verified-by-source",
                    f"Verified: {ver_status_clean}",
                )

            # Anomaly Flags
            doc_flags = flags_by_doc.get(doc.id, [])
            for flag in doc_flags:
                flag_node_id = f"flag_{flag.id}"
                sanitized_reason = _sanitize_reason(flag.reason)
                flag_label = f"[{flag.severity}] {flag.detector}: needs verification"

                flag_props: Dict[str, Any] = {
                    "id": flag.id,
                    "document_id": doc.id,
                    "detector": flag.detector,
                    "code": flag.code,
                    "group_key": flag.group_key,
                    "severity": flag.severity,
                    "reason": sanitized_reason,
                    "recommended_action": flag.recommended_action,
                    "review_status": flag.review_status,
                    "has_overlay": bool(flag.overlay_image_path and os.path.exists(flag.overlay_image_path)),
                }

                if is_admin:
                    flag_props["confidence"] = flag.confidence
                    flag_props["evidence"] = flag.evidence_json
                    flag_props["overlay_image_path"] = flag.overlay_image_path
                else:
                    # Sanitize evidence by omitting raw confidence scores
                    sanitized_evidence = []
                    for ev in (flag.evidence_json or []):
                        if isinstance(ev, dict):
                            clean_ev = {k: v for k, v in ev.items() if k not in ["confidence", "internal_score"]}
                            sanitized_evidence.append(clean_ev)
                        else:
                            sanitized_evidence.append(ev)
                    flag_props["evidence"] = sanitized_evidence

                add_node(flag_node_id, "anomaly_flag", flag_label, flag_props)

                add_edge(
                    f"edge_flag_{flag.id}_doc_{doc.id}",
                    flag_node_id,
                    doc_node_id,
                    "flag-about-document",
                    "Flags potential anomaly",
                    {"severity": flag.severity, "reason": sanitized_reason},
                )

                # Check if flag references a duplicate document
                if flag.code in ["EXACT_HASH_DUPLICATE", "VISUAL_SIMILARITY_DUPLICATE"]:
                    for ev in (flag.evidence_json or []):
                        if isinstance(ev, dict) and "duplicate_with_id" in ev:
                            dup_id = ev["duplicate_with_id"]
                            add_edge(
                                f"edge_dup_{doc.id}_{dup_id}",
                                f"doc_{doc.id}",
                                f"doc_{dup_id}",
                                "duplicate-of",
                                "Potential duplicate (needs verification)",
                                {"reason": sanitized_reason},
                            )

        # 4. Duplicate Check by SHA-256 (Cross-Document in this Application)
        seen_hashes: Dict[str, Document] = {}
        for doc in docs:
            if not doc.sha256_hash:
                continue
            if doc.sha256_hash in seen_hashes:
                other_doc = seen_hashes[doc.sha256_hash]
                e_id = f"edge_dup_sha_{doc.id}_{other_doc.id}"
                if not any(e["id"] == e_id for e in edges):
                    add_edge(
                        e_id,
                        f"doc_{doc.id}",
                        f"doc_{other_doc.id}",
                        "duplicate-of",
                        "Identical SHA-256 duplicate (needs verification)",
                        {
                            "sha256_hash": doc.sha256_hash,
                            "reason": f"Document #{doc.id} ({doc.original_filename}) shares identical SHA-256 with document #{other_doc.id} ({other_doc.original_filename}); potential anomaly requiring verification.",
                        },
                    )
            else:
                seen_hashes[doc.sha256_hash] = doc

        # 5. Cross-Document Conflict Detection
        # Compare all pairs of documents (doc_a, doc_b)
        num_docs = len(docs)
        for i in range(num_docs):
            for j in range(i + 1, num_docs):
                doc_a = docs[i]
                doc_b = docs[j]
                fields_a = doc_fields_map.get(doc_a.id, {})
                fields_b = doc_fields_map.get(doc_b.id, {})

                # (a) Institute Name Conflicts
                inst_val_a = None
                inst_key_a = None
                for k in cls.INSTITUTE_NAME_KEYS:
                    if k in fields_a and str(fields_a[k]).strip():
                        inst_val_a = str(fields_a[k]).strip()
                        inst_key_a = k
                        break

                inst_val_b = None
                inst_key_b = None
                for k in cls.INSTITUTE_NAME_KEYS:
                    if k in fields_b and str(fields_b[k]).strip():
                        inst_val_b = str(fields_b[k]).strip()
                        inst_key_b = k
                        break

                if inst_val_a and inst_val_b:
                    sim = _similarity(_clean_str(inst_val_a), _clean_str(inst_val_b))
                    if sim < 0.85:
                        reason = (
                            f"Institute name mismatch across documents ('{inst_val_a}' in {doc_a.original_filename} vs "
                            f"'{inst_val_b}' in {doc_b.original_filename}); potential anomaly requiring verification."
                        )
                        c_item = {
                            "type": "INSTITUTE_NAME_CONFLICT",
                            "field": "institute_name",
                            "doc_id_1": doc_a.id,
                            "doc_id_2": doc_b.id,
                            "doc_file_1": doc_a.original_filename,
                            "doc_file_2": doc_b.original_filename,
                            "value_1": inst_val_a,
                            "value_2": inst_val_b,
                            "reason": reason,
                        }
                        conflicts.append(c_item)

                        node_a_id = f"field_{doc_a.id}_{inst_key_a}"
                        node_b_id = f"field_{doc_b.id}_{inst_key_b}"
                        add_edge(
                            f"edge_conflict_inst_name_{doc_a.id}_{doc_b.id}",
                            node_a_id,
                            node_b_id,
                            "field-conflicts-with-field",
                            "Conflicting institute name (needs verification)",
                            c_item,
                        )

                # (b) AICTE ID Conflicts
                aicte_val_a = None
                aicte_key_a = None
                for k in cls.AICTE_ID_KEYS:
                    if k in fields_a and str(fields_a[k]).strip():
                        aicte_val_a = str(fields_a[k]).strip()
                        aicte_key_a = k
                        break

                aicte_val_b = None
                aicte_key_b = None
                for k in cls.AICTE_ID_KEYS:
                    if k in fields_b and str(fields_b[k]).strip():
                        aicte_val_b = str(fields_b[k]).strip()
                        aicte_key_b = k
                        break

                if aicte_val_a and aicte_val_b:
                    norm_a = re.sub(r"[^a-zA-Z0-9]", "", aicte_val_a).lower()
                    norm_b = re.sub(r"[^a-zA-Z0-9]", "", aicte_val_b).lower()
                    if norm_a and norm_b and norm_a != norm_b:
                        reason = (
                            f"AICTE permanent ID mismatch across documents ('{aicte_val_a}' in {doc_a.original_filename} vs "
                            f"'{aicte_val_b}' in {doc_b.original_filename}); potential anomaly requiring verification."
                        )
                        c_item = {
                            "type": "AICTE_ID_CONFLICT",
                            "field": "aicte_id",
                            "doc_id_1": doc_a.id,
                            "doc_id_2": doc_b.id,
                            "doc_file_1": doc_a.original_filename,
                            "doc_file_2": doc_b.original_filename,
                            "value_1": aicte_val_a,
                            "value_2": aicte_val_b,
                            "reason": reason,
                        }
                        conflicts.append(c_item)

                        node_a_id = f"field_{doc_a.id}_{aicte_key_a}"
                        node_b_id = f"field_{doc_b.id}_{aicte_key_b}"
                        add_edge(
                            f"edge_conflict_aicte_id_{doc_a.id}_{doc_b.id}",
                            node_a_id,
                            node_b_id,
                            "field-conflicts-with-field",
                            "Conflicting AICTE ID (needs verification)",
                            c_item,
                        )

                # (c) Address Conflicts
                addr_val_a = None
                addr_key_a = None
                for k in cls.ADDRESS_KEYS:
                    if k in fields_a and str(fields_a[k]).strip():
                        addr_val_a = str(fields_a[k]).strip()
                        addr_key_a = k
                        break

                addr_val_b = None
                addr_key_b = None
                for k in cls.ADDRESS_KEYS:
                    if k in fields_b and str(fields_b[k]).strip():
                        addr_val_b = str(fields_b[k]).strip()
                        addr_key_b = k
                        break

                if addr_val_a and addr_val_b and len(addr_val_a) >= 8 and len(addr_val_b) >= 8:
                    sim_addr = _similarity(_clean_str(addr_val_a), _clean_str(addr_val_b))
                    if sim_addr < 0.70:
                        reason = (
                            f"Institute location address mismatch across documents ('{addr_val_a}' vs '{addr_val_b}'); "
                            f"potential anomaly requiring verification."
                        )
                        c_item = {
                            "type": "ADDRESS_CONFLICT",
                            "field": "address",
                            "doc_id_1": doc_a.id,
                            "doc_id_2": doc_b.id,
                            "doc_file_1": doc_a.original_filename,
                            "doc_file_2": doc_b.original_filename,
                            "value_1": addr_val_a,
                            "value_2": addr_val_b,
                            "reason": reason,
                        }
                        conflicts.append(c_item)

                        node_a_id = f"field_{doc_a.id}_{addr_key_a}"
                        node_b_id = f"field_{doc_b.id}_{addr_key_b}"
                        add_edge(
                            f"edge_conflict_address_{doc_a.id}_{doc_b.id}",
                            node_a_id,
                            node_b_id,
                            "field-conflicts-with-field",
                            "Conflicting address (needs verification)",
                            c_item,
                        )

                # (d) Date Conflicts (Same type documents or contradictory period ranges)
                if (
                    doc_a.document_type_code
                    and doc_b.document_type_code
                    and doc_a.document_type_code == doc_b.document_type_code
                ):
                    issue_a = fields_a.get("issue_date") or fields_a.get("date_of_issue")
                    issue_b = fields_b.get("issue_date") or fields_b.get("date_of_issue")
                    if issue_a and issue_b and str(issue_a).strip() != str(issue_b).strip():
                        reason = (
                            f"Inconsistent issuance dates for certificate type '{doc_a.document_type_code}' "
                            f"('{issue_a}' in {doc_a.original_filename} vs '{issue_b}' in {doc_b.original_filename}); "
                            f"potential anomaly requiring verification."
                        )
                        c_item = {
                            "type": "DATE_CONFLICT",
                            "field": "issue_date",
                            "doc_id_1": doc_a.id,
                            "doc_id_2": doc_b.id,
                            "doc_file_1": doc_a.original_filename,
                            "doc_file_2": doc_b.original_filename,
                            "value_1": str(issue_a),
                            "value_2": str(issue_b),
                            "reason": reason,
                        }
                        conflicts.append(c_item)

                        node_a_id = f"field_{doc_a.id}_issue_date"
                        node_b_id = f"field_{doc_b.id}_issue_date"
                        if node_a_id in node_ids and node_b_id in node_ids:
                            add_edge(
                                f"edge_conflict_date_{doc_a.id}_{doc_b.id}",
                                node_a_id,
                                node_b_id,
                                "field-conflicts-with-field",
                                "Conflicting issue date (needs verification)",
                                c_item,
                            )

        summary = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "conflict_count": len(conflicts),
            "anomaly_flag_count": len(all_flags),
            "documents_count": len(docs),
        }

        return {
            "application_id": app.application_id,
            "application_pk": app.id,
            "institute_id": inst.id if inst else app.institute_id,
            "institute_name": inst_name,
            "nodes": nodes,
            "edges": edges,
            "conflicts": conflicts,
            "summary": summary,
        }

