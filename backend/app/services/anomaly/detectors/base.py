import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import pymupdf  # PyMuPDF
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.document import Document
from backend.app.models.application import Application
from backend.app.models.document_type import DocumentType
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


class DetectionContext:
    def __init__(
        self,
        db: Session,
        document: Document,
        application: Optional[Application] = None,
        doc_type: Optional[DocumentType] = None,
        extracted_fields: Optional[Dict[str, Any]] = None,
    ):
        self.db = db
        self.document = document
        self.application = application
        self.doc_type = doc_type
        self.extracted_fields = extracted_fields or {}
        self._rendered_pages: Optional[List[Tuple[int, Image.Image]]] = None
        self._full_text: Optional[str] = None

    def get_rendered_pages(self, max_pages: int = 3) -> List[Tuple[int, Image.Image]]:
        """
        Renders PDF pages or loads image files as PIL Images (memoized).
        Returns list of (page_number, PIL.Image).
        """
        if self._rendered_pages is not None:
            return self._rendered_pages

        results: List[Tuple[int, Image.Image]] = []
        file_path = self.document.file_path

        if not file_path or not os.path.exists(file_path):
            self._rendered_pages = []
            return self._rendered_pages

        try:
            if file_path.lower().endswith(".pdf"):
                doc_pdf = pymupdf.open(file_path)
                num_pages = min(len(doc_pdf), max_pages)
                for page_idx in range(num_pages):
                    page = doc_pdf[page_idx]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    results.append((page_idx + 1, img))
                doc_pdf.close()
            elif any(file_path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                img = Image.open(file_path).convert("RGB")
                results.append((1, img))
        except Exception:
            results = []

        self._rendered_pages = results
        return self._rendered_pages

    def get_document_text(self) -> str:
        """
        Returns full concatenated text from document pages or OCR.
        """
        if self._full_text is not None:
            return self._full_text

        text_parts = []
        if self.document.pages:
            for p in self.document.pages:
                if p.text:
                    text_parts.append(p.text)

        if not text_parts and self.document.file_path and self.document.file_path.lower().endswith(".pdf"):
            try:
                doc_pdf = pymupdf.open(self.document.file_path)
                for page in doc_pdf:
                    text_parts.append(page.get_text() or "")
                doc_pdf.close()
            except Exception:
                pass

        self._full_text = " ".join(text_parts).strip()
        return self._full_text


class BaseDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        pass


class DetectorRegistry:
    _registry: List[BaseDetector] = []

    @classmethod
    def register(cls, detector_instance: BaseDetector):
        cls._registry.append(detector_instance)

    @classmethod
    def get_detectors(cls) -> List[BaseDetector]:
        return list(cls._registry)

    @classmethod
    def clear(cls):
        cls._registry.clear()

