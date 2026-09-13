# Sürüm Notları

## 6.0.30
* **İşlem geçmişi:** Düğme basışları (geri, ana menü, sayfa, cevaplar) ve yazılan her metin artık kaydedilmez. Yalnızca anlamlı olaylar tutulur: giriş/çıkış, var olan hesaba hatalı giriş ve kilitlenme, şifre ve kişi işlemleri, denetim başlatma/sonuç (bulgu sayısıyla), föy başlatma/tamamlama (uygunsuzluk sayısıyla), kontrol çizelgesi, arama (sonuç sayısıyla), hukuki değerlendirme, yarım denetim, sorun bildirimi. Her kayıt kategori (Denetim, Arama, Hukuki, Oturum, Güvenlik, Yönetim, Destek) ve önem düzeyiyle (bilgi, uyarı, kritik) saklanır; eski kayıtlar otomatik sınıflandırılır.
* **Yönetici paneli:** Dikkat gerektirenler (onay bekleyen üyelik, şifre talebi, açık sorun, hatalı giriş), bugün/7 gün özet tablosu, son önemli işlemler; kategori ve kişi süzgeçli, sayfalı işlem geçmişi; personel tablosu (son giriş, 7 günlük denetim, bulgu ve arama sayıları); kişi özeti; eski gezinme kayıtlarını onayla temizleme.

## 6.0.29
* **Düzeltme:** Hiç çalışmayan service worker kaydı kaldırıldı. Kayıt sayfaya gömülü betik olduğu için sitenin güvenlik politikası (CSP) tarafından her açılışta engelleniyor ve konsola hata düşüyordu. Site her ekran için sunucuya ihtiyaç duyduğundan çevrimdışı önbellek gerçek bir kullanım sağlamıyor, Home Assistant panelinin alt yolunda da yanlış adrese gidiyordu. Ana ekrana ekleme (manifest) korunur.

## 6.0.28
* **Canlı kontrol:** `/health` yanıtı eklenti sürümünü de bildirir; canlı kurulumun doğrulanması için kullanılır.
* **Geliştirme:** Proje becerisi `canli-kontrol` (`.claude/skills/`) ve dağıtım adımlarına canlı doğrulama eklendi; betik ve erişim bilgileri yalnızca yerel bilgisayarda durur.

## 6.0.27
* **Kaynaklar:** `SU ÜRÜNLERİ KAYNAKLAR (MARKDOWN)/` klasörü depodan çıkarıldı; test ve veri üretimi klasör yokken paket kopyasıyla çalışır, paket kopyasında kısıtlı yayın işareti denetlenir.
* **Föyler:** Kontrol listesi yayınlarıyla çapraz doğrulanan 13 madde mevcut föylere eklendi (sonar, IMO, kıyı sürütme ağları, akivades/kidonya eleği, yabancı amatör belgeleri vb.); turizm föyünün madde bağlantıları 6/1 Md.48'e düzeltildi.
* **Yeni föyler:** Yabancı Uyruk/Bayrak, Uluslararası Sular/MEB, Orkinos/Kılıç, Balık Çiftliği.
* **Kolluk İşlem Rehberi:** Delil ve tutanak kontrol listesi, ceza katsayıları, askıdaki ruhsat, adli sevk gerektiren tekrarlar ve 9 yeni saha kartı.
* **Denetim:** Föy ve duruma özel denetim sonucunda yazdırılabilir Kontrol Çizelgesi; uluslararası sular ve balık çiftliği için ek sorular ve föy önerileri.
* **Hukuki değerlendirme:** 09 Saha Uygulama Esasları belgesi korpusa eklendi (usul notu; hüküm ve tutarda mevzuat esas).

## 6.1.5
* **Mimari:** Veritabanı SQLite WAL moduna geçirilerek eşzamanlı okuma/yazma performansı artırıldı.
* **Mimari:** Dev screens.py dosyası screens/ klasöründe modüllere bölündü.
* **Arayüz:** Sürüm notları (Changelog) menüye eklendi.
* **Arayüz:** Single Page Application (SPA) VDOM (Sanal DOM) yaklaşımıyla yenilendi.
* **Offline:** Çevrimdışı (offline) kullanım için PWA Service Worker eklendi.
* **Sunucu:** Asenkron syncio HTTP sunucusuna geçildi.
* **CI/CD:** Otomatik test altyapısı (GitHub Actions) kuruldu.

