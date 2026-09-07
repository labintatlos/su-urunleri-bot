# API Referansı

## 🎮 Komutlar

### /start
Botu başlatır ve hoş geldiniz mesajı ile ana menüyü gösterir.

```
/start
```

**Yanıt:**
- Hoş geldiniz mesajı
- Ana menü (inline buttons)

**Gerekli:** Yetki

---

### /menu
Ana menüyü gösterir.

```
/menu
```

**Yanıt:**
- Ana menü (inline buttons)

**Gerekli:** Yetki

---

### /help
Yardım mesajını gösterir.

```
/help
```

**Yanıt:**
- Komut listesi
- Özellikler
- Kullanım ipuçları

---

### /id
Kullanıcının Telegram ID'sini gösterir.

```
/id
```

**Yanıt:**
- `🆔 Senin Telegram ID: 123456789`

---

## 🎯 Callback Data Formatı

### Menu Navigasyonu
```
menu                    # Ana menüyü göster
field:Gemi/Ruhsat      # Belirli kategori
vessel:menu            # Gemi menüsü
```

### Makale/Madde
```
art:61:18              # 6/1 Tebliğ Madde 18
srclist:61:0           # Kaynağın madde listesi, sayfa 0
artp:61:18:1           # Madde 18, metin bölümü 1
```

### Türler
```
sp:commercial:1        # Ticari tür ID 1
species:menu           # Tür menüsü
species:kind:commercial # Ticari türleri ara
```

### Cezalar
```
pen:123                # Ceza kartı ID 123
ceza:menu              # Ceza menüsü
ceza:view:cat_id       # Kategori
```

### Denetim
```
audit:start            # Denetime başla
audit:region:karadeniz # Bölge seçimi
audit:activity:commercial # Faaliyet seçimi
audit:subject:fishing  # Konu seçimi
audit:date:today       # Bugün tarihini seç
audit:date:other       # Başka tarih gir
```

### Yönetici
```
admin:panel            # Admin paneli
admin:stats:main       # Ana istatistikler
admin:stats:users      # Kullanıcı istatistikleri
admin:stats:logs       # Son sorgular
```

### Diğer
```
fav:add:article:61-18  # Favoriye ekle
fav:list               # Favori listesi
history                # Son sorgular
about                  # Sürüm bilgisi
```

---

## 📝 Metin Handler Modları

### Arama Modları

#### Penalty Mode (`mode:penalty`)
Ceza kartlarını ara.
```
Kullanıcı: BAGİS arızası
Çıkış: İlgili ceza kartlarının listesi
```

#### Species Mode (`mode:species_search`)
Balık türlerini ara.
```
Kullanıcı: kalkan
Çıkış: Kalkan türünün detayları
```

#### Article Mode (`mode:source_search`)
Mevzuat makalelerini ara.
```
Kullanıcı: ruhsat
Çıkış: İlgili ruhsat makalelerinin listesi
```

#### Gear Mode (`mode:gear`)
Av araçlarını ara.
```
Kullanıcı: gırgır
Çıkış: Gırgır detayları
```

### Denetim Modları

#### Audit Length (`mode:audit_length_exact`)
Gemi boyunu gir (metre).
```
Kullanıcı: 17.4
Çıkış: Tarih seçim ekranı
```

#### Audit Date (`mode:audit_date`)
Denetim tarihini gir (GG.AA.YYYY).
```
Kullanıcı: 20.05.2024
Çıkış: Kontrol konusu seçimi
```

#### Audit Species (`mode:audit_species_search`)
Kontrol edilen türü ara.
```
Kullanıcı: hamsi
Çıkış: Hamsi detayları + devam butonu
```

---

## 🎨 Mesaj Formatları

### Makale Mesajı
```
📚 Madde 18
Başlık Metni
Sayfa 10-10

Madde içeriği...
```

### Tür Mesajı
```
🐟 Hamsi
📏 Asgari boy: 9 cm
⚖️ Asgari ağırlık: -
📅 Zaman Yasağı: 01-01 – 06-30
```

### Ceza Mesajı
```
⚖️ Ruhsatsız Avcılık
Seçenek: Ruhsatsız gemi
💰 Taban Ceza: 5,000 TL
✓ Ürün El Konuşu: Evet
✓ Av Aracı El Konuşu: Evet
```

### Hata Mesajı
```
❌ Hata: Tanımlama yapılamadı
[Detaylı hata metni]
```

### Başarı Mesajı
```
✅ İşlem başarıyla tamamlandı
[Detaylar]
```

---

## 🗂️ Veri Modelleri

### User
```python
{
  "user_id": 123456789,
  "username": "testuser",
  "first_name": "Test",
  "full_name": "Test User",
  "is_admin": False,
  "is_allowed": True,
  "permissions": ["read", "search"]
}
```

### Article
```python
{
  "id": 1,
  "source": "61",
  "article": 18,
  "title": "Madde 18",
  "body": "Madde içeriği...",
  "page_start": 10,
  "page_end": 10,
  "scope": "sea_or_general"
}
```

### Species
```python
{
  "id": 1,
  "name": "Hamsi",
  "min_cm": 9.0,
  "min_kg": None,
  "time_bans": ["01-01/06-30"],
  "limit_text": "50 kg"
}
```

### Penalty
```python
{
  "id": 1,
  "violation": "Ruhsatsız Avcılık",
  "option_text": "Ruhsatsız gemi",
  "law": "1380 Kanun Md. 36",
  "base_ipc": 5000.0,
  "amounts": {"first": 5000, "repeat": 10000},
  "product_seizure": "Evet",
  "means_seizure": "Evet"
}
```

### Audit Record
```python
{
  "user_id": 123,
  "username": "testuser",
  "region": "karadeniz",
  "activity": "commercial",
  "audit_date": "2024-05-20",
  "vessel_length": 17.4,
  "violations": [
    {
      "type": "minor",
      "description": "Ruhsat hatası",
      "amount": 1000
    }
  ],
  "total_penalty": 1000,
  "severity": "minor"
}
```

---

## 🔧 Configuration Enums

### Region
```python
karadeniz    → Karadeniz
marmara      → Marmara Denizi
istanbul     → İstanbul Boğazı
canakkale    → Çanakkale Boğazı
ege          → Ege Denizi
akdeniz      → Akdeniz
international → Uluslararası / MEB
```

### Activity
```python
commercial   → Ticari Avcılık (6/1)
amateur      → Amatör Avcılık (6/2)
```

### VesselBand
```python
none         → Gemi/Tekne yok (0.0m)
lt12         → 12 metreden küçük (11.0m)
12to22       → 12-22m altı (17.0m)
ge22         → 22m ve üzeri (22.0m)
```

### ViolationType
```python
no_violation → İhlal Yok
minor        → Hafif İhlal
moderate     → Orta Düzey İhlal
severe       → Ağır İhlal
```

---

## 📊 Service API'si

### SearchService
```python
search_service = SearchService()

# Makale arama
results = search_service.search_articles(query, source, limit)
article = search_service.get_article(source, article_number)

# Tür arama
species = search_service.search_species(query, kind, limit)
sp_detail = search_service.get_species(kind, species_id)

# Ceza arama
penalties = search_service.search_penalties(query, limit)
penalty = search_service.get_penalty(penalty_id)
```

### AuditService
```python
audit_service = AuditService()

# Denetim oluşturma
audit = audit_service.create_audit(user_id, username, region, activity, date)

# İhlal ekleme
audit_service.add_violation(audit, description, violation_type, penalty_id, amount)

# Denetimi tamamlama
audit_service.complete_audit(audit)
summary = audit_service.get_audit_summary(audit)
```

### SpeciesService
```python
species_service = SpeciesService()

# Boy kontrolü
check = species_service.check_size_compliance(species, size_cm)

# Mevsim kontrolü
check = species_service.check_season_compliance(species, check_date)

# Tümünü valide et
validation = species_service.validate_species(species, size_cm, kind)
```

---

**Versiyon:** 5.0.0 | **Son Güncelleme:** 2024
