import os
from difflib import SequenceMatcher
from typing import List
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.document import Document
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


def _compute_dhash(img: Image.Image, hash_size: int = 8) -> int:
    """Computes difference hash (dHash) for an image."""
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())
    val = 0
    idx = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * (hash_size + 1) + col]
            right = pixels[row * (hash_size + 1) + col + 1]
            if left > right:
                val |= (1 << idx)
            idx += 1
    return val


def _hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")


class DuplicateDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "DuplicateDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document
        db: Session = context.db

        # 1. Exact SHA-256 duplicate across applications and types
        if doc.sha256_hash:
            exact_dup = (
                db.query(Document)
                .filter(Document.sha256_hash == doc.sha256_hash, Document.id != doc.id)
                .first()
            )
            if exact_dup:
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="EXACT_HASH_DUPLICATE",
                        group_key="DUPLICATE",
                        severity="HIGH",
                        reason=f"Identical SHA-256 file hash matches document #{exact_dup.id} ('{exact_dup.original_filename}'); potential anomaly requiring verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "duplicate_with_id": exact_dup.id,
                            "duplicate_filename": exact_dup.original_filename,
                            "sha256_hash": doc.sha256_hash,
                        }],
                        confidence=1.0,
                        recommended_action="Review duplicate uploads and provide the unique certified record for this application.",
                    )
                )

        # 2. Near-duplicate perceptual visual hash and text similarity
        rendered = context.get_rendered_pages(max_pages=1)
        doc_hash = _compute_dhash(rendered[0][1]) if rendered else None
        doc_text = context.get_document_text()

        # Query candidates from the same institute or application (exclude self and exact hash dupes)
        candidates_query = db.query(Document).filter(Document.id != doc.id)
        if doc.application_id:
            candidates_query = candidates_query.filter(
                (Document.application_id == doc.application_id) | (Document.institute_id == doc.institute_id)
            )
        else:
            candidates_query = candidates_query.filter(Document.institute_id == doc.institute_id)

        candidates = candidates_query.limit(25).all()

        visual_flagged = False
        text_flagged = False

        for cand in candidates:
            # Skip if exact duplicate already flagged for this pair
            if doc.sha256_hash and cand.sha256_hash == doc.sha256_hash:
                continue

            # Perceptual hash comparison
            if doc_hash is not None and not visual_flagged and cand.file_path and os.path.exists(cand.file_path):
                try:
                    cand_ctx = DetectionContext(db=db, document=cand)
                    cand_rendered = cand_ctx.get_rendered_pages(max_pages=1)
                    if cand_rendered:
                        cand_hash = _compute_dhash(cand_rendered[0][1])
                        h_dist = _hamming_distance(doc_hash, cand_hash)
                        if h_dist <= settings.ANOMALY_DUPLICATE_PHASH_THRESHOLD:
                            visual_flagged = True
                            flags.append(
                                AnomalyFlagDTO(
                                    detector=self.name,
                                    code="VISUAL_NEAR_DUPLICATE",
                                    group_key="DUPLICATE",
                                    severity="MEDIUM",
                                    reason=f"Visual layout perceptual hash closely matches document #{cand.id} ('{cand.original_filename}') with distance {h_dist}; potential anomaly requiring verification.",
                                    evidence=[{
                                        "document_id": doc.id,
                                        "duplicate_with_id": cand.id,
                                        "duplicate_filename": cand.original_filename,
                                        "hamming_distance": h_dist,
                                        "max_threshold": settings.ANOMALY_DUPLICATE_PHASH_THRESHOLD,
                                    }],
                                    confidence=round(1.0 - (h_dist / (settings.ANOMALY_DUPLICATE_PHASH_THRESHOLD + 1)) * 0.2, 2),
                                    recommended_action="Verify whether visual near-duplicate originates from a shared template or repeated scan.",
                                )
                            )
                except Exception:
                    pass

            # Text similarity comparison
            if doc_text and len(doc_text) > 80 and not text_flagged:
                cand_ctx = DetectionContext(db=db, document=cand)
                cand_text = cand_ctx.get_document_text()
                if cand_text and len(cand_text) > 80:
                    sim = SequenceMatcher(None, doc_text[:1000], cand_text[:1000]).ratio()
                    if sim >= settings.ANOMALY_DUPLICATE_TEXT_SIMILARITY_THRESHOLD:
                        text_flagged = True
                        flags.append(
                            AnomalyFlagDTO(
                                detector=self.name,
                                code="TEXT_NEAR_DUPLICATE",
                                group_key="DUPLICATE",
                                severity="MEDIUM",
                                reason=f"Extracted document text exhibits {int(sim * 100)}% similarity with document #{cand.id} ('{cand.original_filename}'); potential anomaly requiring verification.",
                                evidence=[{
                                    "document_id": doc.id,
                                    "duplicate_with_id": cand.id,
                                    "duplicate_filename": cand.original_filename,
                                    "text_similarity": round(sim, 3),
                                    "threshold": settings.ANOMALY_DUPLICATE_TEXT_SIMILARITY_THRESHOLD,
                                }],
                                confidence=round(sim, 2),
                                recommended_action="Inspect text contents to verify statutory distinction between filings.",
                            )
                        )

        return flags

