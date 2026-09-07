"""
Audit model for inspection records and validations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict

from bot.models.enums import Region, Activity, VesselBand, AuditSubject, ViolationType


@dataclass
class Violation:
    """Single violation record."""

    violation_type: ViolationType
    description: str
    penalty_id: Optional[int] = None
    amount: float = 0.0
    notes: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'type': self.violation_type.value,
            'description': self.description,
            'penalty_id': self.penalty_id,
            'amount': self.amount,
            'notes': self.notes,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class AuditRecord:
    """Complete audit/inspection record."""

    user_id: int
    username: str
    region: Region
    activity: Activity
    audit_date: date
    violations: List[Violation] = field(default_factory=list)

    # Vessel information
    vessel_length: Optional[float] = None
    vessel_band: Optional[VesselBand] = None
    vessel_license: Optional[str] = None
    vessel_name: Optional[str] = None

    # Inspection details
    subject: Optional[AuditSubject] = None
    fishing_gear: Optional[str] = None
    target_species: Optional[str] = None

    # Findings
    notes: Optional[str] = None
    photos: List[str] = field(default_factory=list)

    # Status
    is_completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def validate(self) -> List[str]:
        """Validate audit record."""
        errors = []

        if not self.region:
            errors.append("Region is required")
        if not self.activity:
            errors.append("Activity is required")
        if not self.audit_date:
            errors.append("Audit date is required")

        return errors

    def add_violation(self, violation: Violation) -> None:
        """Add violation to audit."""
        self.violations.append(violation)
        self.updated_at = datetime.now()

    def add_violations(self, violations: List[Violation]) -> None:
        """Add multiple violations."""
        self.violations.extend(violations)
        self.updated_at = datetime.now()

    def clear_violations(self) -> None:
        """Clear all violations."""
        self.violations.clear()
        self.updated_at = datetime.now()

    @property
    def violation_count(self) -> int:
        """Get total violation count."""
        return len(self.violations)

    @property
    def total_penalty(self) -> float:
        """Get total penalty amount."""
        return sum(v.amount for v in self.violations)

    @property
    def has_violations(self) -> bool:
        """Check if audit has any violations."""
        return len(self.violations) > 0

    @property
    def severity(self) -> str:
        """Get overall severity."""
        if not self.violations:
            return "none"

        max_severity = max(v.violation_type for v in self.violations)
        if max_severity == ViolationType.SEVERE:
            return "severe"
        elif max_severity == ViolationType.MODERATE:
            return "moderate"
        elif max_severity == ViolationType.MINOR:
            return "minor"
        return "none"

    def complete(self) -> None:
        """Mark audit as completed."""
        self.is_completed = True
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'region': self.region.value,
            'activity': self.activity.value,
            'audit_date': self.audit_date.isoformat(),
            'vessel_length': self.vessel_length,
            'vessel_band': self.vessel_band.value if self.vessel_band else None,
            'vessel_license': self.vessel_license,
            'vessel_name': self.vessel_name,
            'subject': self.subject.value if self.subject else None,
            'fishing_gear': self.fishing_gear,
            'target_species': self.target_species,
            'violations': [v.to_dict() for v in self.violations],
            'violation_count': self.violation_count,
            'total_penalty': self.total_penalty,
            'severity': self.severity,
            'notes': self.notes,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_summary(self) -> str:
        """Get audit summary as formatted string."""
        lines = [
            f"<b>Denetim Özeti</b>",
            f"Tarih: {self.audit_date.strftime('%d.%m.%Y')}",
            f"Bölge: {self.region.label}",
            f"Aktivite: {self.activity.label}",
        ]

        if self.vessel_length:
            lines.append(f"Gemi Boyu: {self.vessel_length} m")

        if self.fishing_gear:
            lines.append(f"Av Aracı: {self.fishing_gear}")

        if self.target_species:
            lines.append(f"Hedef Tür: {self.target_species}")

        lines.append(f"<b>İhlal Sayısı: {self.violation_count}</b>")
        lines.append(f"<b>Toplam Ceza: {self.total_penalty:,.0f} TL</b>")

        if self.notes:
            lines.append(f"Notlar: {self.notes}")

        return "\n".join(lines)
