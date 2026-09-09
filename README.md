# Su Ürünleri Denetim Asistanı

**Telegram Bot** | **Home Assistant Eklentisi**

Deniz görev alanında su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesine, ihlallerin tespitine ve uygulanacak işlemlerin belirlenmesine yardımcı olan Telegram botu.

## 🌊 Özellikler

### 📋 Tekne Türü Kılavuzları
Çıkılacak tekneye özel kontrol föyü açılır; her madde **Uygun / Uygunsuz / Kontrol Edilmedi** olarak işaretlenir, sonunda özet ve dayanak maddeleri gösterilir. Ölçüm/kayıt alanları ayrıca girilebilir.

### 🚨 Denetime Başla
Bölge → faaliyet → gemi boyu → tarih → konu → av aracı → tür sırasıyla ilerleyen yönlendirilmiş denetim. Seçimlerden doğrudan çıkan mevzuat uyarıları ile cevaplara göre olası aykırılıklar ayrı ayrı listelenir. Yarıda kalan denetim kaydedilir ve sonra kaldığı yerden sürdürülebilir.

### 📖 Pratik Ceza Rehberi
İdari yaptırım tablosundan ihlal başlığına göre ceza kartları; tutar, ürüne/av aracına el koyma, ruhsat işlemi ve dayanak maddeleri.

### 📖 Pratik Tür Çizelgesi
Ticari (6/1) ve amatör (6/2) türler, asgari boy/ağırlık, alıkonulabilir miktar ve zaman yasakları.

### 🖼️ Görsel Rehberler
Karıştırılan balık türleri için teşhis kartları ve yasak av araçlarının görsel tespiti.

### ⚖️ Hukuki Değerlendirme
Olay serbest metinle anlatılır ve yüklü mevzuatın tam metni üzerinden değerlendirilir. Denetim sonucu ekranlarındaki **“Bu Denetimi Değerlendir”** düğmesi, o denetimde girilen bilgileri ve işaretlenen uygunsuzlukları otomatik olarak değerlendirmeye taşır.

### 💬 Doğrudan Arama
Menüde gezmeden tür, ceza veya mevzuat kelimesi yazmak yeterlidir; tür, ceza ve madde sonuçları birlikte listelenir. Mevzuat maddelerine buradan ve her ekrandaki dayanak düğmelerinden ulaşılır; madde ekranından kaynağın tüm madde listesi açılabilir.

### 🔐 Yönetici Paneli
Kullanıcı istatistikleri, denetim ve arama dağılımı, işlem kayıtları.

## 🚀 Kurulum

### Home Assistant Eklentisi (kullanılan yöntem)

Depoyu Home Assistant’a eklenti deposu olarak ekleyin, ardından eklenti ayarlarından doldurun:

```yaml
bot_token: "TELEGRAM_BOT_TOKEN"
admin_id: "123456789"
allowed_users: ["123456789"]
gemini_api_key: ""          # Hukuki değerlendirme için (opsiyonel)
gemini_model: "gemini-3.6-flash"
result_limit: 8
timezone: "Europe/Istanbul"
```

Eklenti `run.sh` üzerinden `bot.py` dosyasını çalıştırır.

### Yerel Çalıştırma

```bash
cd su_urunleri_bot
pip install -r requirements.txt

export TELEGRAM_TOKEN="..."
export ADMIN_IDS="123456789"
export ALLOWED_USER_IDS="123456789"
export GEMINI_API_KEY="..."      # opsiyonel

python bot.py
```

## 📖 Komutlar

| Komut | Açıklama |
|-------|----------|
| `/start` · `/menu` | Ana menüyü aç |
| `/id` | Telegram kullanıcı ID’nizi göster |
| `/admin` · `/istatistik` | Yönetici paneli (yalnız yönetici) |

## 🏗️ Yapı

```
su_urunleri_bot/
├── bot.py            # Botun tamamı: menüler, denetim akışları, arama, AI
├── db.py             # SQLite şeması, veri yükleme ve arama
├── data/             # Mevzuat, tür, ceza ve kılavuz verileri (JSON)
│   ├── articles.json          # Kanun/yönetmelik/tebliğ maddeleri
│   ├── penalty_cards.json     # İdari yaptırım tablosu
│   ├── vessel_guides.json     # Tekne türü kontrol föyleri
│   └── sources.json           # Kaynak metin tanımları
├── config.yaml       # Home Assistant eklenti tanımı
├── Dockerfile
└── run.sh            # Eklenti giriş noktası
```

Veriler `data/` altındaki JSON dosyalarından SQLite’a yüklenir. `db.py` içindeki
`DATASET` sürümü değiştiğinde veritabanı yeniden kurulur; veri dosyalarını
güncelledikten sonra bu sürümü artırmak gerekir.

## 📊 Veritabanı Tabloları

`sources`, `articles`, `rules`, `commercial_species`, `amateur_species`,
`prohibited_species`, `penalty_cards`, `raw_excel_rows`, `users`, `query_log`,
`inspections`, `meta`.

## 📚 Mevzuat Kaynakları

- 1380 sayılı Su Ürünleri Kanunu
- Su Ürünleri Yönetmeliği
- 6/1 Numaralı Ticari Amaçlı Su Ürünleri Avcılığı Tebliği (2024/20)
- 6/2 Numaralı Amatör Amaçlı Su Ürünleri Avcılığı Tebliği (2024/21)
- Balıkçı Gemilerini İzleme Sistemi Tebliği (2021/26)
- İdari yaptırım (ceza) tablosu

6/1 ve 6/2 tebliğleri **1/9/2024 – 31/8/2028** av dönemi için yayımlanmıştır.
Dönem sonunda yenileriyle değiştirilirler; yeni metinler `data/` altındaki JSON
dosyalarına işlenmeden bot eski hükümlerle cevap vermeye devam eder.

## ⚠️ Sorumluluk

Bot bir karar destek aracıdır. Ürettiği hiçbir sonuç nihai yaptırım kararı
değildir; dayanak maddeler ve ceza tablosundaki maddi unsurlar her olayda ayrıca
doğrulanmalıdır.
