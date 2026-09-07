# Su Ürünleri Denetim Asistanı

**Telegram Bot** | **Home Assistant Eklentisi** | **v5.0.0**

Deniz görev alanında su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesi, ihlallerin tespiti ve uygulanacak işlemlerin belirlenmesinde yardımcı olan akıllı Telegram botu.

## 🌊 Özellikler

### 📋 Tekne Türü Kılavuzları
- Çıkacağınız tekneye özel kontrol föyleri
- Dinamik uygunluk/uygunsuzluk işaretleme
- Otomatik rapor oluşturma

### 🚨 Denetime Başla
- Adım adım denetim rehberi
- Bölge, faaliyet, gemi boyu seçimi
- Otomatik ihlal tespiti ve ceza hesaplaması

### 📖 Ceza Rehberi
- 1380 Sayılı Kanun maddeleri
- İdari cezalar ve yaptırımlar
- Tekrar ihlal çarpanları

### 🐟 Tür Çizelgesi
- Ticari (6/1) ve Amatör (6/2) türleri
- Asgari boy/ağırlık bilgileri
- Mevsimsel avlanma yasağı

### 🖼️ Görsel Rehberler
- Balık türleri teşhis kartları
- Yasak av araçları görsel tespiti
- İşlemli fotoğraf rehberleri

### 🧮 Hesaplayıcılar
- Mavi yüzgeçli orkinos %5 adet toleransı
- Ticari küçük boy toleransı (%5-15)
- Otomatik ceza hesaplama

### 👤 Yönetici Paneli
- Kullanıcı istatistikleri
- Sorgu geçmişi analizi
- Sistem durumu izleme

## 🚀 Başlangıç

### Gereksinimler
- Python 3.9+
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Home Assistant (optional)

### Kurulum

#### Yerel Kurulum
```bash
# Depo klonlama
git clone <repo-url>
cd su-urunleri-bot

# Bağımlılıkları yükleme
pip install -r requirements.txt

# Ortam değişkenleri
export TELEGRAM_TOKEN="your_token_here"
export ADMIN_IDS="123456789"

# Çalıştırma
python run.py
```

#### Home Assistant Eklentisi
```yaml
# configuration.yaml
su_urunleri_bot:
  bot_token: !secret telegram_token
  admin_id: "123456789"
  allowed_users: []
  result_limit: 8
  log_level: INFO
```

### Sağlık Kontrolü
```bash
python run.py --check
```

## 📖 Komutlar

| Komut | Açıklama |
|-------|----------|
| `/start` | Botu başlat ve menüyü göster |
| `/menu` | Ana menüyü göster |
| `/help` | Yardım mesajını göster |
| `/id` | Telegram ID'nizi öğrenin (Admin) |

## 🎯 Ana Menü

- **📋 Tekne Türü Kılavuzları** - Kontrol föyü seç
- **🚨 Denetime Başla** - Denetim başlat
- **📖 Pratik Ceza Rehberi** - Cezaları ara
- **📖 Pratik Tür Çizelgesi** - Türleri ara
- **🚢 Gemi/Ruhsat/BAGİS** - Gemi kontrol kartları
- **🧾 Kolluk İşlem Rehberi** - İşlem prosedürleri
- **🧮 Hesaplayıcılar** - Otomatik hesaplama
- **⭐ Favoriler** - Kayıtlı araştırmalar
- **🕘 Son Sorgular** - Geçmiş araştırmalar
- **ℹ️ Sürüm** - Versiyon bilgisi

## 🏗️ Mimarisi

```
bot/
├── config.py           # Konfigürasyon yönetimi
├── logger.py           # Yapılandırılmış logging
├── exceptions.py       # Özel istisnalar
├── main.py            # Uygulama entry point
├── health.py          # Sağlık kontrolleri
├── handlers/          # Command & callback handlers
├── services/          # İş mantığı servisleri
├── models/            # Veri modelleri
├── formatters/        # Mesaj formatlamayı
├── middleware/        # Auth & rate limiting
└── db/               # Veritabanı & repositories
```

## 🧪 Testler

```bash
# Tüm testleri çalıştır
pytest

# Belirli test türü
pytest -m unit
pytest -m integration

# Coverage raporu ile
pytest --cov=bot --cov-report=html

# Belirli dosya
pytest tests/test_models/test_user.py
```

## 📊 Veritabanı

SQLite veritabanı yapısı:
- **users** - Kullanıcı bilgileri
- **query_log** - Sorgu geçmişi
- **articles** - Mevzuat maddeleri
- **commercial_species** - Ticari türler
- **amateur_species** - Amatör türler
- **prohibited_species** - Yasaklı türler
- **penalty_cards** - Ceza kartları
- **favorites** - Kullanıcı favorileri
- **audit_records** - Denetim kayıtları

## 🔐 Güvenlik

- ✅ Kullanıcı kimlik doğrulaması
- ✅ Admin rol kontrolleri
- ✅ Oran limitlemesi (10 req/min)
- ✅ Giriş kayıtlama
- ✅ Yapılandırılmış hata işleme

## 📝 Yapılandırma

### Ortam Değişkenleri
```bash
TELEGRAM_TOKEN          # Bot tokeni (gerekli)
ADMIN_IDS              # Admin ID'leri (opsiyonel)
ALLOWED_USER_IDS       # İzin verilen kullanıcılar
RESULT_LIMIT           # Arama sonucu limiti (default: 8)
TZ                     # Saat dilimi (default: Europe/Istanbul)
LOG_LEVEL              # Loglama seviyesi (default: INFO)
```

### Home Assistant Options
```yaml
bot_token: "TOKEN"
admin_id: "ID"
allowed_users: []
result_limit: 8
log_level: "INFO"
enable_admin_panel: true
rate_limit_enabled: true
```

## 🤝 Katkı Yapma

1. Branch oluştur: `git checkout -b feature/yeni-ozellik`
2. Değişiklikleri commit et: `git commit -m "Açıkla"`
3. Push et: `git push origin feature/yeni-ozellik`
4. Pull Request oluştur

## 📚 Belgelendirme

- [DEVELOPMENT.md](DEVELOPMENT.md) - Geliştirme rehberi
- [ARCHITECTURE.md](ARCHITECTURE.md) - Mimari tasarım
- [API.md](API.md) - API referansı

## 📄 Lisans

MIT License - Detaylar için LICENSE dosyasına bakın.

## 📞 Destek

Sorularınız için [GitHub Issues](https://github.com/repo/issues) sayfasını kullanın.

---

**Versiyon:** 5.0.0 | **Güncelleme:** 2024 | **Python:** 3.9+
