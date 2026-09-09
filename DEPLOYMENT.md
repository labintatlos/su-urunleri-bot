# Deployment Rehberi

## 🏠 Home Assistant Eklentisi

### Kurulum Adımları

#### 1. Eklentiyi Ekleme
```yaml
# configuration.yaml veya su_urunleri_bot.yaml
su_urunleri_bot:
  bot_token: !secret telegram_token
  admin_id: "123456789"
  allowed_users: []
  result_limit: 8
  log_level: INFO
  enable_admin_panel: true
  rate_limit_enabled: true
```

#### 2. secrets.yaml
```yaml
# secrets.yaml
telegram_token: "YOUR_BOT_TOKEN_HERE"
```

#### 3. HA Yeniden Başlat
- Settings → Developer Tools → YAML
- Reload veya restart yapın

### Yapılandırma Seçenekleri

| Seçenek | Tür | Varsayılan | Açıklama |
|---------|-----|-----------|----------|
| `bot_token` | string | (gerekli) | Telegram bot tokeni |
| `admin_id` | string | - | Admin Telegram ID |
| `allowed_users` | list | [] | İzin verilen kullanıcılar |
| `result_limit` | int | 8 | Arama sonuçları sayısı |
| `timezone` | string | Europe/Istanbul | Saat dilimi |
| `log_level` | string | INFO | Loglama seviyesi |
| `enable_admin_panel` | bool | true | Admin panelini etkinleştir |
| `rate_limit_enabled` | bool | true | Oran limitlemesi |
| `max_requests_per_minute` | int | 10 | Maksimum istek/dakika |

## 🐳 Docker Kurulumu

### docker-compose.yml
```yaml
version: '3.8'

services:
  su-urunleri-bot:
    image: ghcr.io/username/su_urunleri_bot:latest
    container_name: su_urunleri_bot
    restart: unless-stopped
    environment:
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN}
      ADMIN_IDS: ${ADMIN_IDS}
      LOG_LEVEL: INFO
      TZ: Europe/Istanbul
    volumes:
      - ./data:/share/su_urunleri_bot
      - ./logs:/share/su_urunleri_bot/logs
    ports:
      - "8000:8000"  # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

### Başlatma
```bash
# .env dosyası oluştur
echo "TELEGRAM_TOKEN=your_token_here" > .env
echo "ADMIN_IDS=123456789" >> .env

# Çalıştır
docker-compose up -d

# Logları kontrol et
docker-compose logs -f
```

## 🚀 Bulut Dağıtımı (Heroku, Railway, vb.)

### Environment Değişkenleri
```
TELEGRAM_TOKEN=your_token
ADMIN_IDS=123456789
LOG_LEVEL=INFO
TZ=Europe/Istanbul
```

### Procfile (Heroku)
```
web: python bot.py
```

## 📊 Sağlık Kontrolleri

### Health Endpoint
```bash
curl http://localhost:8000/health

# Yanıt:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "uptime": "1d 2h 30m",
  "telegram": {
    "status": "healthy",
    "message": "Telegram API accessible"
  },
  "database": {
    "status": "healthy",
    "message": "Database accessible"
  }
}
```

## 📈 Monitoring

### Logları İzleme
```bash
# Home Assistant
Settings → System → Logs

# Docker
docker-compose logs -f su-urunleri-bot

# Dosyadan
tail -f /share/su_urunleri_bot/logs/bot.log
tail -f /share/su_urunleri_bot/logs/critical.log
```

### Metrikleri İzleme
- Kullanıcı sayısı
- Sorgu sayısı
- Error oranı
- Response time

## 🔄 Güncellemeler

### Yeni Versiyon Yükleme
```bash
# Docker
docker-compose pull
docker-compose up -d

# Home Assistant
Settings → System → Check for updates

# Manuel
git pull
pip install -r requirements.txt
# Bot'u yeniden başlat
```

## 🔐 Backup & Restore

### Backup
```bash
# Database yedekle
cp /share/su_urunleri_bot/su_urunleri_kolluk.db /backup/su_urunleri_kolluk.db.bak

# Tüm verileri yedekle
tar -czf su_urunleri_bot_backup.tar.gz /share/su_urunleri_bot/
```

### Restore
```bash
# Database'i geri yükle
cp /backup/su_urunleri_kolluk.db.bak /share/su_urunleri_bot/su_urunleri_kolluk.db

# Tümünü geri yükle
tar -xzf su_urunleri_bot_backup.tar.gz -C /
```

## 🆘 Sorun Giderme

### Bot Başlamıyor
```bash
# Logları kontrol et
docker-compose logs su-urunleri-bot

# Yapılandırmayı doğrula
python -m bot.config

# Tokeni kontrol et
echo $TELEGRAM_TOKEN
```

### Veritabanı Hatası
```bash
# Veritabanı dosyasını kontrol et
ls -la /share/su_urunleri_bot/

# İzin problemleri
chmod 755 /share/su_urunleri_bot/

# Veritabanı optimize et
sqlite3 /share/su_urunleri_bot/su_urunleri_kolluk.db "VACUUM;"
```

### Bağlantı Sorunları
```bash
# Telegram API erişimini kontrol et
curl -I https://api.telegram.org

# DNS sorunları
nslookup api.telegram.org
```

## 📋 Deployment Kontrol Listesi

- [ ] Telegram bot tokeni hazır
- [ ] Admin ID'leri yapılandırıldı
- [ ] Veritabanı başlatıldı
- [ ] Log dizini oluşturuldu
- [ ] Environment değişkenleri ayarlandı
- [ ] Health check çalışıyor
- [ ] Bot mesaj gönderiyor
- [ ] Yönetici paneli erişilebilir
- [ ] Backuplar yapılıyor
- [ ] Monitoring aktif

## 🔗 Kaynaklar

- [Home Assistant Add-on Development](https://developers.home-assistant.io/docs/add-ons/)
- [python-telegram-bot Dokümantasyonu](https://python-telegram-bot.readthedocs.io/)
- [Docker Dokümantasyonu](https://docs.docker.com/)

---

**Versiyon:** 5.0.0 | **Sürüm:** 2024
