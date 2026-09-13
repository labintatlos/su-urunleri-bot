# Sürüm Notları

## 6.0.34
* **Düzeltme:** Ceza Rehberindeki "Kanun 36 Sağlaması" tablosunda hükmün adı görünmüyordu (yalnızca bent yazıyordu); ilk sütun olarak "Hüküm" eklendi.

## 6.0.33
* **Ceza dosyası sağlaması:** Kanun 36'nın 44 hükmü (a–t bentleri ve son fıkralar) Kanun metninde birebir doğrulanarak her ceza kartına bağlandı. Her kartta bent, taban tutarın güncel karşılığı veya kanun aralığı, 12–22 m ×2 / ≥22 m ×3 boy çarpanı, gırgır 3 katı, tekrar (2 kat, özel tekrar, adli yaptırım), ruhsat geri alma, el koyma, Yönetmelik/Tebliğ madde-fıkra atfının varlığı ve konusu, Excel ham satırı sağlanır (`tools/verify_penalties.py`). Duman testi ve veri üretimi sağlama hatasında durur.
* **Kanuna göre düzeltilenler (08 tablosundaki değer kartta saklanır):** Yasak tür/boy gırgır tutarı 56.640 → 71.076 TL; dip trolü kişi cezası 23.692 → 66.357 TL (36/l); BAGİS işlevsizlik bildirmeme 12–22 m 18.946 TL, ≥22 m 28.419 TL; BAGİS takmama/teslim etmeme 12–22 m 94.794 TL; arıza giderilmeden avcılık ≥22 m 48.318 TL; uluslararası sularda ruhsatsız ≥22 m gemi 568.890 TL (kanuni asgari); arıtma kalemleri 36/e; seyir defteri atfı 6/1 Tebliğ 49/9; amatör gemi ve içsu serpme kalemlerine boy kademeleri.
* **Kanundan eklenen kalemler:** Ruhsat belgesini göstermeyen gemi sahibi (boy kademeli), yasak ürünü işleme/muhafaza/ihraç (36/m), yetiştiricilik tesisinde izleme sistemi yükümlülüğü (36/p, 47.397–237.034 TL), askıdaki ruhsatla avcılıkta gemiye el koyma (Kanun 36 son fıkralar).
* **Tekrar ve ruhsat metinleri:** Boş kalan kartlara Kanundaki tekrar hükmü yazıldı; 36/b–f özel tekrar, 36/j ikinci paragraf, 36/l trol ve 36/m yurt dışı çıkarma tekrarındaki adli yaptırım ayrıca belirtilir.
* **Arayüz:** Ceza kartında ve Pratik Ceza Rehberinde "Mevzuat/Kanun sağlaması" satırı; rehbere "Kanun 36 Sağlaması (Tüm Hükümler)" başlığı; Yaptırım Özetinde düzeltilen ve Kanundan eklenen tutarlar işaretlenir.

## 6.0.32
* **Yaptırım özeti:** Kontrol föyü ve duruma özel denetim sonucunda "⚖️ Yaptırım Özeti" düğmesi. Uygunsuz işaretlenen her madde, olası aykırılık ve otomatik mevzuat uyarısı için 08 numaralı güncel ceza tablosundaki kalem, Kanun 36 bendi ve Kanun/Yönetmelik/Tebliğ dayanağı, muhatap (kişi / gemi sahibi), gemi boyuna göre idari para cezası, gırgır gemisi tutarı, el koyma ve tekrar/ruhsat işlemi gösterilir. Boy bilinmiyorsa girilebilir. Toplam tutar bilinçli olarak gösterilmez. Usul maddeleri ve tabloda karşılığı olmayan hükümler açıkça belirtilir, tahmini tutar üretilmez.
* **Kaynak entegrasyonu:** 313 föy maddesi, 59 denetim sorusu ve 11 otomatik uyarı `tools/build_penalty_links.py` ile ceza kartlarına bağlandı (`data/penalty_links.json`). Sağlama: kart ve bent uyumu, boy kademeleri, 36/k tutar tutarlılığı ve her maddenin dayanağının kart madde alanlarıyla eşleşmesi; eşleşmeyen 19 durum gerekçeleriyle kayıtlıdır. Duman testi her profil, boy ve gırgır kombinasyonunu ve her maddeyi ayrıca işler.
* **Kontrol çizelgesi:** Bulgu varsa "Yaptırım ön bilgisi" bölümü eklenir.

## 6.0.31
* **Arayüz:** Her sayfanın alt bilgisine ve giriş ekranına sade bir geliştirici imzası eklendi: "Geliştirici: Aykut Cem CİVELEK". Masaüstünde giriş ekranının sol panelinde, telefonda giriş kartının altında görünür.

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

