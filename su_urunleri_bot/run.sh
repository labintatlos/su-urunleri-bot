#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Su Ürünleri Denetim Asistanı başlatılıyor (v5.0.0)..."

if ! bashio::config.has_value 'bot_token'; then
  bashio::log.error "Telegram Bot Token boş bırakılamaz!"
  exit 1
fi

export TZ="$(bashio::config 'timezone')"
export LOG_LEVEL="$(bashio::config 'log_level')"

cd /app
exec python3 -u /app/run.py
