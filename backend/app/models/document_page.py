from sqlalchemy import Column, Integer, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_no = Column(Integer, nullable=False)
    text = Column(Text, nullable=False, default="")
    words_json = Column(JSON, default=list, nullable=False)  # List of {word: str, bbox: [x0, y0, x1, y1], confidence: float}
    width = Column(Float, nullable=False, default=0.0)
    height = Column(Float, nullable=False, default=0.0)

    document = relationship("Document", back_populates="pages")

