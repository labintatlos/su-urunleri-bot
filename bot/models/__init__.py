"""
Data models for user, audit, and guide sessions.
"""

from bot.models.enums import (
    Region,
    Activity,
    VesselBand,
    AuditSubject,
    SpeciesKind,
    GearType,
    AuditStatus,
    ViolationType,
)

from bot.models.user import (
    User,
    UserSession,
)

from bot.models.audit import (
    Violation,
    AuditRecord,
)

from bot.models.guide import (
    GuideQuestion,
    GuideSession,
    GuideTemplate,
)

__all__ = [
    # Enums
    "Region",
    "Activity",
    "VesselBand",
    "AuditSubject",
    "SpeciesKind",
    "GearType",
    "AuditStatus",
    "ViolationType",
    # User models
    "User",
    "UserSession",
    # Audit models
    "Violation",
    "AuditRecord",
    # Guide models
    "GuideQuestion",
    "GuideSession",
    "GuideTemplate",
]
