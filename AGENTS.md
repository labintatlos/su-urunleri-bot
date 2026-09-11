# Bu depoda çalışan yapay zekâ asistanları için

Bu dosya Claude Code, ChatGPT/Codex veya başka bir asistanın işi kaldığı yerden
devralabilmesi için yazılmıştır. Kullanıcı Türkçe konuşur; arayüz metinleri ve
kullanıcıya verilen cevaplar Türkçedir.

## Proje

Su Ürünleri Denetim Asistanı: deniz görev alanında su ürünleri denetimi için
mevzuat, ceza ve tür rehberi. Home Assistant OS üzerinde (Raspberry Pi 5) bir
eklenti olarak çalışan, kullanıcı adı ve şifreyle açılan bir web sitesidir.
Eskiden Telegram botuydu; 6.0.0 ile tamamen web sitesine geçildi. Ekran
mantığı ve düğme verileri Telegram botundan birebir taşındı.

Mimari, dosya yapısı ve veritabanı tabloları için [README.md](README.md),
dağıtım ve KeenDNS için [DEPLOYMENT.md](DEPLOYMENT.md).

## Değişmez kurallar

1. **Çalışan özellikler korunur.** Mevcut davranış gereksinimdir. Büyük yeniden
   yazım yapılmaz; değişiklik küçük adımlarla yapılır ve her adım eskisiyle
   karşılaştırılarak doğrulanır.
2. **Çalıştırmadan "bitti" denmez.** Kod gerçekten çalıştırılmadan ve test
   çıktısı görülmeden hiçbir iş "tamamlandı / test edildi" diye raporlanmaz.
   Doğrulanamayan kısım açıkça söylenir.
3. **Teslim = push + sürüm artışı.** Home Assistant güncellemeyi yalnızca
   GitHub'daki `su_urunleri_bot/config.yaml` içindeki `version` alanından görür.
   Her push'ta (yalnızca doküman değişse bile) sürüm artırılır, commit
   `origin/master`'a gönderilir. Sürüm artmayan push kullanıcı için "hiç
   yapılmamış iş" demektir.
4. **Çalışma düzeni:** Kullanıcı istekleri sırasız verir; asistan sıralar,
   her adımı bitirip pushlar ve bir sonraki adıma geçmeden onay bekler.
5. **İstenmeyen mekanizma eklenmez.** (Örnek: tek kişilik özel bota eklenen hız
   sınırlayıcı normal kullanımı bozmuştu.)
6. **Depo herkese açıktır (public).** Şifre, API anahtarı, erişim anahtarı,
   KeenDNS adresi, MAC adresi ve benzeri hiçbir özel bilgi commit edilmez.
   Erişim bilgisi gerektiğinde kullanıcıdan `C:\Users\cemci\erisim_bilgileri.txt`
   dosyasına yazması istenir (kullanıcının tercih ettiği yöntem; sohbete şifre
   yazdırılmaz) ve iş bitince dosyayı silmesi önerilir.
7. **Canlı sisteme bağlanarak çalışılır.** Home Assistant ve Keenetic modeme
   doğrudan erişilir; dışa aktarılmış dosyalar üzerinden tahmin yürütülmez.
8. Kullanıcıya zamir gerekiyorsa cinsiyet varsayılmaz.

## Yerel notlar (depoda yok)

Bu bilgisayarda depo klasöründeki `yerel/` dizini `.gitignore` ile dışarıda
tutulur. Varsa önce onu okuyun:

- `yerel/NOTLAR.md`: canlı sistemin adresleri, KeenDNS kayıtları, Home Assistant
  güncelleme varlığı, bilinen API ayrıntıları.
- `yerel/ops.py`: Keenetic RCI ve Home Assistant REST yardımcı betiği (bilgileri
  `erisim_bilgileri.txt` dosyasından okur).
- `yerel/ha_update.py`: eklenti mağazasını yenileyip güncellemeyi kurar ve canlı
  siteyi kontrol eder.

## Çalıştırma ve doğrulama

Hiçbir paket gerekmez (Python 3.11+ standart kütüphanesi).

```bash
python tools/smoke_test.py
```

Betik `su_urunleri_bot/web.py`'yi geçici bir veritabanıyla gerçekten başlatır,
kurulum koduyla ilk yöneticiyi oluşturur, giriş yapar ve ana menüden
ulaşılabilen her düğmeye basar; metin bekleyen ekranlara örnek metin yazar.
Beklenen çıktı `errors: 0`'dır ve çıkış kodu 0 olur. Günlükteki
`GEMINI_API_KEY yapılandırılmamış` satırı yerel denemede normaldir.

Arayüz değişikliklerinde ayrıca tarayıcıda telefon, tablet ve masaüstü
genişliklerinde bakılmalıdır.

## Dağıtım adımları

1. Değişikliği yap, `python tools/smoke_test.py` çalıştır, `errors: 0` gör.
2. `su_urunleri_bot/config.yaml` içindeki `version` değerini artır.
3. Commit et ve `git push origin master`.
4. Home Assistant'ta eklenti mağazasını yenile ve güncellemeyi kur
   (`yerel/ha_update.py` bunu yapar; yoksa kullanıcıdan **Ayarlar → Eklentiler →
   Eklenti Mağazası → ⋮ → Güncellemeleri kontrol et** istenir).
5. Canlı sitede `/health` ve değişen davranışı kontrol et.

## Bilinen kısıtlar

- Site dışarıya Keenetic KeenDNS **bulut modu** ile açılır (modemin genel IP'si
  yok). Bu tünel `X-Forwarded-For` / `X-Forwarded-Proto` iletmez ve `http://`
  isteklerini de siteye geçirir:
  - Her istek sunucuya modemin adresinden gelir; gerçek ziyaretçi IP'si
    bilinemez. Hatalı giriş kilidi fiilen kullanıcı adına göre çalışır.
  - `http://` → `https://` yönlendirmesi sunucuda yapılamaz; `static/app.js`
    en başta alan adıyla `http://` açıldıysa sayfayı `https://`'e taşır ve
    8101 portu `Strict-Transport-Security` gönderir. Bu kod silinmemelidir.
  - Oturum çerezinin `Secure` bayrağı bu yüzden `X-Forwarded-Proto`'ya değil,
    tarayıcının POST isteğine eklediği `Origin` başlığına bakar (`https://` ise
    eklenir). Ev ağında `http://` ile giriş bu sayede çalışmaya devam eder.
- Sunucu bağlantıları 60 sn okuma/yazma zaman aşımıyla çalışır ve aynı anda en
  fazla 4 scrypt hesabı yapılır (Pi'de bellek tüketmeye karşı). Hatalı giriş
  kilidi kullanıcının kararıyla olduğu gibi kaldı; kilit, dış istekler aynı
  adresten geldiği için kullanıcı adına göre çalışır. **Üye ol** formu onay
  bekleyen en fazla 20 başvuru kabul eder (6.0.10).
- 8099 (Ingress) portu dışarı açılmaz; `X-Remote-User-Name` başlığına yalnızca
  Supervisor adresinden gelen istekte güvenilir.

## Yol haritası

Kullanıcının istediği sırayla değil, bağımlılığa göre dizildi. Her adım ayrı
push ve kullanıcı onayıyla ilerler. Durumu adım bitince burada güncelleyin.

| # | Adım | Durum |
|---|------|-------|
| 1 | Devir dokümanı (bu dosya), ortak tarama betiği | ✅ 6.0.2 |
| 2 | Telefon / tablet / PC uyumluluğu (telefonda tek satır üst çubuk, 44 px dokunma hedefleri, çentik boşlukları, yatay telefon, ━━━ ayırıcıları) | ✅ 6.0.3 |
| 3 | Aydınlık / karanlık arayüz | ✅ 6.0.4 |
| 4 | Kullanıcı işlem kayıtları: hangi kişi ne yaptı, yönetici görebilsin | ✅ 6.0.5 |
| 5 | Ana sayfada yönetici onaylı **Üye ol** sekmesi (ad, soyad, e-posta, telefon, statü, kullanıcı adı, şifre) ve **Şifremi unuttum** talebi | ✅ 6.0.6 |
| 6 | Sayfada **Sorun bildir** butonu; yönetici açık bildirimleri görüp kapatabilsin | ✅ 6.0.7 |
| 7 | Açık bulmaya yönelik kapsamlı güvenlik taraması: site, Home Assistant ve Keenetic modem dahil | ✅ 6.0.9 tarama + site düzeltmeleri; 6.0.10 üyelik başvuru sınırı; modem/HA önerileri kullanıcı onayıyla tek tek uygulanıyor |
| 8 | Yeni Markdown klasörünü tek kaynak yap, eski kaynakları kaldır ve eklenti korpusunu eşle | ✅ 6.0.14 |
| 9 | Ceza, tür, madde, saha kuralı ve tekne föyü JSON verilerini yeni kaynaklardan yeniden üret | ✅ 6.0.15 |
| 10 | Ekran/denetim akışlarını yeni kaynak kapsamıyla eşleştir ve çapraz doğrula | ⏳ |

Ara adım: Kullanıcının isteğiyle kapsamlı arayüz yenilemesi yapıldı (6.0.8).
Giriş/üyelik, açıklamalı ana menü kartları, ortak denizcilik teması ve yönetim
pencereleri yenilendi.

Güvenlik taraması (6.0.9): sitede çerez `Secure` bayrağı, bozuk
`Content-Length` ile iş parçacığı kilitlenmesi, bağlantı zaman aşımı, sınırsız
büyüyen kilit sözlüğü ve eşzamanlı scrypt bellek tüketimi düzeltildi. Modem ve
Home Assistant bulguları ev ağına özel bilgi içerdiği için depoda değil,
bu bilgisayardaki `yerel/GUVENLIK_TARAMASI.md` dosyasındadır; oradaki
değişiklikler kullanıcı onayıyla tek tek yapılacak.
