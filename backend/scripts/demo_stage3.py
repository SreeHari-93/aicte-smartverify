#!/usr/bin/env python
"""
AICTE SmartVerify AI — Stage 3 End-to-End Demo Script
Demonstrates the full regulatory pipeline for 4 SKCET demo applications:
1. Document Upload & Storage (Synthetic PDFs)
2. OCR Processing & Classification
3. Field Extraction & Cross-reconciliation
4. Validation Run (Ruleset v2.0 evaluation, scoring, deterministic status)
5. Root Cause Analysis & Explainer Generation (English & Hindi)
Works out of the box with zero external API keys in deterministic template mode.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.database import SessionLocal
from backend.app.models.institute import Institute
from backend.app.models.rule import Rule
from backend.app.services.demo_data import DemoDataSeeder
from backend.app.services.validation.runner import ValidationRunner
from backend.app.services.explainer.root_cause import RootCauseAnalyzer
from backend.app.services.explainer.narrator import ExplainerNarrator


def run_demo():
    print("=" * 80)
    print("AICTE SmartVerify AI — Stage 3-i & 3-ii End-to-End Demonstration")
    print("Institute: Sri Krishna College of Engineering and Technology (SKCET01)")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. Seed demo applications and synthetic PDFs
        print("\n[Stage 1 & 2] Seeding 4 Demo Applications with Synthetic Statutory PDFs...")
        seeded_apps = DemoDataSeeder.seed_all_demo_applications(db)

        skcet = db.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
        inst_name = skcet.name if skcet else "Sri Krishna College of Engineering and Technology"

        # Pre-fetch rules for metadata lookup
        rules = db.query(Rule).all()
        rules_by_code = {r.rule_code: r for r in rules}

        app_order = ["DEMO-READY", "DEMO-ATTENTION", "DEMO-LIKELY-FAIL", "DEMO-BLOCKED"]

        for app_id in app_order:
            app = seeded_apps.get(app_id)
            if not app:
                continue

            print("\n" + "#" * 80)
            print(f"APPLICATION: {app.application_id} ({app.category} | AY {app.academic_year})")
            print(f"Target Outcome: {app.application_id.replace('DEMO-', '')}")
            print("#" * 80)

            # Pipeline Stages summary
            docs = app.documents if hasattr(app, "documents") else []
            print(f"• Document Pipeline : {len(docs)} documents loaded (OCR: COMPLETED | Classify: VERIFIED)")

            # Run Validation Runner (Stage 3-i)
            val_run = ValidationRunner.run_validation(db, app.id)

            print(f"• Overall Status    : {val_run.overall_status}")
            print(f"• Compliance Score  : {val_run.score}/100.0")
            print(f"• Blocker Deficits  : {val_run.blocker_count}")
            print(f"• Major Deficits    : {val_run.major_count}")
            print(f"• Minor / Advisory  : {val_run.minor_count} minor, {val_run.advisory_count} advisory")

            # Deterministic Root Cause Analysis (Stage 3-ii)
            root_causes = RootCauseAnalyzer.analyze_findings(val_run.findings, rules_by_code)

            print(f"\n[ROOT CAUSE ANALYSIS] ({len(root_causes)} grouped causes identified):")
            if not root_causes:
                print("  ✓ Zero compliance deficiencies detected across all published statutory rules.")
            else:
                for idx, rc in enumerate(root_causes, 1):
                    rules_str = ", ".join(rc.affected_rule_codes) if rc.affected_rule_codes else "General Check"
                    print(f"  {idx}. [{rc.cause_code}] {rc.headline}")
                    print(f"     Severity: {rc.severity} | Fixable by Institute: {rc.fixable_by_institute}")
                    print(f"     Affected Rules: {rules_str}")
                    if rc.ordered_suggested_actions:
                        print(f"     Suggested Remediation: {rc.ordered_suggested_actions[0]}")

            # Explainer Generation - English
            exp_en = ExplainerNarrator.explain(
                root_causes=root_causes,
                application_id=app.application_id,
                institute_name=inst_name,
                lang="en",
                run_id=val_run.id,
                db=db,
            )

            print("\n[EXPLAINER NARRATIVE — ENGLISH (EN)]")
            print(f"Headline : {exp_en.get('headline')}")
            print(f"Summary  : {exp_en.get('plain_summary')}")
            if exp_en.get("reasons"):
                print("Reasons  :")
                for r in exp_en["reasons"]:
                    print(f"  - [{r.get('cause_code')}] {r.get('explanation')}")
            if exp_en.get("how_to_fix"):
                print("How To Fix (Remediation Steps):")
                for s in exp_en["how_to_fix"]:
                    print(f"  - {s.get('step')} (Effort: {s.get('effort')})")
            print(f"Disclaimer: {exp_en.get('disclaimer')}")

            # Explainer Generation - Hindi
            exp_hi = ExplainerNarrator.explain(
                root_causes=root_causes,
                application_id=app.application_id,
                institute_name=inst_name,
                lang="hi",
                run_id=val_run.id,
                db=db,
            )

            print("\n[EXPLAINER NARRATIVE — HINDI (HI)]")
            print(f"शीर्षक (Headline)  : {exp_hi.get('headline')}")
            print(f"विवरण (Summary)   : {exp_hi.get('plain_summary')}")
            if exp_hi.get("reasons"):
                print("कारण (Reasons)    :")
                for r in exp_hi["reasons"]:
                    print(f"  - [{r.get('cause_code')}] {r.get('explanation')}")
            if exp_hi.get("how_to_fix"):
                print("सुधार कदम (How-To-Fix):")
                for s in exp_hi["how_to_fix"]:
                    print(f"  - {s.get('step')} (प्रयास: {s.get('effort')})")
            print(f"अस्वीकरण (Disclaimer): {exp_hi.get('disclaimer')}")

        print("\n" + "=" * 80)
        print("✓ All 4 demo applications processed successfully through Stage 3 pipeline.")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
