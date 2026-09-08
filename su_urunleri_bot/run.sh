#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Su Ürünleri Denetim Asistanı başlatılıyor..."

if ! bashio::config.has_value 'bot_token'; then
  bashio::log.error "Telegram Bot Token boş bırakılamaz!"
  exit 1
fi

export TELEGRAM_TOKEN="$(bashio::config 'bot_token')"
export ADMIN_IDS="$(bashio::config 'admin_id')"
export ALLOWED_USER_IDS="$(bashio::config 'allowed_users')"
export TZ="$(bashio::config 'timezone')"
export RESULT_LIMIT="$(bashio::config 'result_limit')"
if bashio::config.has_value 'gemini_api_key'; then
  export GEMINI_API_KEY="$(bashio::config 'gemini_api_key')"
fi

cd /app

# Runs the complete, feature-carrying bot. The bot/ package is an in-progress
# modular rewrite whose guide and species screens are still placeholders, so it
# is deliberately not the entrypoint yet.
exec python3 -u /app/bot.py
