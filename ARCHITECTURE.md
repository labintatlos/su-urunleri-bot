# Mimari Tasarım

## 🏗️ Sistem Genel Yapısı

```
User (Telegram)
    ↓
Telegram Bot API
    ↓
Application (python-telegram-bot)
    ↓
┌─────────────────────────────────┐
│ Handler Layer                   │
│ ├─ Command Handlers             │
│ ├─ Callback Query Handlers      │
│ └─ Text Message Handlers        │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│ Middleware Layer                │
│ ├─ Authentication               │
│ └─ Rate Limiting                │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│ Service Layer (Business Logic)  │
│ ├─ Search Service               │
│ ├─ Audit Service                │
│ ├─ Penalty Service              │
│ ├─ Species Service              │
│ └─ Admin Service                │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│ Data Access Layer (Repository)  │
│ ├─ User Repository              │
│ ├─ Article Repository           │
│ ├─ Species Repository           │
│ ├─ Penalty Repository           │
│ └─ Admin Repository             │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│ Database Layer                  │
│ └─ SQLite Database              │
└─────────────────────────────────┘
```

## 🔄 İstek Akışı

### Komut İsteği Örneği (/start)
```
User Input (/start)
    ↓
CommandHandler.handle()
    ↓
start_command()
    ↓
Authentication Check
    ↓
User Repository.touch_user()
    ↓
Send Welcome Message
    ↓
Response to User
```

### Callback Query Örneği (Madde Seç)
```
User Click (Inline Button)
    ↓
CallbackQueryHandler.route()
    ↓
ArticleHandler.handle()
    ↓
Rate Limiting Check
    ↓
SearchService.get_article()
    ↓
ArticleRepository.get_article()
    ↓
Database Query
    ↓
Format Response
    ↓
Send Response
```

### Text Handler Örneği (Ara)
```
User Text Input
    ↓
TextHandler.route()
    ↓
Check Mode
    ↓
Appropriate Handler
    ↓
Service Layer Call
    ↓
Format Results
    ↓
Send Response
```

## 📊 Veritabanı Şeması

### Kullanıcılar
```
users
├── user_id (INTEGER PK)
├── username (TEXT)
├── first_name (TEXT)
└── last_seen (TEXT)

query_log
├── id (INTEGER PK)
├── user_id (INTEGER FK)
├── action (TEXT)
├── query (TEXT)
└── created_at (TEXT)

favorites
├── user_id (INTEGER FK)
├── item_type (TEXT)
├── item_id (TEXT)
├── created_at (TEXT)
└── PRIMARY KEY(user_id, item_type, item_id)
```

### Mevzuat
```
articles
├── id (INTEGER PK)
├── source (TEXT)
├── article (INTEGER)
├── title (TEXT)
├── body (TEXT)
├── page_start (INTEGER)
├── page_end (INTEGER)
├── scope (TEXT)
└── search_text (TEXT)

rules
├── id (TEXT PK)
├── cat (TEXT)
├── title (TEXT)
├── summary (TEXT)
├── refs (JSON)
└── search_text (TEXT)
```

### Türler
```
commercial_species
├── id (INTEGER PK)
├── name (TEXT)
├── min_cm (REAL)
├── min_kg (REAL)
├── time_bans (JSON)
├── article_time (INTEGER)
└── search_text (TEXT)

amateur_species
├── id (INTEGER PK)
├── name (TEXT)
├── min_cm (REAL)
├── min_kg (REAL)
├── limit_text (TEXT)
├── time_bans (JSON)
└── search_text (TEXT)

prohibited_species
├── id (INTEGER PK)
├── name (TEXT)
└── search_text (TEXT)
```

### Cezalar
```
penalty_cards
├── id (INTEGER PK)
├── source_row (INTEGER)
├── violation (TEXT)
├── option_text (TEXT)
├── law (TEXT)
├── base_ipc (REAL)
├── amounts (JSON)
├── product_seizure (TEXT)
├── means_seizure (TEXT)
├── license_action (TEXT)
├── scope (TEXT)
├── layout (TEXT)
└── search_text (TEXT)
```

## 🔐 Güvenlik Mimarisi

### Kimlik Doğrulama
```python
# Auth Middleware
├─ check_user_allowed(user_id)
├─ check_admin(user_id)
├─ require_permission(user_id, permission)
└─ log_access(user_id, action)
```

### Oran Limitlemesi
```python
# Rate Limiter
├─ check_rate_limit(user_id) → bool
├─ record_request(user_id) → None
├─ get_reset_time(user_id) → datetime
└─ get_remaining_time(user_id) → int
```

### Hata İşleme
```python
# Exception Hierarchy
├─ BotException
│  ├─ AuthenticationError
│  ├─ AuthorizationError
│  ├─ ValidationError
│  ├─ DatabaseError
│  ├─ TelegramError
│  └─ RateLimitError
└─ Global Error Handler
```

## 📝 Logging Yapısı

### Seviyeleri
- **DEBUG**: Detaylı geliştirme bilgileri
- **INFO**: Normal işlemler (araştırma, komut)
- **WARNING**: Kurtarılabilir sorunlar (rate limit)
- **ERROR**: İşlem hataları (DB hatası)
- **CRITICAL**: Sistem başarısızlıkları

### Çıktıları
```
Console Handler
├─ SimpleFormatter
└─ STDOUT

File Handler (bot.log)
├─ JSONFormatter
├─ RotatingFile (10MB, 5 backups)
└─ Shared Logs

Critical File (critical.log)
├─ JSONFormatter
├─ RotatingFile (5MB, 3 backups)
└─ Important Errors
```

## 🧩 Modüler Yapı

### Katmanlar

**1. Handler Katmanı**
- Telegram event'lerini işler
- Middleware'i çağırır
- Yanıtları formatlar

**2. Middleware Katmanı**
- Kimlik doğrulama
- Oran limitlemesi
- İstek logging'i

**3. Service Katmanı**
- İş mantığı
- Validasyon
- Veri işleme

**4. Model Katmanı**
- Veri yapıları
- Enum'lar
- Validatorlar

**5. Formatter Katmanı**
- Telegram mesajları
- Klavyeler (inline, reply)
- HTML formatting

**6. Repository Katmanı**
- Database query'leri
- CRUD operasyonları
- Arama/filtreleme

**7. Database Katmanı**
- SQLite bağlantısı
- Connection pooling
- Migration'lar

## 🎯 Design Patterns

### Repository Pattern
```python
# Data Access Layer
user_repo = UserRepository()
users = user_repo.list_users()
user = user_repo.get_user(id)
```

### Service Layer Pattern
```python
# Business Logic
search_service = SearchService()
results = search_service.search_articles(query)
```

### Middleware Pattern
```python
# Cross-cutting Concerns
auth = AuthMiddleware()
auth.require_user_allowed(user_id)
rate_limiter = RateLimiter()
rate_limiter.require_rate_limit(user_id)
```

### Factory Pattern
```python
# Object Creation
router = CallbackRouter()
router.register('menu:', MenuHandler())
router.register('art:', ArticleHandler())
```

## 📈 Ölçeklenebilirlik

### Mevcut Kısıtlamalar
- SQLite: ~1M satıra kadar optimal
- Rate limit: 10 req/min per user
- Message size: 4096 karakter

### Gelecek Iyileştirmeler
- PostgreSQL migration
- Redis caching
- Message sharding
- Async worker queue

## 🧪 Test Mimarisi

```
Tests/
├─ Unit Tests
│  ├─ Model Tests
│  ├─ Service Tests
│  └─ Formatter Tests
├─ Integration Tests
│  ├─ Database Tests
│  └─ Handler Tests
└─ Fixtures
   ├─ Mock Users
   ├─ Mock Updates
   └─ Sample Data
```

---

**Versiyon:** 5.0.0 | **Sürüm:** 2024
