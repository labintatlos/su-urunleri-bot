"""
Enumeration types for audit, species, and activity classifications.
"""

from enum import Enum


class Region(str, Enum):
    """Fishing regions."""
    KARADENIZ = 'karadeniz'
    MARMARA = 'marmara'
    ISTANBUL = 'istanbul'
    CANAKKALE = 'canakkale'
    EGE = 'ege'
    AKDENIZ = 'akdeniz'
    INTERNATIONAL = 'international'

    @property
    def label(self) -> str:
        """Get region label."""
        labels = {
            'karadeniz': 'Karadeniz',
            'marmara': 'Marmara Denizi',
            'istanbul': 'İstanbul Boğazı',
            'canakkale': 'Çanakkale Boğazı',
            'ege': 'Ege Denizi',
            'akdeniz': 'Akdeniz',
            'international': 'Uluslararası / MEB',
        }
        return labels.get(self.value, self.value)


class Activity(str, Enum):
    """Fishing activity type."""
    COMMERCIAL = 'commercial'
    AMATEUR = 'amateur'

    @property
    def label(self) -> str:
        """Get activity label."""
        labels = {
            'commercial': 'Ticari Avcılık (6/1)',
            'amateur': 'Amatör Avcılık (6/2)',
        }
        return labels.get(self.value, self.value)


class VesselBand(str, Enum):
    """Vessel size classification."""
    NONE = 'none'
    LT12 = 'lt12'
    BAND_12_22 = '12to22'
    GE22 = 'ge22'

    @property
    def label(self) -> str:
        """Get vessel band label."""
        labels = {
            'none': 'Gemi/Tekne yok',
            'lt12': '12 metreden küçük',
            '12to22': '12 m – 22 m altı',
            'ge22': '22 m ve üzeri',
        }
        return labels.get(self.value, self.value)

    @property
    def rule_length(self) -> float:
        """Get rule-based length for this band."""
        lengths = {
            'none': 0.0,
            'lt12': 11.0,
            '12to22': 17.0,
            'ge22': 22.0,
        }
        return lengths.get(self.value, 0.0)


class AuditSubject(str, Enum):
    """Audit subject category."""
    FISHING = 'fishing'
    VESSEL = 'vessel'
    SPECIES = 'species'
    TRANSPORT = 'transport'

    @property
    def label(self) -> str:
        """Get subject label."""
        labels = {
            'fishing': 'Avcılık faaliyeti',
            'vessel': 'Gemi / ruhsat / donanım',
            'species': 'Ürün / tür kontrolü',
            'transport': 'Nakil / satış kontrolü',
        }
        return labels.get(self.value, self.value)


class SpeciesKind(str, Enum):
    """Type of species."""
    COMMERCIAL = 'commercial'
    AMATEUR = 'amateur'
    PROHIBITED = 'prohibited'

    @property
    def label(self) -> str:
        """Get species kind label."""
        labels = {
            'commercial': 'Ticari (6/1)',
            'amateur': 'Amatör (6/2)',
            'prohibited': 'Tamamen Yasak',
        }
        return labels.get(self.value, self.value)


class GearType(str, Enum):
    """Fishing gear/equipment type."""
    GIRGIR = 'gırgır'
    DIP_TROL = 'dip trolü'
    ORTASU_TROL = 'ortasu trolü'
    UZATMA_AGI = 'uzatma ağı'
    PARAKETE = 'parakete'
    ALGARNA = 'algarna'
    MANYAT = 'manyat'
    DEMINZ = 'deniz'
    ISIK = 'ışık'
    DALMA = 'dalma'
    MONOFILAMENT = 'monofilament'
    TURIZM = 'turizm'

    @property
    def label(self) -> str:
        """Get gear type label."""
        return self.value


class AuditStatus(str, Enum):
    """Audit session status."""
    STARTED = 'started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    SUSPENDED = 'suspended'

    @property
    def label(self) -> str:
        """Get status label."""
        labels = {
            'started': 'Başladı',
            'in_progress': 'Devam Ediyor',
            'completed': 'Tamamlandı',
            'suspended': 'Askıya Alındı',
        }
        return labels.get(self.value, self.value)


class ViolationType(str, Enum):
    """Type of violation found."""
    NO_VIOLATION = 'no_violation'
    MINOR = 'minor'
    MODERATE = 'moderate'
    SEVERE = 'severe'

    @property
    def label(self) -> str:
        """Get violation type label."""
        labels = {
            'no_violation': 'İhlal Yok',
            'minor': 'Hafif İhlal',
            'moderate': 'Orta Düzey İhlal',
            'severe': 'Ağır İhlal',
        }
        return labels.get(self.value, self.value)
