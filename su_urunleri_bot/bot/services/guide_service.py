"""
Guide service for inspection guides and vessel checklists.
"""

from typing import Optional, List

from bot.models import GuideSession, GuideTemplate, GuideQuestion
from bot.exceptions import ServiceError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class GuideService:
    """Service for guide operations."""

    def __init__(self):
        """Initialize guide service."""
        self.active_sessions: dict = {}

    def create_session(
        self,
        guide_id: str,
        guide_name: str,
        user_id: int,
    ) -> GuideSession:
        """Create new guide session."""
        try:
            session = GuideSession(
                guide_id=guide_id,
                guide_name=guide_name,
                user_id=user_id,
            )
            self.active_sessions[user_id] = session
            logger.info(
                "Guide session created",
                extra={
                    'user_id': user_id,
                    'guide_id': guide_id,
                }
            )
            return session
        except Exception as e:
            logger.error(f"Failed to create guide session: {e}")
            raise ServiceError(f"Failed to create guide session: {e}") from e

    def get_session(self, user_id: int) -> Optional[GuideSession]:
        """Get user's active guide session."""
        return self.active_sessions.get(user_id)

    def end_session(self, user_id: int) -> None:
        """End guide session."""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session.complete()
            del self.active_sessions[user_id]
            logger.info(
                "Guide session ended",
                extra={
                    'user_id': user_id,
                    'violations': session.violation_count,
                }
            )

    def answer_question(
        self,
        user_id: int,
        question_id: int,
        answer: str,
    ) -> bool:
        """Record answer to guide question."""
        session = self.get_session(user_id)
        if not session:
            raise ServiceError("No active guide session")

        try:
            session.add_answer(question_id, answer)
            logger.debug(
                "Guide question answered",
                extra={'user_id': user_id, 'question': question_id}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record answer: {e}")
            raise ServiceError(f"Failed to record answer: {e}") from e

    def record_violation(
        self,
        user_id: int,
        violation: str,
        penalty: Optional[dict] = None,
    ) -> None:
        """Record violation in guide session."""
        session = self.get_session(user_id)
        if not session:
            raise ServiceError("No active guide session")

        try:
            session.add_violation(violation, penalty)
            logger.info(
                "Violation recorded",
                extra={
                    'user_id': user_id,
                    'violation': violation,
                }
            )
        except Exception as e:
            logger.error(f"Failed to record violation: {e}")
            raise ServiceError(f"Failed to record violation: {e}") from e

    def next_question(self, user_id: int) -> None:
        """Move to next question."""
        session = self.get_session(user_id)
        if session:
            session.next_question()

    def prev_question(self, user_id: int) -> None:
        """Move to previous question."""
        session = self.get_session(user_id)
        if session:
            session.prev_question()

    def get_session_summary(self, user_id: int) -> str:
        """Get guide session summary."""
        session = self.get_session(user_id)
        if not session:
            return "Aktif rehber oturumu yok."

        return session.get_summary()

    def export_session(self, user_id: int) -> dict:
        """Export guide session as dictionary."""
        session = self.get_session(user_id)
        if not session:
            raise ServiceError("No active guide session")

        return session.to_dict()

    def create_template(
        self,
        guide_id: str,
        name: str,
        description: str,
        category: str,
    ) -> GuideTemplate:
        """Create guide template."""
        try:
            template = GuideTemplate(
                id=guide_id,
                name=name,
                description=description,
                category=category,
            )
            logger.info(
                "Guide template created",
                extra={'guide_id': guide_id, 'name': name}
            )
            return template
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise ServiceError(f"Failed to create template: {e}") from e

    def validate_template(self, template: GuideTemplate) -> List[str]:
        """Validate guide template."""
        return template.validate()

    def add_question_to_template(
        self,
        template: GuideTemplate,
        question: GuideQuestion,
    ) -> None:
        """Add question to template."""
        try:
            template.add_question(question)
            logger.debug(
                "Question added to template",
                extra={'guide_id': template.id}
            )
        except Exception as e:
            logger.error(f"Failed to add question: {e}")
            raise ServiceError(f"Failed to add question: {e}") from e
