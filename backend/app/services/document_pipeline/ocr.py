import io
import os
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from PIL import Image

logger = logging.getLogger("document_pipeline")

import pymupdf as fitz
from rapidocr_onnxruntime import RapidOCR

from backend.app.database import SessionLocal
from backend.app.models.document import Document
from backend.app.models.document_page import DocumentPage
from backend.app.models.document_type import DocumentType
from backend.app.models.document_classification import DocumentClassification
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.audit_log import AuditLog
from backend.app.services.audit_service import AuditService


class WordBox(BaseModel):
    word: str
    bbox: List[float] = Field(..., description="[x0, y0, x1, y1] coordinates")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class PageOCRResult(BaseModel):
    page_no: int
    text: str
    words: List[WordBox] = Field(default_factory=list)
    width: float
    height: float
    confidence: float = 1.0


class DocumentOCRResult(BaseModel):
    engine: str
    page_count: int
    pages: List[PageOCRResult] = Field(default_factory=list)
    full_text: str = ""
    overall_confidence: float = 1.0
    language: str = "en"
    status: str = "DONE"  # PENDING | PROCESSING | DONE | FAILED | MANUAL
    error_message: Optional[str] = None


class BaseOCREngine(ABC):
    @abstractmethod
    def process_document(
        self, file_path: str, mime_type: str, max_pages: int = 20, timeout_sec: int = 60
    ) -> DocumentOCRResult:
        pass


class PyMuPDFEngine(BaseOCREngine):
    """
    Fast, high-fidelity native text extraction for digital PDFs.
    Extracts selectable text and per-word bounding boxes.
    """

    def process_document(
        self, file_path: str, mime_type: str, max_pages: int = 20, timeout_sec: int = 60
    ) -> DocumentOCRResult:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_process = min(total_pages, max_pages)

        pages_result: List[PageOCRResult] = []
        full_text_list: List[str] = []
        total_words_count = 0

        for page_idx in range(pages_to_process):
            page = doc[page_idx]
            # Handle page dimensions taking rotation into account
            rect = page.rect
            width = float(rect.width)
            height = float(rect.height)

            raw_text = page.get_text("text") or ""
            words_raw = page.get_text("words") or []

            word_boxes: List[WordBox] = []
            for w in words_raw:
                # w is (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                if len(w) >= 5:
                    w_text = str(w[4]).strip()
                    if w_text:
                        word_boxes.append(
                            WordBox(
                                word=w_text,
                                bbox=[
                                    round(float(w[0]), 2),
                                    round(float(w[1]), 2),
                                    round(float(w[2]), 2),
                                    round(float(w[3]), 2),
                                ],
                                confidence=0.99,
                            )
                        )

            total_words_count += len(word_boxes)
            full_text_list.append(raw_text.strip())

            pages_result.append(
                PageOCRResult(
                    page_no=page_idx + 1,
                    text=raw_text.strip(),
                    words=word_boxes,
                    width=width,
                    height=height,
                    confidence=0.99 if word_boxes else 1.0,
                )
            )

        doc.close()

        full_text = "\n\n".join(t for t in full_text_list if t)

        # If digital text exists, return successful native extraction
        return DocumentOCRResult(
            engine="pymupdf",
            page_count=pages_to_process,
            pages=pages_result,
            full_text=full_text,
            overall_confidence=0.98 if total_words_count > 0 else 0.5,
            language="en",
            status="DONE",
            error_message=None,
        )


class RapidOCREngine(BaseOCREngine):
    """
    Neural OCR engine using rapidocr-onnxruntime for scanned documents and image files.
    Renders PDF pages at 200 DPI for optimal accuracy.
    """

    def __init__(self):
        self._ocr = RapidOCR()

    def process_document(
        self, file_path: str, mime_type: str, max_pages: int = 20, timeout_sec: int = 60
    ) -> DocumentOCRResult:
        start_time = time.time()
        pages_result: List[PageOCRResult] = []
        full_text_list: List[str] = []
        all_confidences: List[float] = []

        is_pdf = mime_type.lower() == "application/pdf" or file_path.lower().endswith(".pdf")

        if is_pdf:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            pages_to_process = min(total_pages, max_pages)

            for page_idx in range(pages_to_process):
                if time.time() - start_time > timeout_sec:
                    break

                page = doc[page_idx]
                rect = page.rect
                page_width = float(rect.width)
                page_height = float(rect.height)

                # Render page at 200 DPI
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")

                page_text, word_boxes, page_conf = self._run_rapidocr_on_bytes(img_bytes)

                all_confidences.append(page_conf)
                full_text_list.append(page_text)

                pages_result.append(
                    PageOCRResult(
                        page_no=page_idx + 1,
                        text=page_text,
                        words=word_boxes,
                        width=page_width,
                        height=page_height,
                        confidence=page_conf,
                    )
                )

            doc.close()
            page_count = len(pages_result)

        else:
            # Single image file (JPG, PNG, JPEG)
            with open(file_path, "rb") as f:
                img_bytes = f.read()

            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                img_width, img_height = pil_img.size

            page_text, word_boxes, page_conf = self._run_rapidocr_on_bytes(img_bytes)

            all_confidences.append(page_conf)
            full_text_list.append(page_text)
            pages_result.append(
                PageOCRResult(
                    page_no=1,
                    text=page_text,
                    words=word_boxes,
                    width=float(img_width),
                    height=float(img_height),
                    confidence=page_conf,
                )
            )
            page_count = 1

        overall_conf = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )
        full_text = "\n\n".join(t for t in full_text_list if t)

        return DocumentOCRResult(
            engine="rapidocr",
            page_count=page_count,
            pages=pages_result,
            full_text=full_text,
            overall_confidence=round(overall_conf, 3),
            language="en",
            status="DONE" if overall_conf >= 0.5 else "MANUAL",
            error_message=None,
        )

    def _run_rapidocr_on_bytes(
        self, img_bytes: bytes
    ) -> Tuple[str, List[WordBox], float]:
        """Runs RapidOCR on image bytes and returns (text, word_boxes, confidence)"""
        try:
            result, _ = self._ocr(img_bytes)
            if not result:
                return "", [], 1.0  # Clean empty page

            line_texts = []
            word_boxes: List[WordBox] = []
            scores = []

            for item in result:
                # item is [dt_boxes, rec_res, score]
                # dt_boxes: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                dt_boxes, text, score = item
                text_clean = str(text).strip()
                if not text_clean:
                    continue

                line_texts.append(text_clean)
                scores.append(float(score))

                # Calculate bounding box
                xs = [p[0] for p in dt_boxes]
                ys = [p[1] for p in dt_boxes]
                bbox = [
                    round(float(min(xs)), 2),
                    round(float(min(ys)), 2),
                    round(float(max(xs)), 2),
                    round(float(max(ys)), 2),
                ]

                # Segment text into words for granular token matching
                words = text_clean.split()
                if len(words) == 1:
                    word_boxes.append(WordBox(word=words[0], bbox=bbox, confidence=round(float(score), 3)))
                else:
                    # Distribute x span across words proportionally
                    w_width = (bbox[2] - bbox[0]) / max(len(words), 1)
                    for i, w in enumerate(words):
                        w_x0 = round(bbox[0] + i * w_width, 2)
                        w_x1 = round(w_x0 + w_width, 2)
                        word_boxes.append(
                            WordBox(
                                word=w,
                                bbox=[w_x0, bbox[1], w_x1, bbox[3]],
                                confidence=round(float(score), 3),
                            )
                        )

            avg_score = sum(scores) / len(scores) if scores else 1.0
            full_text = "\n".join(line_texts)
            return full_text, word_boxes, round(avg_score, 3)

        except Exception as e:
            return "", [], 0.0


class OCRService:
    """
    Unified OCR Service orchestrating native PDF extraction and RapidOCR fallback.
    Enforces maximum 20 pages, 60s timeout, non-blocking background execution,
    and automatic fallback to 'MANUAL' review on edge-case failures.
    """

    MAX_PAGES = 20
    TIMEOUT_SECONDS = 60

    _pymupdf_engine = PyMuPDFEngine()
    _rapidocr_engine: Optional[RapidOCREngine] = None

    @classmethod
    def get_rapidocr_engine(cls) -> RapidOCREngine:
        if cls._rapidocr_engine is None:
            cls._rapidocr_engine = RapidOCREngine()
        return cls._rapidocr_engine

    @classmethod
    def process_file(
        cls, file_path: str, mime_type: str = "application/pdf"
    ) -> DocumentOCRResult:
        if not os.path.exists(file_path):
            return DocumentOCRResult(
                engine="none",
                page_count=0,
                status="FAILED",
                error_message=f"File not found: {file_path}",
                overall_confidence=0.0,
            )

        # Check if file is completely corrupted
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return DocumentOCRResult(
                    engine="none",
                    page_count=0,
                    status="FAILED",
                    error_message="Uploaded document is empty (0 bytes).",
                    overall_confidence=0.0,
                )
        except Exception as e:
            return DocumentOCRResult(
                engine="none",
                page_count=0,
                status="FAILED",
                error_message=f"Could not access file: {str(e)}",
                overall_confidence=0.0,
            )

        is_pdf = mime_type.lower() == "application/pdf" or file_path.lower().endswith(".pdf")

        if is_pdf:
            # 1. Attempt native digital PDF extraction via PyMuPDF
            try:
                res_pymupdf = cls._pymupdf_engine.process_document(
                    file_path=file_path,
                    mime_type=mime_type,
                    max_pages=cls.MAX_PAGES,
                    timeout_sec=cls.TIMEOUT_SECONDS,
                )

                # Check if native extraction yielded sufficient text
                total_text_len = sum(len(p.text.strip()) for p in res_pymupdf.pages)
                total_words = sum(len(p.words) for p in res_pymupdf.pages)

                if total_text_len >= 20 or total_words >= 5:
                    return res_pymupdf

                # If text is empty or sparse, the PDF is likely scanned. Fallback to RapidOCR!
            except Exception as e:
                # PDF corrupted or PyMuPDF error -> try rapidocr or fail gracefully
                pass

            # 2. Run RapidOCR on rendered 200 DPI pages
            try:
                engine = cls.get_rapidocr_engine()
                return engine.process_document(
                    file_path=file_path,
                    mime_type=mime_type,
                    max_pages=cls.MAX_PAGES,
                    timeout_sec=cls.TIMEOUT_SECONDS,
                )
            except Exception as e:
                return DocumentOCRResult(
                    engine="rapidocr",
                    page_count=0,
                    status="FAILED",
                    error_message=f"OCR execution failed on document: {str(e)}",
                    overall_confidence=0.0,
                )

        else:
            # Image file (PNG / JPG / JPEG)
            try:
                engine = cls.get_rapidocr_engine()
                return engine.process_document(
                    file_path=file_path,
                    mime_type=mime_type,
                    max_pages=1,
                    timeout_sec=cls.TIMEOUT_SECONDS,
                )
            except Exception as e:
                return DocumentOCRResult(
                    engine="rapidocr",
                    page_count=0,
                    status="FAILED",
                    error_message=f"Image OCR failed: {str(e)}",
                    overall_confidence=0.0,
                )

    @classmethod
    def _get_active_session(cls) -> Tuple[Any, bool]:
        """Returns (db, should_close). Respects dependency overrides during testing."""
        try:
            from backend.app.main import app
            from backend.app.database import get_db
            if get_db in app.dependency_overrides:
                override = app.dependency_overrides[get_db]
                res = override()
                if hasattr(res, "__next__"):
                    return next(res), False
                return res, False
        except Exception:
            pass
        return SessionLocal(), True

    @classmethod
    def run_document_ocr_task(cls, document_id: int):
        """
        Background task to run OCR processing asynchronously.
        Executes: OCR -> Classification -> Extraction -> Verification -> Anomaly Scan.
        Never crashes the request thread and logs status transitions to AuditLog and logger.
        """
        db, should_close = cls._get_active_session()
        start_time = time.time()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.warning(f"[JOB ABORTED] Document #{document_id} not found in database.")
                return

            logger.info(f"[JOB START] Document #{doc.id} ('{doc.original_filename}') - beginning processing pipeline...")

            doc.ocr_status = "PROCESSING"
            doc.status = "Processing"
            db.commit()

            AuditService.log_event(
                db=db,
                action="DOCUMENT_OCR_PROCESSING",
                user_id=None,
                role="SYSTEM",
                reason=f"Started asynchronous OCR pipeline for document ID {doc.id} ({doc.original_filename})",
                details={"document_id": doc.id, "file_path": doc.file_path},
            )

            # Execute OCR pipeline
            ocr_result = cls.process_file(file_path=doc.file_path, mime_type=doc.mime_type)

            # Clear any previously saved pages for this document (idempotent / reprocess)
            db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()

            # Populate DocumentPage records
            for p in ocr_result.pages:
                dp = DocumentPage(
                    document_id=doc.id,
                    page_no=p.page_no,
                    text=p.text,
                    words_json=[w.model_dump() for w in p.words],
                    width=p.width,
                    height=p.height,
                )
                db.add(dp)

            # Update Document OCR attributes
            doc.ocr_status = ocr_result.status
            doc.ocr_engine = ocr_result.engine
            doc.ocr_confidence = ocr_result.overall_confidence
            doc.page_count = ocr_result.page_count
            doc.language = ocr_result.language
            doc.processed_at = datetime.now(timezone.utc)
            doc.error_message = ocr_result.error_message

            # Save full extracted text into extracted_data
            updated_ocr_data = dict(doc.extracted_data or {})
            updated_ocr_data["full_text"] = ocr_result.full_text
            updated_ocr_data["ocr_engine"] = ocr_result.engine
            updated_ocr_data["ocr_confidence"] = ocr_result.overall_confidence
            doc.extracted_data = updated_ocr_data

            if ocr_result.status == "FAILED":
                doc.status = "Failed – retry available"
                db.commit()
                logger.error(f"[JOB OCR FAILED] Document #{doc.id}: {ocr_result.error_message}")
                AuditService.log_event(
                    db=db,
                    action="DOCUMENT_OCR_FAILED",
                    user_id=None,
                    role="SYSTEM",
                    reason=f"OCR pipeline failed for document ID {doc.id}: {ocr_result.error_message}",
                    details={"document_id": doc.id, "error": ocr_result.error_message},
                )
                return

            db.commit()
            logger.info(
                f"[JOB OCR DONE] Document #{doc.id}: engine={ocr_result.engine}, "
                f"pages={ocr_result.page_count}, confidence={ocr_result.overall_confidence:.2f}, "
                f"text_length={len(ocr_result.full_text or '')}"
            )

            AuditService.log_event(
                db=db,
                action="DOCUMENT_OCR_COMPLETED",
                user_id=None,
                role="SYSTEM",
                reason=f"OCR pipeline finished with status '{ocr_result.status}' for document ID {doc.id}",
                details={
                    "document_id": doc.id,
                    "ocr_status": ocr_result.status,
                    "ocr_engine": ocr_result.engine,
                    "ocr_confidence": ocr_result.overall_confidence,
                    "page_count": ocr_result.page_count,
                    "error_message": ocr_result.error_message,
                },
            )

            # ------------------------------------------------------------------
            # Run Classification and Extraction automatically after OCR
            # ------------------------------------------------------------------
            all_dts = db.query(DocumentType).filter(DocumentType.is_active == True).all()
            cls_res = None
            try:
                from backend.app.services.document_pipeline.classifier import DocumentClassifier

                cls_res = DocumentClassifier.classify(
                    ocr_text=ocr_result.full_text or "",
                    document_types=all_dts,
                    uploaded_code=doc.document_type_code,
                )

                classification = (
                    db.query(DocumentClassification)
                    .filter(DocumentClassification.document_id == doc.id)
                    .first()
                )
                if not classification:
                    classification = DocumentClassification(document_id=doc.id)
                    db.add(classification)

                classification.predicted_type = cls_res.predicted_type
                classification.score = cls_res.score
                classification.candidates_json = [c.model_dump() for c in cls_res.candidates]
                classification.mismatch_flag = cls_res.mismatch_flag
                classification.warning_message = cls_res.warning_message
                db.commit()

                logger.info(
                    f"[JOB CLASSIFIED] Document #{doc.id}: predicted_type='{cls_res.predicted_type}' "
                    f"(score={cls_res.score:.2f}, mismatch={cls_res.mismatch_flag})"
                )

                AuditService.log_event(
                    db=db,
                    action="DOCUMENT_CLASSIFIED",
                    user_id=None,
                    role="SYSTEM",
                    reason=f"Document ID {doc.id} classified as '{cls_res.predicted_type}' (Score: {cls_res.score}, Mismatch: {cls_res.mismatch_flag})",
                    details={
                        "document_id": doc.id,
                        "predicted_type": cls_res.predicted_type,
                        "score": cls_res.score,
                        "mismatch_flag": cls_res.mismatch_flag,
                        "warning_message": cls_res.warning_message,
                    },
                )
            except Exception as cls_err:
                logger.warning(f"[JOB CLASSIFICATION ERROR] Document #{doc.id}: {cls_err}")

            # Determine DocumentType for extraction schema
            target_dt = None
            if doc.document_type:
                target_dt = doc.document_type
            elif doc.document_type_code:
                target_dt = next((dt for dt in all_dts if dt.code.upper() == doc.document_type_code.upper()), None)
            if not target_dt and cls_res:
                target_dt = next((dt for dt in all_dts if dt.code.upper() == cls_res.predicted_type.upper()), None)

            extracted_fields_count = 0
            has_review_needed = False
            if target_dt:
                try:
                    from backend.app.services.document_pipeline.extractor import DocumentExtractor

                    pages_info = [
                        {"page_no": p.page_no, "words": [w.model_dump() for w in p.words]}
                        for p in ocr_result.pages
                    ]
                    ext_res = DocumentExtractor.extract_fields(
                        ocr_text=ocr_result.full_text or "",
                        doc_type=target_dt,
                        pages_info=pages_info,
                        document_id=doc.id,
                    )

                    # Delete unverified fields for idempotency
                    db.query(ExtractedField).filter(
                        ExtractedField.document_id == doc.id,
                        ExtractedField.verified_by_user == False,
                    ).delete()

                    for f in ext_res.fields:
                        existing = (
                            db.query(ExtractedField)
                            .filter(
                                ExtractedField.document_id == doc.id,
                                ExtractedField.key == f.key,
                            )
                            .first()
                        )
                        if existing and existing.verified_by_user:
                            continue

                        ef = ExtractedField(
                            document_id=doc.id,
                            key=f.key,
                            value=f.value,
                            normalized_value=f.normalized_value,
                            confidence=f.confidence,
                            page_no=f.page_no,
                            bbox_json=f.bbox,
                            source=f.source,
                            needs_review=f.needs_review,
                            verified_by_user=False,
                        )
                        db.add(ef)

                    updated_ext_data = dict(doc.extracted_data or {})
                    for f in ext_res.fields:
                        if f.key and f.value:
                            updated_ext_data[f.key] = f.normalized_value or f.value
                    updated_ext_data["expiry_date"] = ext_res.expiry_date
                    updated_ext_data["issue_date"] = ext_res.issue_date
                    updated_ext_data["is_expired"] = ext_res.is_expired
                    updated_ext_data["days_remaining"] = ext_res.days_remaining
                    if cls_res:
                        updated_ext_data["classification"] = {
                            "predicted_type": cls_res.predicted_type,
                            "score": cls_res.score,
                            "mismatch_flag": cls_res.mismatch_flag,
                            "warning_message": cls_res.warning_message,
                        }
                    doc.extracted_data = updated_ext_data

                    extracted_fields_count = len(ext_res.fields)
                    has_review_needed = any(f.needs_review for f in ext_res.fields)

                    AuditService.log_event(
                        db=db,
                        action="DOCUMENT_EXTRACTED",
                        user_id=None,
                        role="SYSTEM",
                        reason=f"Extracted {len(ext_res.fields)} fields for document ID {doc.id} (Expiry: {ext_res.expiry_date})",
                        details={
                            "document_id": doc.id,
                            "fields_count": len(ext_res.fields),
                            "expiry_date": ext_res.expiry_date,
                            "is_expired": ext_res.is_expired,
                            "days_remaining": ext_res.days_remaining,
                        },
                    )
                    logger.info(f"[JOB EXTRACTION DONE] Document #{doc.id}: extracted {extracted_fields_count} fields.")
                except Exception as ext_err:
                    logger.warning(f"[JOB EXTRACTION ERROR] Document #{doc.id}: {ext_err}")

            # Update overall document status
            mismatch = cls_res.mismatch_flag if cls_res else False
            if mismatch or has_review_needed:
                doc.status = "Needs Attention"
            else:
                doc.status = "Verified"
            db.commit()

            # Automatically register or update DocumentValidityRecord if expiry date is present
            try:
                from backend.app.services.validity_service import ValidityService
                ValidityService.register_or_update_document_validity(db, doc)
            except Exception as val_reg_err:
                logger.warning(f"[JOB VALIDITY REGISTER NOTE] Document #{doc.id}: {val_reg_err}")

            # ------------------------------------------------------------------
            # Statutory Verification is ALWAYS triggered when OCR/Extraction finish
            # ------------------------------------------------------------------
            try:
                from backend.app.services.verification import VerificationService
                logger.info(f"[JOB VERIFICATION START] Document #{doc.id}: running statutory verification...")
                ver_res = VerificationService.verify_document(db=db, document_id=doc.id, triggered_by=None)
                logger.info(
                    f"[JOB VERIFICATION FINISHED] Document #{doc.id}: "
                    f"status='{ver_res.status}', source='{ver_res.source_name}'"
                )
            except Exception as ver_err:
                logger.error(f"[JOB VERIFICATION ERROR] Document #{doc.id}: {ver_err}", exc_info=True)

            # ------------------------------------------------------------------
            # Anomaly Screening is triggered automatically
            # ------------------------------------------------------------------
            try:
                from backend.app.services.anomaly import AnomalyService
                logger.info(f"[JOB ANOMALY SCAN START] Document #{doc.id}: running preliminary anomaly detection...")
                _, flags = AnomalyService.scan_document(db=db, document_id=doc.id)
                logger.info(f"[JOB ANOMALY SCAN FINISHED] Document #{doc.id}: {len(flags)} preliminary indicators recorded.")
            except Exception as anom_err:
                logger.warning(f"[JOB ANOMALY SCAN NOTE] Document #{doc.id}: {anom_err}")

            elapsed = time.time() - start_time
            logger.info(
                f"[JOB FINISHED] Document #{doc.id} ('{doc.original_filename}') completed in {elapsed:.2f}s "
                f"with status='{doc.status}', ocr_status='{doc.ocr_status}', "
                f"verification_status='{doc.verification_status}'"
            )

        except Exception as e:
            logger.error(f"[JOB CRITICAL ERROR] Document #{document_id} pipeline crashed: {str(e)}", exc_info=True)
            db.rollback()
            try:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if doc:
                    doc.ocr_status = "FAILED"
                    doc.status = "Failed – retry available"
                    doc.error_message = f"Processing error: {str(e)}"
                    doc.processed_at = datetime.now(timezone.utc)
                    db.commit()

                    AuditService.log_event(
                        db=db,
                        action="DOCUMENT_OCR_FAILED",
                        user_id=None,
                        role="SYSTEM",
                        reason=f"OCR pipeline uncaught error for document ID {document_id}: {str(e)}",
                        details={"document_id": document_id, "error": str(e)},
                    )
            except Exception:
                pass
        finally:
            if should_close:
                db.close()
