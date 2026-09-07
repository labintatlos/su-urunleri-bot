"""
Main application entry point.
Initializes and runs the Telegram bot.
"""

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import get_config
from bot.logger import setup_logger
from bot.db import get_migration_runner
from bot.handlers import (
    start_command,
    help_command,
    id_command,
    menu_command,
    error_handler,
)
from bot.handlers.callback_handlers import (
    MenuHandler,
    ArticleHandler,
    SpeciesHandler,
    PenaltyHandler,
    GuideHandler,
    AuditHandler,
    AdminHandler,
    CallbackRouter,
)

logger = setup_logger(__name__)


def initialize_app() -> Application:
    """Initialize the Telegram bot application."""
    config = get_config()

    logger.info("Initializing bot application")

    # Initialize database
    try:
        migration_runner = get_migration_runner()
        migration_runner.init_db(config.data_path)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Create application
    app = Application.builder().token(config.bot_token).build()

    # Register command handlers
    logger.debug("Registering command handlers")
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))

    # Register callback handlers
    logger.debug("Registering callback handlers")
    callback_router = CallbackRouter()

    # Register individual handlers
    menu_handler = MenuHandler()
    article_handler = ArticleHandler()
    species_handler = SpeciesHandler()
    penalty_handler = PenaltyHandler()
    guide_handler = GuideHandler()
    audit_handler = AuditHandler()
    admin_handler = AdminHandler()

    # Route callbacks
    app.add_handler(CallbackQueryHandler(
        lambda update, context: callback_handler_dispatcher(
            update, context,
            menu_handler, article_handler, species_handler,
            penalty_handler, guide_handler, audit_handler, admin_handler
        )
    ))

    # Register text message handler
    logger.debug("Registering text message handlers")
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))

    # Register error handler
    app.add_error_handler(error_handler)

    logger.info("Bot application initialized successfully")
    return app


async def callback_handler_dispatcher(
    update,
    context,
    menu_handler,
    article_handler,
    species_handler,
    penalty_handler,
    guide_handler,
    audit_handler,
    admin_handler,
):
    """Dispatch callback to appropriate handler."""
    callback_data = update.callback_query.data

    handlers = [
        menu_handler,
        article_handler,
        species_handler,
        penalty_handler,
        guide_handler,
        audit_handler,
        admin_handler,
    ]

    for handler in handlers:
        if handler.can_handle(callback_data):
            await handler.handle(update, context)
            return

    # No handler found
    logger.warning(f"No handler for callback: {callback_data}")
    await update.callback_query.answer("İşlem bulunamadı!", show_alert=True)


async def handle_text_message(update, context):
    """Handle text messages."""
    user = update.effective_user
    message_text = update.message.text

    logger.debug(
        "Text message received",
        extra={'user_id': user.id, 'text_length': len(message_text)}
    )

    # Check if in a search or input mode
    mode = context.user_data.get('mode')

    if mode:
        logger.debug(f"Handling mode: {mode}", extra={'user_id': user.id})
        # Mode handlers would be implemented here
    else:
        # Default: show help
        await update.message.reply_text(
            "Lütfen menüdeki seçeneklerden birini seçin veya /help yazın."
        )


def main():
    """Main entry point.

    Note: this is deliberately synchronous. Application.run_polling() is a
    blocking call that creates and owns its own event loop, so it must not be
    awaited or run inside asyncio.run().
    """
    try:
        logger.info("Starting bot application")

        # Initialize app
        app = initialize_app()

        # Get config
        config = get_config()

        # Log config
        logger.info(
            "Bot configuration loaded",
            extra={
                'admin_ids': len(config.admin_ids),
                'allowed_users': len(config.allowed_user_ids),
                'log_level': config.log_level,
            }
        )

        # Run bot
        logger.info("Starting polling")
        app.run_polling(
            allowed_updates=["message", "callback_query", "my_chat_member"],
            drop_pending_updates=True,
        )

    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
