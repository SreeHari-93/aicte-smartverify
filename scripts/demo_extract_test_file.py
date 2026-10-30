import sys
sys.path.insert(0, ".")

from backend.app.database import SessionLocal
from backend.app.models.document_type import DocumentType
from backend.app.services.document_pipeline.extractor import DocumentExtractor
from backend.app.services.document_pipeline.classifier import DocumentClassifier

db = SessionLocal()
dts = db.query(DocumentType).filter(DocumentType.is_active == True).all()

text = """Fire & Life Safety No Objection Certificate
Certificate Number: FSNOC-SKCET-2026-VAL
Issued To: Sri Krishna College of Engineering and Technology
Building Name: Sri Krishna College of Engineering and Technology
Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008
AICTE Institute ID: SKCET01
Date of Issue: 02-07-2026
Valid Upto: 02-07-2027"""

cls_res = DocumentClassifier.classify(text, dts)
fire_dt = next((d for d in dts if d.code == "FIRE_NOC"), None)
ext = DocumentExtractor.extract_fields(text, fire_dt)

print("=" * 60)
print(f"CLASSIFICATION RESULT: {cls_res.predicted_type} (Score: {cls_res.score:.2%})")
print("=" * 60)
print("EXTRACTED FIELDS:")
for f in ext.fields:
    print(f"  • {f.key:18}: {f.value}  [normalized: {f.normalized_value}]")
print("-" * 60)
print(f"Document Level Issue Date : {ext.issue_date}")
print(f"Document Level Expiry Date: {ext.expiry_date}")
print(f"Days Remaining            : {ext.days_remaining}")
print(f"Is Expired                : {ext.is_expired}")
print("=" * 60)
db.close()

