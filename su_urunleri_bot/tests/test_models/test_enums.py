"""
Tests for enum types.
"""

import pytest
from bot.models.enums import (
    Region,
    Activity,
    VesselBand,
    AuditSubject,
    SpeciesKind,
    ViolationType,
)


class TestRegion:
    """Test Region enum."""

    def test_region_values(self):
        """Test region enum values."""
        assert Region.KARADENIZ.value == 'karadeniz'
        assert Region.MARMARA.value == 'marmara'
        assert Region.AKDENIZ.value == 'akdeniz'

    def test_region_labels(self):
        """Test region labels."""
        assert Region.KARADENIZ.label == 'Karadeniz'
        assert Region.MARMARA.label == 'Marmara Denizi'
        assert Region.AKDENIZ.label == 'Akdeniz'

    def test_region_count(self):
        """Test all regions exist."""
        assert len(Region) == 7


class TestActivity:
    """Test Activity enum."""

    def test_activity_values(self):
        """Test activity values."""
        assert Activity.COMMERCIAL.value == 'commercial'
        assert Activity.AMATEUR.value == 'amateur'

    def test_activity_labels(self):
        """Test activity labels."""
        assert Activity.COMMERCIAL.label == 'Ticari Avcılık (6/1)'
        assert Activity.AMATEUR.label == 'Amatör Avcılık (6/2)'


class TestVesselBand:
    """Test VesselBand enum."""

    def test_vessel_band_values(self):
        """Test vessel band values."""
        assert VesselBand.NONE.value == 'none'
        assert VesselBand.LT12.value == 'lt12'

    def test_vessel_band_labels(self):
        """Test vessel band labels."""
        assert VesselBand.NONE.label == 'Gemi/Tekne yok'
        assert VesselBand.LT12.label == '12 metreden küçük'

    def test_vessel_band_rule_length(self):
        """Test vessel band rule lengths."""
        assert VesselBand.NONE.rule_length == 0.0
        assert VesselBand.LT12.rule_length == 11.0
        assert VesselBand.BAND_12_22.rule_length == 17.0
        assert VesselBand.GE22.rule_length == 22.0


class TestAuditSubject:
    """Test AuditSubject enum."""

    def test_audit_subject_values(self):
        """Test audit subject values."""
        assert AuditSubject.FISHING.value == 'fishing'
        assert AuditSubject.VESSEL.value == 'vessel'
        assert AuditSubject.SPECIES.value == 'species'
        assert AuditSubject.TRANSPORT.value == 'transport'

    def test_audit_subject_count(self):
        """Test all subjects exist."""
        assert len(AuditSubject) == 4


class TestSpeciesKind:
    """Test SpeciesKind enum."""

    def test_species_kind_values(self):
        """Test species kind values."""
        assert SpeciesKind.COMMERCIAL.value == 'commercial'
        assert SpeciesKind.AMATEUR.value == 'amateur'
        assert SpeciesKind.PROHIBITED.value == 'prohibited'


class TestViolationType:
    """Test ViolationType enum."""

    def test_violation_type_values(self):
        """Test violation type values."""
        assert ViolationType.NO_VIOLATION.value == 'no_violation'
        assert ViolationType.MINOR.value == 'minor'
        assert ViolationType.SEVERE.value == 'severe'

    def test_violation_type_labels(self):
        """Test violation type labels."""
        assert ViolationType.NO_VIOLATION.label == 'İhlal Yok'
        assert ViolationType.MINOR.label == 'Hafif İhlal'
