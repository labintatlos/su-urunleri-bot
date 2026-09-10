#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Su Ürünleri Denetim Asistanı (web sitesi) başlatılıyor..."

export TZ="$(bashio::config 'timezone')"
export RESULT_LIMIT="$(bashio::config 'result_limit')"
if bashio::config.has_value 'gemini_api_key'; then
  export GEMINI_API_KEY="$(bashio::config 'gemini_api_key')"
fi
if bashio::config.has_value 'gemini_model'; then
  export GEMINI_MODEL="$(bashio::config 'gemini_model')"
fi

export WEB_PORT=8101
export INGRESS_PORT=8099

cd /app

exec python3 -u /app/web.py
