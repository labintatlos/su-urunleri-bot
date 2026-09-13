---
name: canli-kontrol
description: Su Ürünleri sitesini canlı sistemde doğrula — Home Assistant'ta kurulu eklenti sürümü, canlı sitenin sağlığı, güvenlik başlıkları, konsol hataları ve oturumlu denetim akışları. Her push/dağıtımdan sonra, kullanıcı "canlıda kontrol et / canlıda çalışıyor mu" dediğinde veya canlıda hata şüphesi olduğunda kullan.
---

# Canlı sistem kontrolü

Bu proje Home Assistant eklentisi olarak çalışır ve dışarıya KeenDNS adresiyle açılır.
Adres, IP ve erişim bilgileri depoda **yoktur**; yalnızca bu bilgisayardaki `yerel/`
klasöründe ve `C:\Users\cemci\erisim_bilgileri.txt` dosyasında durur. Hiçbirini
commit etme, sohbete değer olarak yazma.

## 1. Tek komutla tam kontrol

```bash
python yerel/canli_kontrol.py                 # beklenen sürüm = su_urunleri_bot/config.yaml
python yerel/canli_kontrol.py --sadece-genel  # oturum açmadan
```

Betik sırayla şunları yapar ve her kontrolü ✅/❌/⚪ olarak yazar:
- Home Assistant: güncelleme varlığında GitHub sürümü ve kurulu sürüm (`HA_ANAHTAR`).
- Canlı site: `/health` sürümü beklenenle aynı mı, güvenlik başlıkları, oturumsuz API 401, statik dosyalar.
- Edge + Playwright: http→https, giriş sayfası konsol hataları, telefon/masaüstü yatay taşma.
- `SITE_KULLANICI`/`SITE_SIFRE` varsa: giriş, föy listesi, orkinos föyü + kontrol çizelgesi,
  uluslararası sular denetimi + çizelge, Kolluk İşlemi delil kartı, ceza ve tür tabloları, çıkış.

Çıktı ve ekran görüntüleri: `yerel/canli_kontrol_sonuc/<zaman>/` (`rapor.json`). Çıkış kodu 0 değilse
kalan kontrolleri kullanıcıya olduğu gibi bildir; "çalışıyor" deme.

## 2. Eksik erişim bilgisi

- `HA_ANAHTAR` 401 veriyorsa: kullanıcıdan Home Assistant'ta yeni uzun ömürlü erişim anahtarı
  oluşturup `erisim_bilgileri.txt` dosyasına yazmasını iste.
- Oturumlu akış atlandıysa: kullanıcıdan canlı sitede yalnızca kontrol için **yönetici olmayan**
  bir hesap açıp `SITE_KULLANICI=` ve `SITE_SIFRE=` satırlarını aynı dosyaya yazmasını iste.
- İş bitince dosyayı silmesini öner.

## 3. Sürüm canlıda değilse

Önce `python yerel/ha_update.py` ile mağazayı yenileyip güncellemeyi kur, sonra bu kontrolü tekrar çalıştır.

## 4. Elle keşif (Playwright CLI)

Betiğin kapsamadığı bir ekranı incelemek için `playwright-cli` kullan (çalışma dizini olarak
scratchpad klasörünü seç ki `.playwright-cli/` kayıtları depoya düşmesin):

```bash
playwright-cli open <site adresi>
playwright-cli snapshot          # öğe referansları (e12 gibi)
playwright-cli fill e28 "<kullanıcı>"; playwright-cli click e33
playwright-cli console           # konsol mesajları
playwright-cli screenshot --filename=ekran.png
playwright-cli close
```

Şifreyi komut satırına yazman gerekiyorsa değeri dosyadan okuyup değişkenle geç; çıktıya basma.
