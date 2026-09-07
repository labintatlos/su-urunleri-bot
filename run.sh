#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Su Ürünleri Denetim Asistanı başlatılıyor (v2.3.0 Engine)..."

export TELEGRAM_TOKEN="$(bashio::config 'bot_token')"
export ADMIN_IDS="$(bashio::config 'admin_id')"
export ALLOWED_USER_IDS="$(bashio::config 'allowed_users')"
export TZ="Europe/Istanbul"
export RESULT_LIMIT="8"

if [ -z "${TELEGRAM_TOKEN}" ]; then
  bashio::log.error "Telegram Bot Token boş bırakılamaz!"
  exit 1
fi

exec python3 -u /app/bot.py
