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
if bashio::config.has_value 'gemini_model'; then
  export GEMINI_MODEL="$(bashio::config 'gemini_model')"
fi

cd /app

exec python3 -u /app/bot.py
