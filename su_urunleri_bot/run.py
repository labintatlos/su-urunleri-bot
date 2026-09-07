#!/usr/bin/env python3
"""
Bot entry point script.
Run this to start the bot.

Usage:
    python run.py              # Start bot
    python run.py --check      # Health check
"""

import sys
import argparse

from bot import __version__
from bot.main import main
from bot.health import get_health
from bot.logger import setup_logger

logger = setup_logger(__name__)


def check_health():
    """Run health check."""
    health = get_health()
    status = health.get_full_status()

    print(health.get_summary())
    print()

    # Exit with appropriate code
    if status['telegram']['status'] == 'healthy' and status['database']['status'] == 'healthy':
        print("✅ Bot is healthy")
        sys.exit(0)
    else:
        print("❌ Bot has issues")
        sys.exit(1)


def main_entry():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Su Ürünleri Denetim Asistanı - Telegram Bot'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run health check and exit'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    args = parser.parse_args()

    if args.check:
        check_health()
        return

    # Run bot
    try:
        logger.info("=" * 60)
        logger.info("SU ÜRÜNLERİ DENETIM ASİSTANI - TELEGRAM BOT")
        logger.info(f"Versiyon: {__version__}")
        logger.info("=" * 60)
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main_entry()
