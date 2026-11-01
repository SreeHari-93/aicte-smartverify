"""
Institute Record Adapter (SIMULATED)
Simulates fetching institutional master records and historical approval decisions
from the National AICTE Institute Registry (NIER/APH Master DB).

Features:
- Fetches institute master profile and verified council registration metadata.
- Retrieves multi-year approval history (2021-2025).
- Strictly read-only; never alters institutional ownership or bypasses permissions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.integrations.base import BaseIntegrationAdapter
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.services.audit_service import AuditService


class InstituteRecordAdapter(BaseIntegrationAdapter):
    """
    SIMULATED Institute Record Adapter for legacy AICTE Institute Master Registry.
    """

    def __init__(self):
        super().__init__(
            name="InstituteRecordAdapter",
            adapter_type="INSTITUTE_MASTER_REGISTRY",
            is_simulated=True,
        )
        self.registry_endpoint = "https://simulated-registry.aicte-india.org/api/v1/institutes"

    def health_check(self) -> Dict[str, Any]:
        return {
            "adapter": self.name,
            "status": "HEALTHY",
            "is_simulated": True,
            "endpoint": self.registry_endpoint,
            "latency_ms": 22,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.adapter_type,
            "is_simulated": True,
            "capabilities": ["FETCH_PROFILE", "APPROVAL_HISTORY", "ACCREDITATION_LOOKUP"],
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_message": self.last_sync_message,
        }

    def fetch_institute_profile(
        self,
        db: Session,
        institute_id: int,
        operator_user_id: Optional[int] = None,
        operator_role: str = "OFFICER",
    ) -> Dict[str, Any]:
        """
        Fetch external verified profile and historical approvals for an institute.
        """
        inst = db.query(Institute).filter(Institute.id == institute_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Institution not found in local registry.")

        now = datetime.now(timezone.utc)
        self.last_sync = now
        self.last_sync_status = "SUCCESS"
        self.last_sync_message = f"Fetched external master record for {inst.name} ({inst.aicte_institute_id})"

        # Generate simulated past approval decisions from 2021 to 2025
        past_approvals = [
            {
                "academic_year": "2025-2026",
                "category": "Extension of Approval (EoA)",
                "decision": "APPROVED",
                "order_number": f"AICTE/SOUTH/2025/{inst.aicte_institute_id}/EOA",
                "sanctioned_intake": 420,
                "issued_on": "2025-05-18",
            },
            {
                "academic_year": "2024-2025",
                "category": "Extension of Approval (EoA)",
                "decision": "APPROVED",
                "order_number": f"AICTE/SOUTH/2024/{inst.aicte_institute_id}/EOA",
                "sanctioned_intake": 360,
                "issued_on": "2024-05-22",
            },
            {
                "academic_year": "2023-2024",
                "category": "Increase in Intake",
                "decision": "APPROVED",
                "order_number": f"AICTE/SOUTH/2023/{inst.aicte_institute_id}/INTAKE",
                "sanctioned_intake": 360,
                "issued_on": "2023-06-04",
            },
        ]

        # Audit log for external record access
        AuditService.log(
            db=db,
            action="INTEGRATION_INSTITUTE_LOOKUP",
            user_id=operator_user_id,
            role=operator_role,
            reason=f"Queried simulated external institute profile for #{inst.id} ({inst.name})",
            details={
                "institute_id": inst.id,
                "aicte_id": inst.aicte_institute_id,
                "adapter": self.name,
                "is_simulated": True,
            },
        )

        return {
            "adapter": self.name,
            "is_simulated": True,
            "institute_id": inst.id,
            "aicte_institute_id": inst.aicte_institute_id,
            "name": inst.name,
            "state": inst.state,
            "status": inst.status,
            "external_registry_status": "VERIFIED_ACTIVE",
            "establishment_year": 2001,
            "trust_society_name": f"{inst.name} Educational & Charitable Trust",
            "historical_approvals": past_approvals,
            "compliance_standing": "IN_GOOD_STANDING",
            "last_synced_at": now.isoformat(),
        }

