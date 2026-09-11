# Su Ürünleri Denetim Asistanı

**Web Sitesi** | **Home Assistant Eklentisi**

Deniz görev alanında su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesine, ihlallerin tespitine ve uygulanacak işlemlerin belirlenmesine yardımcı olan web sitesi. Telefondan ve bilgisayardan kullanıcı adı ve şifreyle açılır; Telegram'a bağımlılığı yoktur. Home Assistant OS yalnızca sunucuyu çalıştıran makinedir.

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
Olay serbest metinle anlatılır ve eklentiyle paketlenen Markdown mevzuat belgelerinin tam metni üzerinden Gemini 3.5 Flash-Lite ile değerlendirilir. Yanıtlar daima **Kanun → Yönetmelik → Tebliğ** sırasıyla hazırlanır; somut karşılığı bulunmayan bölümün yeri boş bırakılarak sıra korunur. Denetim sonucu ekranlarındaki **“Bu Denetimi Değerlendir”** düğmesi, o denetimde girilen bilgileri ve işaretlenen uygunsuzlukları otomatik olarak değerlendirmeye taşır.

### 💬 Doğrudan Arama
Üstteki arama kutusuna tür, ceza veya mevzuat kelimesi yazmak yeterlidir; tür, ceza ve madde sonuçları birlikte listelenir. Bir ekran cevap beklediğinde (tür adı, gemi boyu, tarih, olay metni) kutu o ekranın içine gelir.

### 🌗 Aydınlık / Karanlık Görünüm
Site ilk açılışta cihazın görünüm ayarını izler. Giriş ekranındaki veya üst çubuktaki ay/güneş düğmesiyle görünüm değiştirilebilir; seçim aynı tarayıcıda korunur.

### 🎨 Denizcilik Temalı Arayüz
6.0.8 ile giriş ve üyelik ekranları, ana sayfa, rehberler ve yönetim pencereleri ortak lacivert/turkuaz görünüme kavuştu. Ana menü açıklamalı ve vektör simgeli işlem kartları sunar. Telefonlarda tek sütun, tablet ve bilgisayarlarda iki sütun kullanılır; dokunma hedefleri, klavye odağı ve azaltılmış hareket tercihi desteklenir. Görseller ve yazı tipleri için dış servis gerekmez.

### 👤 Üyelik ve Şifre Yenileme
Giriş ekranındaki **Üye ol** sekmesinden ad, soyad, e-posta, telefon, statü, kullanıcı adı ve şifreyle başvuru yapılır. Hesap yönetici onayına kadar giriş yapamaz. **Şifremi unuttum** bağlantısıyla kullanıcı adı veya e-posta üzerinden talep oluşturulur; yönetici **Kişiler / Şifreler** ekranından yeni şifre vererek talebi kapatır.

### 🛠 Sorun Bildirimi
Hesap menüsündeki **Sorun bildir** düğmesiyle karşılaşılan problem yöneticiye iletilir. Yönetici panelinde açık bildirim sayısı, bildiren kişi, zaman ve açıklama görünür; çözülen bildirim tek düğmeyle kapatılır.

### 🔐 Yönetici Paneli ve Kişiler
Kullanıcı istatistikleri, denetim ve arama dağılımı, hangi kişinin ne zaman hangi işlemi yaptığını gösteren son 30 işlem kaydı. Giriş/çıkış, düğme kullanımı, arama ve hesap yönetimi kaydedilir; parolalar kayda alınmaz. Yönetici **Kişiler / Şifreler** ekranından kişi ekler, şifre verir, yönetici yapar veya pasifleştirir. Herkes kendi şifresini sağ üstteki menüden değiştirebilir.

## 🚀 Kurulum

Depoyu Home Assistant'a eklenti deposu olarak ekleyin ve eklentiyi kurun. Ayarlar:

```yaml
gemini_api_key: ""          # Hukuki değerlendirme için (opsiyonel)
gemini_model: "gemini-3.5-flash-lite"
result_limit: 8
timezone: "Europe/Istanbul"
```

İlk açılışta site bir **kurulum kodu** ister; kod eklentinin **Günlük** sekmesinde yazar. Ev dışından HTTPS ile açmak için KeenDNS adımları [DEPLOYMENT.md](DEPLOYMENT.md) içindedir.

| Adres | Giriş |
|-------|-------|
| Home Assistant yan menüsündeki **Su Ürünleri** | HA oturumu (ilk seferde bir kez site şifresi) |
| `http://homeassistant.local:8101` (ev ağı) | kullanıcı adı ve şifre |
| KeenDNS adresi (HTTPS) | kullanıcı adı ve şifre |

### Yerel Çalıştırma

Hiçbir paket kurmak gerekmez (yalnızca Python 3.11+ standart kütüphanesi):

```bash
cd su_urunleri_bot
export GEMINI_API_KEY="..."      # opsiyonel
python web.py                    # http://localhost:8101
```

## 🏗️ Yapı

```
su_urunleri_bot/
├── web.py            # HTTP sunucusu: giriş, oturum, API, statik dosyalar
├── screens.py        # Bütün ekranlar ve akışlar: menüler, denetim, arama, AI
├── accounts.py       # Kişiler, şifre özeti, oturum çerezi, kurulum kodu
├── db.py             # SQLite şeması, veri yükleme ve arama
├── static/           # Arayüz (index.html, app.js, style.css)
├── data/             # Mevzuat, tür, ceza ve kılavuz verileri (JSON)
│   ├── markdown/              # Yeni ana kaynak klasörünün paketlenmiş kopyası
│   ├── articles.json          # Kanun/yönetmelik/tebliğ maddeleri
│   ├── penalty_cards.json     # İdari yaptırım tablosu
│   ├── vessel_guides.json     # Tekne türü kontrol föyleri
│   └── sources.json           # Kaynak metin tanımları
├── config.yaml       # Home Assistant eklenti tanımı
├── Dockerfile
└── run.sh            # Eklenti giriş noktası
```

Depo kökündeki `SU ÜRÜNLERİ KAYNAKLAR (MARKDOWN)/` klasörü içerik için tek ana
kaynaktır. Eklenti derleme bağlamına girebilmesi için bu klasördeki Markdown
belgelerinin birebir kopyası `data/markdown/` altında paketlenir; duman testi iki
klasörün dosya adlarını ve içeriklerini karşılaştırır. Normal arama ve denetim
verileri `data/` altındaki JSON dosyalarından SQLite'a yüklenir. Hukuki
Değerlendirme ise paketlenmiş Markdown belgelerinin tamamını doğrudan ve tam
metin olarak kullanır. `db.py` içindeki `DATASET` sürümü değiştiğinde veritabanı
yeniden kurulur; JSON veri dosyalarını güncelledikten sonra bu sürümü artırmak
gerekir.

## 📊 Veritabanı Tabloları

`sources`, `articles`, `rules`, `commercial_species`, `amateur_species`,
`prohibited_species`, `penalty_cards`, `raw_excel_rows`, `users`, `query_log`,
`inspections`, `meta`, `web_accounts` (site kişileri ve üyelik onayı),
`password_reset_requests` (şifre yenileme talepleri), `web_state` (kişinin
kaldığı ekran ve akış durumu), `activity_log` (kullanıcı işlem kayıtları),
`issue_reports` (açık ve çözülmüş sorun bildirimleri).

## 📚 Kaynaklar

`SU ÜRÜNLERİ KAYNAKLAR (MARKDOWN)/` altında 1380 sayılı Kanun, Su Ürünleri
Yönetmeliği, 6/1 ve 6/2 numaralı Tebliğler, BAGİS Tebliği ile bunlardan konuya
göre düzenlenen 00-07 rehberleri ve Excel'den doğrulanan 08 numaralı idari ceza
uygulama tablosu bulunur. Klasördeki Excel dosyası ceza tablosunun ham kaynağıdır.

6/1 ve 6/2 tebliğleri **1/9/2024 – 31/8/2028** av dönemi için yayımlanmıştır.
Dönem sonunda yenileriyle değiştirilirler. Kaynak değişiklikleri önce ana kaynak
klasöründe yapılmalı, sonra `su_urunleri_bot/data/markdown/` kopyası aynı içerikle
güncellenmelidir.

## ⚠️ Sorumluluk

Site bir karar destek aracıdır. Ürettiği hiçbir sonuç nihai yaptırım kararı
değildir; dayanak maddeler ve ceza tablosundaki maddi unsurlar her olayda ayrıca
doğrulanmalıdır.
