"""
Audit service for inspection workflow and data management.
"""

from datetime import datetime
from typing import Optional, List

from bot.models import AuditRecord, Violation, ViolationType
from bot.exceptions import ServiceError, AuditError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class AuditService:
    """Service for audit operations."""

    def __init__(self):
        """Initialize audit service."""
        pass

    def create_audit(
        self,
        user_id: int,
        username: str,
        region,
        activity,
        audit_date,
    ) -> AuditRecord:
        """Create new audit record."""
        try:
            audit = AuditRecord(
                user_id=user_id,
                username=username,
                region=region,
                activity=activity,
                audit_date=audit_date,
            )
            logger.info(
                "Audit created",
                extra={
                    'user_id': user_id,
                    'region': region.value,
                    'activity': activity.value,
                }
            )
            return audit
        except Exception as e:
            logger.error(f"Failed to create audit: {e}")
            raise AuditError(f"Failed to create audit: {e}") from e

    def validate_audit(self, audit: AuditRecord) -> List[str]:
        """Validate audit record."""
        errors = audit.validate()
        if errors:
            logger.warning(f"Audit validation failed: {errors}")
        return errors

    def add_violation(
        self,
        audit: AuditRecord,
        description: str,
        violation_type: ViolationType = ViolationType.MINOR,
        penalty_id: Optional[int] = None,
        amount: float = 0.0,
        notes: Optional[str] = None,
    ) -> None:
        """Add violation to audit."""
        try:
            violation = Violation(
                violation_type=violation_type,
                description=description,
                penalty_id=penalty_id,
                amount=amount,
                notes=notes,
            )
            audit.add_violation(violation)
            logger.info(
                "Violation added",
                extra={
                    'user_id': audit.user_id,
                    'type': violation_type.value,
                    'amount': amount,
                }
            )
        except Exception as e:
            logger.error(f"Failed to add violation: {e}")
            raise AuditError(f"Failed to add violation: {e}") from e

    def remove_violation(self, audit: AuditRecord, index: int) -> None:
        """Remove violation from audit."""
        try:
            if 0 <= index < len(audit.violations):
                audit.violations.pop(index)
                logger.info(
                    "Violation removed",
                    extra={'user_id': audit.user_id, 'index': index}
                )
        except Exception as e:
            logger.error(f"Failed to remove violation: {e}")

    def update_vessel_info(
        self,
        audit: AuditRecord,
        length: Optional[float] = None,
        band=None,
        license: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Update vessel information."""
        if length is not None:
            audit.vessel_length = length
        if band is not None:
            audit.vessel_band = band
        if license is not None:
            audit.vessel_license = license
        if name is not None:
            audit.vessel_name = name
        logger.debug(
            "Vessel info updated",
            extra={'user_id': audit.user_id, 'length': length}
        )

    def get_audit_summary(self, audit: AuditRecord) -> str:
        """Get audit summary as formatted string."""
        return audit.to_summary()

    def complete_audit(self, audit: AuditRecord) -> None:
        """Complete audit session."""
        try:
            audit.complete()
            logger.info(
                "Audit completed",
                extra={
                    'user_id': audit.user_id,
                    'violations': audit.violation_count,
                    'total_penalty': audit.total_penalty,
                }
            )
        except Exception as e:
            logger.error(f"Failed to complete audit: {e}")
            raise AuditError(f"Failed to complete audit: {e}") from e

    def export_audit(self, audit: AuditRecord) -> dict:
        """Export audit as dictionary."""
        return audit.to_dict()
