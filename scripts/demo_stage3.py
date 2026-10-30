import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import SessionLocal
from backend.app.services.demo_data import DemoDataSeeder
from backend.app.services.validation.runner import ValidationRunner
from backend.app.models.application import Application


def run_stage3_demo():
    print("=" * 70)
    print("AICTE SmartVerify AI — Stage 3 Validation Scrutiny Demo")
    print("=" * 70)
    db = SessionLocal()
    try:
        print("\n[+] Seeding Stage 3 demo applications (DEMO-READY, DEMO-ATTENTION, DEMO-LIKELY-FAIL, DEMO-BLOCKED)...")
        app_ids = DemoDataSeeder.seed_all_demo_applications(db)
        print(f"    Seeded {len(app_ids)} applications: {', '.join(app_ids)}")

        for app_id in app_ids:
            app = db.query(Application).filter(Application.application_id == app_id).first()
            if not app:
                continue
            val_run = ValidationRunner.run_validation(db=db, application_id=app.id)
            print(f"\n---> Application: {app.application_id} ({app.category})")
            print(f"     Status: {val_run.overall_status}")
            print(f"     Score:  {val_run.score:.1f}/100")
            print(f"     Blockers: {val_run.blocker_count} | Major: {val_run.major_count} | Minor: {val_run.minor_count}")
            print(f"     Total Findings: {len(val_run.findings)}")
            for f in val_run.findings[:3]:
                print(f"       - [{f.status}] {f.rule_code}: {f.reason}")
        print("\n" + "=" * 70)
        print("Stage 3 Demo Completed Successfully.")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    run_stage3_demo()

