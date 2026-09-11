# Home Assistant OS Dağıtımı ve KeenDNS

## Mimari

| Giriş | Kimlik | Nereden |
|-------|--------|---------|
| **Web sitesi** (port 8101) | kullanıcı adı ve şifre | ev ağından `http://homeassistant.local:8101`, dışarıdan KeenDNS adresi |
| **Home Assistant paneli** (Ingress, port 8099) | HA oturumu | HA'nın sol menüsündeki **Su Ürünleri** |

İki giriş aynı süreçte, aynı veritabanıyla çalışır. 8101 portu Ingress
başlıklarına hiç güvenmez; kimlik yalnızca şifreyle verilen oturum çerezinden
gelir. 8099 portu dışarıya açılmaz ve `X-Remote-User-Name` başlığına yalnızca
Supervisor'ın adresinden gelen istekte güvenilir.

Veritabanı `/share/su_urunleri_bot/su_urunleri_kolluk.db` içindedir; eklenti
güncellense veya yeniden kurulsa da silinmez. Oturum imza anahtarı
(`session_secret`) da aynı klasördedir.

## 5.x (Telegram botu) → 6.0 geçişi

- Telegram ayarları (`bot_token`, `admin_id`, `allowed_users`) kalkar; bot
  artık Telegram'a bağlanmaz.
- Denetim kayıtları, işlem geçmişi ve istatistikler olduğu gibi kalır; eski
  Telegram kullanıcılarının geçmişi yönetici panelinde görünmeye devam eder.
- Kişiler Telegram kimliğiyle değil, sitede açılan kullanıcı adıyla girer.
  Yönetici herkesi **Kişiler / Şifreler** ekranından ekler.

## İlk kurulum

1. Eklentiyi güncelleyin veya kurun ve başlatın.
2. **Günlük** sekmesinde `İlk yönetici henüz oluşturulmadı ... kurulum kodunu girin: 1234-5678` satırını bulun.
3. Siteyi açın, kodu, adınızı, kullanıcı adınızı ve şifrenizi girin.
4. Sağ üstteki menüden **Kişiler / Şifreler** ile diğer kişileri ekleyin.

Kullanıcı adı 3-32 karakterdir (küçük harf, rakam, nokta, alt çizgi); şifre en
az 8 karakterdir. Aynı kullanıcı adıyla 15 dakika içinde 5 hatalı deneme
yapılırsa o ad bir süre için kilitlenir. Onay bekleyen 20 üyelik başvurusu
varken yeni başvuru alınmaz; yönetici onaylayıp reddettikçe yer açılır.

## KeenDNS ile HTTPS adres (Keenetic modem)

Keenetic modem, KeenDNS alan adı için HTTPS sertifikasını kendisi alır ve gelen
isteği ev ağındaki Raspberry Pi'ye iletir. Modemde port açmak gerekmez.

1. Modem arayüzünü açın (`http://192.168.1.1` veya `my.keenetic.net`).
2. **Ağ kuralları → Alan adı** (bazı sürümlerde **Yönetim → KeenDNS**)
   bölümünde KeenDNS adınızın kayıtlı olduğunu görün (ör. `evim.keenetic.pro`).
3. **Ev ağındaki web uygulamalarına erişim** kısmında yeni kayıt ekleyin:

   | Alan | Değer |
   |------|-------|
   | Ad | `suurunleri` → adres `suurunleri.evim.keenetic.pro` olur |
   | Cihaz | Home Assistant (Raspberry Pi) |
   | Protokol | HTTP (dış tarafta HTTPS'i KeenDNS sağlar) |
   | Port | `8101` |
   | Yetkilendirme | Kapalı (site kendi şifresini ister) |

4. Telefonda mobil veriyle `https://suurunleri.evim.keenetic.pro` adresini açın.

Modemde 8101 portunu doğrudan düz HTTP olarak internete açmayın: şifre
şifrelenmeden gider.

### KeenDNS bulut modunun kısıtları

Modemin genel IP'si yoksa KeenDNS "bulut" modunda çalışır. Bu modda:

- `http://` ile yazılan adres de siteye ulaşır ve modemin "HTTPS'e yönlendir"
  ayarı uygulanmaz. Site bu yüzden `http://` ile açılınca giriş formunu
  göstermeden kendini `https://`'e taşır ve HSTS başlığı gönderir; bir kez
  HTTPS ile girildikten sonra tarayıcı adresi bir daha düz HTTP ile açmaz.
- Modem ziyaretçinin IP'sini iletmez; bütün istekler modemin adresinden gelmiş
  görünür. Hatalı giriş kilidi bu yüzden kullanıcı adına göre çalışır.

## Kontrol

| İstek | Beklenen |
|-------|----------|
| `https://suurunleri.evim.keenetic.pro/health` | `{"status":"ok"}` |
| `https://suurunleri.evim.keenetic.pro/api/screen` (giriş yapmadan) | `401` |

## Sorun giderme

- **Kurulum kodunu bulamıyorum:** Eklentiyi yeniden başlatın; etkin yönetici
  yoksa kod her açılışta günlüğe yeniden yazılır.
- **Şifremi unuttum:** Başka bir yönetici **Kişiler / Şifreler** ekranından
  yeni şifre verebilir.
- **Hukuki değerlendirme çalışmıyor:** Eklenti ayarlarında `gemini_api_key`
  dolu olmalıdır; asıl hata eklenti günlüğüne yazılır.
