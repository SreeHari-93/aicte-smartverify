"""
AICTE Legacy Systems Integrations Package (SIMULATED).
"""

from backend.app.integrations.base import BaseIntegrationAdapter
from backend.app.integrations.application_feed_adapter import ApplicationFeedAdapter
from backend.app.integrations.institute_record_adapter import InstituteRecordAdapter

# Shared adapter instances
app_feed_adapter = ApplicationFeedAdapter()
institute_record_adapter = InstituteRecordAdapter()

__all__ = [
    "BaseIntegrationAdapter",
    "ApplicationFeedAdapter",
    "InstituteRecordAdapter",
    "app_feed_adapter",
    "institute_record_adapter",
]

