# Geliştirme Rehberi

Bu belge, Su Ürünleri Denetim Asistanı üzerinde geliştirme yapacak geliştiriciler için rehberdir.

## 🛠️ Geliştirme Ortamı Kurulumu

### 1. Repository Klonlama
```bash
git clone <repository-url>
cd su-urunleri-bot
```

### 2. Virtual Environment Oluşturma
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

### 3. Bağımlılıkları Yükleme
```bash
pip install -r requirements.txt
```

### 4. Ortam Değişkenlerini Ayarlama
```bash
export TELEGRAM_TOKEN="your_test_token"
export ADMIN_IDS="your_user_id"
export LOG_LEVEL="DEBUG"
```

## 📁 Proje Yapısı

```
bot/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── logger.py                # Structured logging
├── exceptions.py            # Custom exceptions
├── main.py                  # Application entry point
├── health.py                # Health checks
├── handlers/                # Command & callback handlers
│   ├── command_handlers.py
│   ├── callback_handlers/   # Callback query handlers
│   └── text_handlers/       # Text message handlers
├── services/                # Business logic
│   ├── search_service.py
│   ├── species_service.py
│   ├── penalty_service.py
│   ├── audit_service.py
│   ├── guide_service.py
│   └── admin_service.py
├── models/                  # Data models
│   ├── enums.py
│   ├── user.py
│   ├── audit.py
│   └── guide.py
├── formatters/              # Message formatting
│   ├── text_formatter.py
│   ├── keyboard_formatter.py
│   └── message_formatter.py
├── middleware/              # Auth & rate limiting
│   ├── auth.py
│   └── rate_limit.py
└── db/                      # Database layer
    ├── connection.py
    ├── repository.py
    └── migrations/

tests/
├── conftest.py              # Pytest fixtures
├── test_models/             # Model tests
├── test_services/           # Service tests
├── test_handlers/           # Handler tests
└── test_db/                 # Database tests
```

## 🔄 Geliştirme Akışı

### 1. Yeni Özellik Eklemek

```bash
# Branch oluştur
git checkout -b feature/yeni-ozellik

# Kod yaz
# Test yaz
# Commit et
git commit -m "Yeni özellik: ..."

# Push et
git push origin feature/yeni-ozellik
```

### 2. Kodu Test Etmek
```bash
# Tüm testler
pytest

# Belirli test dosyası
pytest tests/test_models/test_user.py

# Coverage ile
pytest --cov=bot

# Spesifik marker
pytest -m unit
```

### 3. Code Quality
```bash
# Format kontrol
black bot/ tests/

# Import sıralaması
isort bot/ tests/

# Linting
flake8 bot/ tests/

# Type checking
mypy bot/
```

### 4. Botu Çalıştırmak
```bash
# Normal çalıştırma
python run.py

# Debug mode ile
export LOG_LEVEL=DEBUG
python run.py

# Health check
python run.py --check
```

## 📝 Kod Standartları

### Dosya Yapısı
- Her modülün başında docstring olmalı
- Import'lar alfabetik sırada
- Maksimum 100 karakter genişlik (doc: 80)

### Fonksiyon/Metod
```python
async def handle_user_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle incoming user input.
    
    Args:
        update: Telegram update
        context: Handler context
    """
    pass
```

### Sınıf
```python
class MyService:
    """Service for handling X operations."""

    def __init__(self):
        """Initialize service."""
        self.repo = get_repository()

    def do_something(self, param: str) -> str:
        """Do something with param."""
        return result
```

### Logging
```python
from bot.logger import setup_logger

logger = setup_logger(__name__)

logger.info("User searched", extra={'user_id': uid, 'query': query})
logger.error("Error occurred", exc_info=True)
```

## 🧪 Test Yazma

### Unit Test Örneği
```python
import pytest
from bot.models import User

class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test user can be created."""
        user = User(user_id=1, first_name="Test")
        assert user.user_id == 1
        assert user.first_name == "Test"

    def test_full_name(self):
        """Test full name property."""
        user = User(user_id=1, first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"
```

### Async Test Örneği
```python
@pytest.mark.asyncio
async def test_handler(mock_update, mock_context):
    """Test async handler."""
    await some_handler(mock_update, mock_context)
    mock_update.callback_query.answer.assert_called()
```

## 🐛 Hata Ayıklama

### Logger Kullanarak
```python
logger.debug("Value is:", extra={'value': my_value})
```

### Breakpoint Koymak
```python
import pdb; pdb.set_trace()
```

### Test Tek Bir Test
```bash
pytest tests/test_models/test_user.py::TestUser::test_user_creation -v
```

## 📦 Commit Mesajı Formatı

```
[Type] Kısa açıklama

Detaylı açıklama (opsiyonel)

Closes #123
```

Türler:
- `[feat]` - Yeni özellik
- `[fix]` - Hata düzeltme
- `[refactor]` - Kod yeniden yapılandırması
- `[test]` - Test ekleme
- `[docs]` - Belge güncelleme
- `[chore]` - Bakım işi

## 🔍 Code Review Kontrol Listesi

- [ ] Kodu okudum ve anladım
- [ ] Testler eklenmiş
- [ ] Testler geçiyor
- [ ] Docstring var
- [ ] Hata işleme uygun
- [ ] Logging yeterli
- [ ] Commit mesajı açık

## 📚 Kaynaklar

- [Architecture](ARCHITECTURE.md)
- [API Reference](API.md)
- [python-telegram-bot docs](https://python-telegram-bot.readthedocs.io/)

## ❓ Sık Sorulan Sorular

**S: Yeni bir handler nasıl eklerim?**
A: `bot/handlers/callback_handlers/` altında yeni dosya oluştur, `CallbackHandler` inherit et, `handle_callback` ve `can_handle` metotlarını implement et.

**S: Veritabanı şemasını nasıl değiştiririm?**
A: `bot/db/migrations/` altında yeni migration dosyası oluştur ve migration runner'a ekle.

**S: Yeni bir service nasıl eklerim?**
A: `bot/services/` altında yeni dosya oluştur, repository'leri inject et, business logic yaz.

---

**Son Güncelleme:** 2024 | **Sürüm:** 5.0.0
