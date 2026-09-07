"""
Guide model for inspection guides and checklists.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class GuideQuestion:
    """Single guide question."""

    id: int
    question: str
    category: str
    answers: List[str] = field(default_factory=list)
    correct_answer: Optional[str] = None
    description: Optional[str] = None
    references: List[Dict[str, str]] = field(default_factory=list)

    def validate_answer(self, answer: str) -> bool:
        """Check if answer is valid."""
        return answer in self.answers

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'question': self.question,
            'category': self.category,
            'answers': self.answers,
            'description': self.description,
            'references': self.references,
        }


@dataclass
class GuideSession:
    """Active guide session."""

    guide_id: str
    guide_name: str
    user_id: int
    current_question_idx: int = 0
    answers: Dict[int, str] = field(default_factory=dict)
    violations_found: List[str] = field(default_factory=list)
    penalties: List[Dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    is_completed: bool = False

    def add_answer(self, question_id: int, answer: str) -> None:
        """Record answer to question."""
        self.answers[question_id] = answer

    def add_violation(self, violation: str, penalty: Optional[Dict] = None) -> None:
        """Record violation found."""
        self.violations_found.append(violation)
        if penalty:
            self.penalties.append(penalty)

    def get_current_question_id(self) -> Optional[int]:
        """Get current question ID."""
        if self.current_question_idx >= 0:
            return self.current_question_idx
        return None

    def next_question(self) -> None:
        """Move to next question."""
        self.current_question_idx += 1

    def prev_question(self) -> None:
        """Move to previous question."""
        if self.current_question_idx > 0:
            self.current_question_idx -= 1

    def complete(self) -> None:
        """Mark guide as completed."""
        self.is_completed = True
        self.completed_at = datetime.now()

    @property
    def progress(self) -> float:
        """Get completion progress (0-100)."""
        if not self.answers:
            return 0.0
        # This would typically be calculated based on total questions
        return min(100.0, (len(self.answers) / max(1, len(self.answers))) * 100)

    @property
    def violation_count(self) -> int:
        """Get violation count."""
        return len(self.violations_found)

    @property
    def total_penalty(self) -> float:
        """Calculate total penalty amount."""
        return sum(p.get('amount', 0) for p in self.penalties)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'guide_id': self.guide_id,
            'guide_name': self.guide_name,
            'user_id': self.user_id,
            'current_question': self.current_question_idx,
            'answers_count': len(self.answers),
            'violations_found': self.violations_found,
            'violation_count': self.violation_count,
            'total_penalty': self.total_penalty,
            'progress': self.progress,
            'is_completed': self.is_completed,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_summary(self) -> str:
        """Get session summary as formatted string."""
        lines = [
            f"<b>{self.guide_name} - Sonuçlar</b>",
            f"Tarih: {self.started_at.strftime('%d.%m.%Y %H:%M')}",
            "",
        ]

        if self.violations_found:
            lines.append("<b>Bulunan İhlaller:</b>")
            for i, violation in enumerate(self.violations_found, 1):
                lines.append(f"{i}. {violation}")
            lines.append("")
            lines.append(f"<b>Toplam İhlal: {self.violation_count}</b>")
            lines.append(f"<b>Toplam Ceza: {self.total_penalty:,.0f} TL</b>")
        else:
            lines.append("✅ <b>İhlal Bulunamadı</b>")

        lines.append(f"Tamamlanma Tarihi: {self.completed_at.strftime('%d.%m.%Y %H:%M') if self.completed_at else 'N/A'}")

        return "\n".join(lines)


@dataclass
class GuideTemplate:
    """Guide template definition."""

    id: str
    name: str
    description: str
    category: str
    questions: List[GuideQuestion] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def add_question(self, question: GuideQuestion) -> None:
        """Add question to guide."""
        self.questions.append(question)

    def get_question(self, question_id: int) -> Optional[GuideQuestion]:
        """Get question by ID."""
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

    @property
    def question_count(self) -> int:
        """Get total question count."""
        return len(self.questions)

    def validate(self) -> List[str]:
        """Validate guide template."""
        errors = []

        if not self.id:
            errors.append("Guide ID is required")
        if not self.name:
            errors.append("Guide name is required")
        if not self.questions:
            errors.append("Guide must have at least one question")

        return errors

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'question_count': self.question_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
