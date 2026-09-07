"""
Command handlers for /start, /menu, /help, and other commands.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.middleware import get_auth, get_rate_limiter
from bot.formatters import MessageFormatter, KeyboardFormatter
from bot.db import get_user_repo, get_query_log_repo
from bot.models import User
from bot.logger import setup_logger

logger = setup_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    chat = update.effective_chat

    # Check rate limit
    try:
        get_rate_limiter().require_rate_limit(user.id)
    except Exception as e:
        logger.warning(f"Rate limit exceeded for user {user.id}")
        await context.bot.send_message(
            chat_id=chat.id,
            text=MessageFormatter.rate_limit_message(60),
            parse_mode='HTML'
        )
        return

    # Check authorization
    auth = get_auth()
    if not auth.check_user_allowed(user.id, user.username):
        msg = MessageFormatter.unauthorized_message(user.id)
        await context.bot.send_message(
            chat_id=chat.id,
            text=msg,
            parse_mode='HTML'
        )
        logger.warning(
            "Unauthorized access attempt",
            extra={'user_id': user.id, 'username': user.username}
        )
        return

    # Record user
    user_repo = get_user_repo()
    user_repo.touch_user(user.id, user.username, user.first_name)

    # Log action
    log_repo = get_query_log_repo()
    log_repo.log_query(user.id, 'start')

    # Send welcome message
    welcome_msg = MessageFormatter.welcome_message(user.first_name or 'Merhaba')

    # Main menu
    menu_buttons = [
        ('📋 Tekne Türü Kılavuzları', 'guide:menu'),
        ('🚨 Denetime Başla', 'audit:start'),
        ('📖 Pratik Ceza Rehberi', 'ceza:menu'),
        ('📖 Pratik Tür Çizelgesi', 'turcizelge:menu'),
        ('🚢 Gemi / Ruhsat / BAGİS', 'vessel:menu'),
        ('🧾 Kolluk İşlem Rehberi', 'field:Kolluk İşlemi'),
        ('🧮 Hesaplayıcılar', 'calc:menu'),
        ('⭐ Favoriler', 'fav:list'),
        ('🕘 Son Sorgular', 'history'),
        ('ℹ️ Sürüm', 'about'),
    ]

    if auth.check_admin(user.id):
        menu_buttons.append(('🔐 Yönetici Paneli', 'admin:panel'))

    keyboard = KeyboardFormatter.menu_keyboard(menu_buttons, columns=2)

    context.user_data.clear()
    await context.bot.send_message(
        chat_id=chat.id,
        text=welcome_msg,
        parse_mode='HTML',
        reply_markup=keyboard
    )

    logger.info(
        "User started bot",
        extra={'user_id': user.id, 'username': user.username}
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    user = update.effective_user
    chat = update.effective_chat

    # Check rate limit
    try:
        get_rate_limiter().require_rate_limit(user.id)
    except Exception:
        return

    # Check authorization
    if not get_auth().check_user_allowed(user.id):
        return

    help_msg = MessageFormatter.help_message()
    await context.bot.send_message(
        chat_id=chat.id,
        text=help_msg,
        parse_mode='HTML'
    )

    logger.info("Help command used", extra={'user_id': user.id})


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /id command - show user's Telegram ID."""
    user = update.effective_user
    chat = update.effective_chat

    msg = f"🆔 <b>Senin Telegram ID:</b> <code>{user.id}</code>"
    await context.bot.send_message(
        chat_id=chat.id,
        text=msg,
        parse_mode='HTML'
    )

    logger.debug("ID command used", extra={'user_id': user.id})


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command - show main menu."""
    user = update.effective_user
    chat = update.effective_chat

    # Check authorization
    if not get_auth().check_user_allowed(user.id):
        return

    # Record user
    user_repo = get_user_repo()
    user_repo.touch_user(user.id, user.username, user.first_name)

    # Main menu
    menu_buttons = [
        ('📋 Tekne Türü Kılavuzları', 'guide:menu'),
        ('🚨 Denetime Başla', 'audit:start'),
        ('📖 Pratik Ceza Rehberi', 'ceza:menu'),
        ('📖 Pratik Tür Çizelgesi', 'turcizelge:menu'),
        ('🚢 Gemi / Ruhsat / BAGİS', 'vessel:menu'),
        ('🧾 Kolluk İşlem Rehberi', 'field:Kolluk İşlemi'),
        ('🧮 Hesaplayıcılar', 'calc:menu'),
        ('⭐ Favoriler', 'fav:list'),
        ('🕘 Son Sorgular', 'history'),
        ('ℹ️ Sürüm', 'about'),
    ]

    if get_auth().check_admin(user.id):
        menu_buttons.append(('🔐 Yönetici Paneli', 'admin:panel'))

    keyboard = KeyboardFormatter.menu_keyboard(menu_buttons, columns=2)

    text = (
        '<b>⚓ SU ÜRÜNLERİ KOLLUK ASİSTANI</b>\n\n'
        '🌊 <b>Deniz görev alanı</b>\n\n'
        'Su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesi, ihlallerin tespiti '
        've uygulanacak işlemlerin belirlenmesine yardımcı olur.'
    )

    context.user_data.clear()
    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

    logger.info("Menu command used", extra={'user_id': user.id})


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(
        f"Error in update {update.update_id}",
        extra={'error': str(context.error)},
    )

    # Notify user if possible
    if update and update.effective_chat:
        try:
            msg = MessageFormatter.error(
                "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin."
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
