# GÜNCEL İDARİ CEZA UYGULAMA TABLOSU (Excel Kaynaklı, Doğrulanmış)

*Kaynak: Kullanıcının klasöre eklediği **"Su ürünleri cezaları.xlsx"** dosyası. Bu dosya, 1380 Sayılı Kanun'un 36. maddesindeki idari para cezalarının **güncel (yeniden değerlenmiş) TL tutarlarıyla**, somut ihlal senaryolarına göre uygulamaya dökülmüş halidir — muhtemelen denetim personeli için hazırlanmış bir "ceza uygulama kılavuzu"dur. Bu dosyada Excel'deki her kalem, 1380 Sayılı Kanun, Su Ürünleri Yönetmeliği ve 6/1-6/2 Numaralı Tebliğlerin (daha önce Dosya 00-07'de işlenen) orijinal metinleriyle karşılaştırılarak doğrulanmış ve anlaşılır tablolar haline getirilmiştir.*

---

## DOĞRULAMA YÖNTEMİ VE GENEL BULGULAR

### 1) Tutarlar güncellenmiş (yeniden değerlenmiş) tutarlardır
1380 Sayılı Kanun'un metninde (2019 tarihli 7191 sayılı değişiklikle) yazan tutarlar (ör. "beş bin Türk lirası") **sabit değildir**; idari para cezaları her yıl Hazine ve Maliye Bakanlığınca ilan edilen **yeniden değerleme oranı** kadar artırılır. Excel'deki tüm tutarlar, Kanun'daki 2019 taban tutarların **tutarlı bir şekilde yaklaşık 9,48 katına** çıkarılmış halidir. Bu oran onlarca kalemde (aşağıdaki doğrulama tablosunda gösterildiği gibi) neredeyse birebir tutmaktadır, bu da Excel'deki rakamların **güncel bir yıla ait resmi/pratik uygulama tutarları** olduğunu doğrulamaktadır. *(Tam olarak hangi yıla ait olduğu Excel'de belirtilmemiştir; kullanıcı bu tutarları operasyonel olarak kullanacaksa, en güncel yıl için Bakanlık/Resmî Gazete duyurusuyla teyit etmesi önerilir.)*

**Örnek doğrulama (Kanun taban tutarı × 9,48 ≈ Excel tutarı):**

| Kanun m.36 Hükmü | Taban Tutar (Kanun metni) | × 9,48 | Excel'deki Tutar | Sonuç |
| :--- | :---: | :---: | :---: | :---: |
| a bendi, kişi ruhsatsız (min) | 1.000 TL | 9.480 | 9.473 | ✅ Uyumlu |
| c bendi, içsu | 10.000 TL | 94.800 | 94.811 | ✅ Uyumlu |
| c bendi, deniz | 20.000 TL | 189.600 | 189.630 | ✅ Uyumlu |
| g bendi, patlayıcı/zehir | 10.000 TL | 94.800 | 94.811 | ✅ Uyumlu |
| i bendi, yabancı avcılık | 20.000 TL | 189.600 | 189.630 | ✅ Uyumlu |
| j bendi, akarsu engelleme | 1.700 TL | 16.116 | 16.106 | ✅ Uyumlu |
| j bendi, balık geçidi (üst sınır) | 250.000 TL | 2.370.000 | 2.370.440 | ✅ Uyumlu |
| j bendi, geçit çalıştırmama | 50.000 TL | 474.000 | 474.079 | ✅ Uyumlu |
| k bendi, kişi (ticari) | 1.700 TL | 16.116 | 16.106 | ✅ Uyumlu |
| k bendi, gemi (ticari) | 2.500 TL | 23.700 | 23.692 | ✅ Uyumlu |
| k bendi, ışıkla avcılık yasağı | 50.000 TL | 474.000 | 474.079 | ✅ Uyumlu |
| k bendi, amatör kişi | 500 TL | 4.740 | 4.730 | ✅ Uyumlu |
| k bendi, amatör gemi | 750 TL | 7.110 | 7.105 | ✅ Uyumlu |
| l bendi, dip trolü (gemi) | 7.000 TL | 66.360 | 66.357 | ✅ Uyumlu |
| l bendi, trol/Marmara-boğaz (gemi, min) | 20.000 TL | 189.600 | 189.630 | ✅ Uyumlu |
| n bendi, bilgi/belge vermeme | 700 TL | 6.636 | 6.627 | ✅ Uyumlu |
| o bendi, m.29 aykırılığı | 850 TL | 8.058 | 8.048 | ✅ Uyumlu |

Bu güçlü ve tutarlı örtüşme, Excel'in **Kanun m.36'dan doğru türetildiğini** doğrulamaktadır.

### 2) İki farklı hesaplama mantığı var
- **(A) Kanun'un ARALIK verdiği durumlarda** (ör. "5.000-50.000 TL", "1.000-5.000 TL"): Excel, bu aralığın içinde **kademeli/somut tutarlar** seçmiştir (ör. tekne boyuna göre 7 farklı basamak, veya ihlalin ağırlığına göre içsu/deniz/dalarak ayrımı). Bu, Kanun metninin **birebir tekrarı değil**, uygulamada takdir yetkisinin nasıl kullanılacağına dair **pratik bir rehberdir** — yasaya aykırı değildir, çünkü seçilen her değer yasal aralığın içindedir.
- **(B) Kanun'un SABİT tutar verdiği durumlarda** (ör. m.23 ihlalleri için "2.500 TL" sabit): Excel, bu sabit tutara Kanun'un son fıkrasındaki **tekne boyu çarpanını** (12-22 m: 2 kat, 22 m ve üzeri: 3 kat) doğru şekilde uygulamıştır. Ayrıca **gırgır ağıyla işlenen ihlallerde her zaman 3 kat** uygulanacağına dair özel hükmü (m.36/k) de doğru yansıtmıştır.

### 3) Doğrulanamayan veya dış kaynağa dayanan kalemler
Excel'in bazı kalemleri (**b, e, f bentleri** — kiralama ihlalleri, yetiştiricilik tesisi ihlalleri, balıkçı barınağı ihlalleri), elimizdeki 5 kaynak belgede tam metni bulunmayan şu yönetmeliklere atıf yapmaktadır: **"Su Ürünleri Üretiminde Kiralama Yönetmeliği"**, **"Balıkçı Barınakları Yönetmeliği"**, **"Su Ürünleri Yetiştiricilik Yönetmeliği"**. Bu kalemlerin madde numaraları ve tutarları **Kanun m.36 (b/e/f bentleri) ile uyumlu aralıklarda** olsa da, atıf yapılan alt yönetmelik maddelerinin doğruluğu bu oturumda elimizdeki kaynaklarla **doğrulanamamıştır**. Bu kısımlar tabloya sadık şekilde aktarılmış ama işaretlenmiştir.

### 4) Tespit edilen olası tutarsızlıklar (şeffaflık için belirtilmiştir)
- **Dip trolü "kişi/tayfa" tutarı (23.692 TL):** Kanun metni dip trolü ihlalinde hem kişiye hem gemi sahibine **aynı 7.000 TL**'yi öngörür ("...aykırı hareket edenlere **ve** kullanılan gemiler için sahip veya donatanlarına yedi bin Türk lirası..."). Excel'de gemi sahibi için doğru şekilde 66.357 TL (7.000×9,48) kullanılmış, ancak kişi/tayfa için bunun yerine m.23 k-bendinin genel "kişi" tutarı olan 23.692 TL (2.500 TL×9,48) kullanılmıştır. Bunun kasıtlı bir ayrım mı (tayfaya genel kural, donatana özel kural) yoksa satır hatası mı olduğu Excel'den anlaşılamamaktadır.
- **"Avlanması yasak tür" ve "Yasak boy" ihlallerinde gırgır 3 katı tutarı (56.640 TL):** Bu iki kalemde gırgır-3-katı tutarı, diğer tüm k-bendi kalemlerinde tutarlı biçimde kullanılan 71.076 TL yerine 56.640 TL olarak görünmektedir. Bu, diğer ~24 kalemle tutarsızdır ve olası bir veri girişi hatası olabilir.
- **BAGİS "arızası giderilmeden avcılık" kalemi:** 22 metre ve üzeri gemi için verilen tutar (22.647 TL), 12-22 metre gemi için verilen tutardan (32.212 TL) **daha düşüktür**; normalde büyük tekne için ceza daha yüksek olmalıdır. Bu satırda olası bir veri girişi hatası bulunmaktadır.
- **Kiralama ihlali tablosunda "%5*'ye kadar" ifadesi:** Bağlamdan (bir önceki satır "%10'a kadar", tutar sıralaması, bir sonraki satır "%50 dahil fazla") bunun **"%50'ye kadar"** olması muhtemeldir. **Ancak bu bir tahmindir, resmi kaynakla doğrulanmamıştır** — "Su Ürünleri Üretiminde Kiralama Yönetmeliği" elimizdeki 5 kaynak belge arasında yer almadığından gerçek yüzdeyi teyit edemedik. Bu nedenle tabloda **orijinal Excel ifadesi korunmuş**, yalnızca olası okuma önerisi not olarak eklenmiştir; sessizce değiştirilmemiştir.
- **Trol (Marmara/İçsu/Boğaz) genel yasağı için "ruhsat geri alma" uygulanması:** Yönetmelik m.41'in lafzı, ruhsat geri alma yaptırımını yalnızca Kanun m.23-a, m.23-b/1 ve **m.24-b (dip trolü)** ihlalleri için öngörmektedir; m.24-a (Marmara/İçsu/Boğazlarda genel trol yasağı) bu maddede açıkça sayılmamıştır. Excel bu yaptırımı m.24-a ihlaline de uygulamış görünmektedir — bu, muhtemelen idarenin genişletici bir uygulaması olup, doğrudan Yönetmelik'in lafzından çıkmamaktadır.

*(Yazım hataları — "edavat"→"edevat", "ürünleirnin"→"ürünlerinin", "İçsu" birleşik yazımı vb. — sessizce düzeltilerek aktarılmıştır.)*

---

## A) RUHSAT VE İZİN BELGESİ İHLALLERİ (Kanun m.36/a)

### A.1) Ruhsatsız Ticari Avcılık — Kişi (Ruhsat almadan/yeniletmeden)
*İlgili madde: Kanun m.3, Yönetmelik m.4*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Ruhsat tezkeresini yeniletmeden ticari avcılık | 9.473 TL |
| Ruhsat tezkeresini almadan ticari avcılık (içsu) | 18.954 TL |
| Ruhsat tezkeresini almadan ticari avcılık (deniz) | 37.914 TL |
| Ruhsat tezkeresini almadan su ürünleri avcılığı (dalarak) | 47.397 TL |

**El koyma:** Ürüne evet; istihsal vasıtasına evet. *Not: Gırgır, ortasu trolü, dip trolü, algarna veya dalarak avcılıkta **gemi dahil tüm istihsal vasıtalarına** el konur; diğer araçlarla yapılan ihlallerde ilk tespitte gemi hariç el konur.*

### A.2) Ruhsatsız Ticari Avcılık — Gemi (tekne boyuna göre)
*İlgili madde: Kanun m.3, Yönetmelik m.4-5*

| Tekne Boyu | İPC Tutarı |
| :--- | :---: |
| 5 metre altı | 47.397 TL |
| 5 m. dahil - 10 m.'den küçük | 94.811 TL |
| 10 m. dahil - 12 m.'den küçük | 142.217 TL |
| 12 m. dahil - 18 m.'den küçük | 237.034 TL |
| 18 m. dahil - 22 m.'den küçük | 331.855 TL |
| 22 m. dahil - 35 m.'den küçük | 379.267 TL |
| 35 m. ve üstü | 474.079 TL |

### A.3) Amatör Avcılık İhlali
*İlgili madde: Kanun m.3/2, Yönetmelik m.6*

| Durum | İlk İhlal | Tekrarında (Birden Fazla İhlal) |
| :--- | :---: | :---: |
| Gemi kullanmamışsa | 2.356 TL | 4.730 TL |
| İçsu (gemi kullanmışsa) | 18.954 TL | 28.433 TL |
| Deniz (gemi kullanmışsa) | 28.433 TL | 47.397 TL |

**El koyma:** Ürüne evet; istihsal vasıtasına hayır.

### A.4) Av Miktarı, Bölge ve Av Araçlarına Ait İzinlere Aykırı Faaliyet
*(Kum midyesi av miktarı/bölge ihlali, ortasu trolü, algarna, hamsi avcılığı, kum midyesi avcılık izin belgeleri vb. — 6/1 Tebliğ'in çeşitli "İzin Belgesi" gerektiren maddeleri)*

| Kategori | İPC Tutarı |
| :--- | :---: |
| Kişi | 47.397 TL |
| Gemi — 5 metre altı | 47.397 TL |
| Gemi — 5 m. dahil - 10 m.'den küçük | 94.811 TL |
| Gemi — 10 m. dahil - 12 m.'den küçük | 142.217 TL |
| Gemi — 12 m. dahil - 18 m.'den küçük | 237.034 TL |
| Gemi — 18 m. dahil - 22 m.'den küçük | 331.855 TL |
| Gemi — 22 m. dahil - 35 m.'den küçük | 379.267 TL |
| Gemi — 35 m. ve üstü | 474.079 TL |

**El koyma:** Ürüne evet; istihsal vasıtasına hayır.

### A.5) Diğer a-Bendi İhlalleri

| İhlal | Tekne Boyu | İPC Tutarı |
| :--- | :--- | :---: |
| Ruhsat kod numarasının gemiye yazılmaması | 12 m.'den küçük | 47.397 TL |
| Ruhsat kod numarasının gemiye yazılmaması | 12 m. ve üstü | 94.811 TL |
| İzin ve ruhsat belgesini gösterme(me) (kişi/donatan) | — | 9.473 TL |

**El koyma:** Yok (her iki kalemde de hayır/hayır).

---

## B) İSTİHSAL HAKKI KİRALAMA İHLALLERİ (Kanun m.36/b)

*İlgili madde: Kanun m.4; "Su Ürünleri Üretiminde Kiralama Yönetmeliği" Md. 13/1 (⚠️ bu alt yönetmelik elimizdeki kaynaklarda yok, doğrulanamadı)*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Avcılığa ait güncel kayıtların tutulmaması veya bulundurulmaması | 23.692 TL |
| İstihsal alanının şeklinin/özelliğinin değiştirilmesi veya değiştirilmesine izin verilmesi | 94.811 TL |
| Kira süresi sonunda/sözleşme feshinde kiralanan yerin istenilen şartlarda teslim edilmemesi | 142.217 TL |
| Şartnamedeki miktardan %10'a kadar fazla avcılık yaptırılması | 47.397 TL |
| Şartnamedeki miktardan %10 dahil %5\*'ye kadar fazla avcılık yaptırılması *(⚠️ Excel'deki orijinal ifade budur; bağlamdan "%50" olması muhtemel görünüyor ama bu resmi kaynakla doğrulanamamıştır — bkz. not)* | 94.811 TL |
| Şartnamedeki miktardan %50 dahil fazla avcılık yaptırılması | 189.630 TL |
| Kiracıların kiralama haklarını başkalarına devretmesi | 237.034 TL |

**Genel not (Kanun m.36/b ile uyumlu):** Aynı kabahatin tekrarında idari para cezaları **iki katı** uygulanır ve **kira sözleşmesi feshedilir.**

---

## C) İSTİHSAL YERİNDE DEĞİŞİKLİK (Kanun m.36/c)

*İlgili madde: Kanun m.7, Yönetmelik m.7*

| Yer | İPC Tutarı |
| :--- | :---: |
| İçsu | 94.811 TL |
| Deniz | 189.630 TL |

**El koyma:** Çıkarılan kum/çakıl vb. maddeye evet; istihsal vasıtasına hayır.

---

## D) SU ALIMI VE ÇEVRESEL TEDBİR İHLALLERİ (Kanun m.36/d)

*İlgili madde: Kanun m.9, Yönetmelik m.8*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Akarsudan su alımlarında filtre vb. tedbirleri almama | 47.397 TL |
| Akarsu üzerinde bulunan yetiştiricilik tesisinin suyunu kesme/bırakmama | 237.034 TL |
| Akarsu/göllerde su alımlarında tedbirleri almama | 237.034 TL |
| HES'lerin can suyunu bırakmaması | 474.079 TL |

**El koyma:** Yok.

---

## E) İZİNSİZ YETİŞTİRİCİLİK TESİSİ VE YETİŞTİRİCİLİK YÖNETMELİĞİ İHLALLERİ (Kanun m.36/e)

*İlgili madde: Kanun m.13; "Su Ürünleri Yetiştiricilik Yönetmeliği" (⚠️ elimizdeki kaynaklarda yok, doğrulanamadı — ancak tutarlar Kanun m.36/e'nin "10.000-100.000 TL" aralığıyla uyumludur)*

### E.1) İzinsiz Tesis Kurma (kapasiteye göre)

| Tesis Türü / Kapasite | İPC Tutarı |
| :--- | :---: |
| Kuluçkahane, kapasite < 1 milyon | 94.811 TL |
| Kuluçkahane, kapasite 1-5 milyon | 284.449 TL |
| Kuluçkahane, kapasite 5-10 milyon | 474.079 TL |
| Kuluçkahane, kapasite ≥ 10 milyon | 948.169 TL |
| Büyütme tesisi, kapasite < 50 ton/yıl | 94.811 TL |
| Büyütme tesisi, kapasite 50-250 ton/yıl | 284.449 TL |
| Büyütme tesisi, kapasite 250-500 ton/yıl | 474.079 TL |
| Büyütme tesisi, kapasite ≥ 500 ton/yıl | 948.169 TL |

### E.2) Teknik Personel Bulundurmama

| Kapasite | İPC Tutarı |
| :--- | :---: |
| Kuluçkahane < 10 milyon veya büyütme < 500 ton/yıl | 331.855 TL |
| Kuluçkahane ≥ 10 milyon veya büyütme ≥ 500 ton/yıl | 474.079 TL |

### E.3) Arıtma Sistemi Kurmama/Çalıştırmama

| Kapasite | İPC Tutarı |
| :--- | :---: |
| Kuluçkahane < 5 milyon veya büyütme < 50 ton/yıl | 47.397 TL |
| Kuluçkahane ≥ 5 milyon veya büyütme ≥ 50 ton/yıl | 474.079 TL |

### E.4) Yetiştiricilik Yönetmeliği Hükümlerine Genel Aykırılık (kapasiteye göre)

| Tesis Türü / Kapasite | İPC Tutarı |
| :--- | :---: |
| Kuluçkahane < 1 milyon | 47.397 TL |
| Kuluçkahane 1-5 milyon | 189.630 TL |
| Kuluçkahane 5-10 milyon | 284.449 TL |
| Kuluçkahane ≥ 10 milyon | 474.079 TL |
| Büyütme tesisi < 50 ton/yıl | 47.397 TL |
| Büyütme tesisi 50-250 ton/yıl | 189.630 TL |
| Büyütme tesisi 250-500 ton/yıl | 284.449 TL |
| Büyütme tesisi ≥ 500 ton/yıl | 474.079 TL |

### E.5) Kiralanan Su/Su Alanının Fazla Kullanımı

| Fazla Kullanım Oranı | İPC Tutarı |
| :--- | :---: |
| %10'a kadar fazla | 47.397 TL |
| %10 dahil - %30'a kadar fazla | 94.811 TL |
| %30 dahil - %60'a kadar fazla | 189.630 TL |
| %60 dahil ve fazlası | 237.034 TL |

**Genel not:** Bu bölümdeki (E) tüm cezalar, **proje kapasitesi 250 ton/yıl ve üzeri** olan yetiştiricilik tesisleri ile **kuluçkahane kapasitesi 5 milyon adet/yıl ve üzeri** olanlar için **iki katı** uygulanır.

---

## F) BALIKÇI BARINAKLARI MEVZUATINA AYKIRILIK (Kanun m.36/f)

*İlgili madde: Kanun m.17; "Balıkçı Barınakları Yönetmeliği" (⚠️ elimizdeki kaynaklarda yok, doğrulanamadı — tutarlar Kanun m.36/f'nin "2.500-25.000 TL" aralığından belirgin şekilde yüksek görünmektedir, bu farkı not ediyoruz)*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Barınakta bağlama planı yapılmaması | 23.692 TL |
| Barınakta ticari amaçla avcılığa izin verilmesi | 23.692 TL |
| Barınakta mevzuata aykırı yapı yapılması | 237.034 TL |
| Barınak/üst yapıların amaç dışı kullanılması veya kullandırılması | 142.217 TL |
| Kiralanan barınak/üst yapının 3. şahıslara kiralanması, devri veya ortak alınması | 237.034 TL |
| Bakanlıkça belirtilen gemilerin barınaktan yararlanmasına izin verilmemesi | 142.217 TL |

> ⚠️ **Doğrulama notu:** Kanun m.36/f'nin lafzı bu ihlaller için "2.500-25.000 TL" aralığı öngörmektedir (×9,48 ≈ 23.700-237.000 TL). Tablodaki 237.034 TL ve 142.217 TL tutarları bu aralığın **üst sınırına yakın veya sınırında** kalmaktadır, dolayısıyla aralığın dışına çıkmamaktadır; sadece aralığın üst ucundan seçim yapıldığı görülmektedir. Aralık kontrolü yapılmış ve **uyumlu** bulunmuştur.

---

## G) PATLAYICI/ZEHİRLİ MADDE İLE AVCILIK (Kanun m.36/g)

*İlgili madde: Kanun m.19, Yönetmelik m.9*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Patlayıcı, öldürücü, uyuşturucu, elektroşok vb. ile avcılık | 94.811 TL |

**El koyma:** Ürüne evet; ihlale neden olan av aracı/eşya/alet/edevat/teçhizata evet (zapt ve kamuya geçirme).

---

## H) SULARA ZARARLI MADDE DÖKÜLMESİ (Kanun m.36/h)

*İlgili madde: Kanun m.20, Yönetmelik m.11*

| Sorumlu | İPC Tutarı |
| :--- | :---: |
| Kişi | 47.397 TL |
| Gıda/Tarım İşletmecisi | 189.630 TL |
| Sanayi İşletmecisi | 474.079 TL |

**El koyma:** Yok.

---

## I) YABANCILARIN SU ÜRÜNLERİ İSTİHSALİ YASAĞI (Kanun m.36/i)

*İlgili madde: Kanun m.21, Yönetmelik m.5*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Yabancıların su ürünleri istihsali yasağı ihlali | 189.630 TL |

**El koyma:** Ürün ve istihsal vasıtasına (gemi dahil) evet — zapt ve kamuya geçirme.

---

## J) AKARSU ENGELLEME VE BALIK GEÇİDİ İHLALLERİ (Kanun m.36/j)

*İlgili madde: Kanun m.22, Yönetmelik m.8*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Akarsulara engel (ağ, bent, çit vs.) koyma | 16.106 TL |
| Balık geçidi yapmayanlara *(18 ay süre verilir, süre sonunda uygulanır)* | 2.370.440 TL |
| Balık geçidi işlevsiz olduğunda gerekli tedbirleri almayanlara | 1.896.350 TL |
| Balık geçidi/göç yapısı varken çalıştırmayanlara | 474.079 TL |

**El koyma:** Yok. **Not:** Akarsu engelleme ihlalinde faaliyet durdurulur ve engel kaldırma masrafı failden tahsil edilir.

---

## K) TİCARİ AVCILIK USUL/ESASINA AYKIRILIK — TEKNE BOYUNA GÖRE (Kanun m.36/k)

*İlgili madde: Kanun m.23-a/b (genel atıf); her satırda ayrıca ilgili Yönetmelik ve 6/1 Tebliğ maddesi belirtilmiştir.*

**Ortak kurallar (tüm bu bölümdeki ihlaller için geçerlidir, tekrar tekrar yazılmamıştır):**
- **Tekne boyu çarpanı** *(Kanun m.36 son fıkra)*: 12-22 metre (dahil) → **2 kat**; 22 metre ve üzeri → **3 kat**. Taban tutar 12 metreden küçük gemiler için geçerlidir.
- **Gırgır istisnası** *(Kanun m.36/k)*: İhlal **gırgır ağı** ile işlenmişse, tekne boyuna bakılmaksızın ceza her zaman **3 kat** (taban × 3) uygulanır.
- **Tekrar halinde ceza 2 katı** uygulanır (kabahatin tespitinden itibaren 2 yıl içinde tekrarı).
- **Ruhsat geri alma** *(Yönetmelik m.41)*: İlk ihlalde **1 ay**, ikinci ihlalde **3 ay** geri alınır, üçüncü ihlalde **iptal** edilir.
- **El koyma:** Aksi belirtilmedikçe ürüne evet, istihsal vasıtasına evet (**gemi hariç**).

| İhlal Nedeni | İlgili Madde (Yönetmelik/Tebliğ) | Taban (<12m) | 12-22m (2×) | 22m+ / Gırgır (3×) |
| :--- | :--- | :---: | :---: | :---: |
| 23. madde hükümlerine aykırı faaliyet yapan kişi (tayfa) | Yön. 16/14 | 16.106 TL *(sabit, tekne boyu ayrımı yok)* | — | — |
| Yasak zamanda gırgır ağlarıyla istihsal | Tebliğ 12 | 23.692 TL | 47.384 TL | 71.076 TL |
| Gırgır ağı ölçüm belgesi olmaması | Yön.14 / Tebliğ 12/7 | 23.692 TL | 47.384 TL | 71.076 TL |
| Parakete ve fanyalı ağ ile kalkan avcılığı | Yön.14 / Tebliğ 21-1/d | 23.692 TL | 47.384 TL | 71.076 TL |
| Deniz salyangozu avcılığı (05:00-20:00 dışı) | Yön.16/14 / Tebliğ 29/1-ç | 23.692 TL | 47.384 TL | 71.076 TL |
| Birden fazla algarna ile avlanma | Yön.17/5 / Tebliğ 29/1-c(4) | 23.692 TL | 47.384 TL | 71.076 TL |
| 90 kulaçtan (164 m) daha derin gırgır ağı | Yön.14 / Tebliğ 12/5 | 23.692 TL | 47.384 TL | 71.076 TL |
| Derinlik yasağına aykırı avcılık (18-24 m'den sığda vb.) | Yön.16/14 / Tebliğ 12/6-a | 23.692 TL | 47.384 TL | 71.076 TL |
| Yasak zamanda av aracını gemi/istihsal yerinde bulundurma | Yön.16/7 / Tebliğ 50/10, 51/5 | 23.692 TL | 47.384 TL | 71.076 TL |
| Tüp, nargile, zıpkın, sualtı tüfeği vb. ile balık avcılığı | Yön.17/8 / Tebliğ 49/11 | 23.692 TL | 47.384 TL | 71.076 TL *(el koyma yalnız 3. tekrarda)* |
| Misina ağlarıyla avcılık kurallarını ihlal (denizde) | Yön.14 / Tebliğ 14/2-ç | 23.692 TL | 47.384 TL | 71.076 TL |
| Şamandıralara plaka yazılmaması / markasız av aracı | Yön.15/3, 14 / Tebliğ 49/2 | 23.692 TL | 47.384 TL | 71.076 TL |
| Manyat, ığrıp, trata, tarlakoz vb. sürütme ağlarıyla avcılık | Yön.14 / Tebliğ 14/1 | 23.692 TL | 47.384 TL | 71.076 TL |
| 12 metreden küçük tekneyle gırgır avcılığı | Yön.13 | 23.692 TL | — | 71.076 TL *(yalnızca gırgırla avlanıyorsa)* |
| İkinci av aracı bulundurma (12 m ve üzeri teknelerde) | Yön.14 / Tebliğ 50/11 | — *(kural yalnız ≥12m'ye uygulanır)* | 47.384 TL | 71.076 TL |
| Tırıvırı ile avcılık | Yön.14 / Tebliğ 49/13 | 23.692 TL | 47.384 TL | 71.076 TL |
| Zaman/yer yasağı ihlali (algarna ile deniz salyangozu) | Yön.16/14 / Tebliğ 29/c | 23.692 TL | 47.384 TL | 71.076 TL |
| Zaman/yer yasağı ihlali (beyaz kum midyesi) | Yön.16/14 / Tebliğ 28/1,9 | 23.692 TL | 47.384 TL | 71.076 TL |
| Kalkan avcılığı kuralları ihlali (zaman, araç, izin belgesi vs.) | Yön.16/14, 14, 15/4 / Tebliğ 21/1-a | 23.692 TL | 47.384 TL | 71.076 TL |
| Palamut kuralları ihlali (zaman, araç) | Yön.16/14, 14 / Tebliğ 20/1 | 23.692 TL | 47.384 TL | 71.076 TL |
| Tebliğ ile belirlenen akarsu mansabı 500 m yarıçapta ticari avcılık | Yön.17/6 / Tebliğ 49/19 | 23.692 TL | 47.384 TL | 71.076 TL |
| Liman, barınak, barınma yeri, çekek yerinde avcılık | Yön.16/14 / Tebliğ 50/8 | 23.692 TL | 47.384 TL | 71.076 TL |
| Serpme ile ticari avcılık (içsu) | Yön.16/14 / 6/2 Tebliğ 13-2 | 23.692 TL *(sabit, tekne boyu ayrımı yok)* | — | — |
| Yetiştiricilik tesislerine mesafe yasağına uymama | Yön.16/14 / Tebliğ 49/15 | 23.692 TL | 47.384 TL | 71.076 TL |
| Işıkla avcılık *(içsu/Karadeniz/Marmara/Boğazlar — Kanun m.36/k özel hüküm)* | Yön.16/14 / Tebliğ 13 | 474.079 TL | 948.158 TL | 1.422.237 TL |
| Avlanması yasak tür avlamak (tür yasağı, Tebliğ m.16) | Yön.16/14 / Tebliğ 16/1 | ⚠️56.640 TL *(bkz. tutarsızlık notu)* | 47.384 TL | 71.076 TL |
| Yasak boyda su ürünü avlama (Tebliğ m.17) | Yön.16/14 / Tebliğ 17/1 | ⚠️56.640 TL *(bkz. tutarsızlık notu)* | 47.384 TL | 71.076 TL |

*Son iki satırda el koyma notu farklıdır: "Evet (3 tekrar sonunda gemi hariç)" — yani istihsal vasıtasına el koyma ancak üçüncü tekrarda uygulanır.*

### K.1) Amatör Avcılık Kurallarının İhlali (m.23-a/b, amatör kısmı)

| Kategori | İPC Tutarı |
| :--- | :---: |
| Kişi | 4.730 TL |
| Gemi | 7.105 TL |

**El koyma:** Ürüne evet; istihsal vasıtasına evet (gemi hariç) — *kullanımı yasak araçlara doğrudan el konur, tekrarında gemi hariç tüm araçlara el konur.*

---

## L) TROL YASAĞI İHLALLERİ (Kanun m.36/l)

> ⚠️ **Düzeltme notu:** Excel'de bu bölümdeki "Kanunun 36. Maddesinin" sütununda harf yerine sayısal "1" değeri görünmektedir; bu açıkça Kanun m.36'nın **"l" bendi**ni (küçük L harfi) ifade etmektedir, sayısal bir madde numarası değildir. Aşağıda doğru şekilde "l bendi" olarak belirtilmiştir.

### L.1) İçsular, Marmara Denizi, İstanbul ve Çanakkale Boğazlarında Trol Avcılığı (Kanun m.24/a)

| Sorumlu | Tekne Boyu | İPC Tutarı |
| :--- | :--- | :---: |
| Kişi (tayfa) | — | 94.811 TL *(sabit)* |
| Gemi donatanı/sahibi | <12 m | 189.630 TL |
| Gemi donatanı/sahibi | 12-22 m (2×) | 379.260 TL |
| Gemi donatanı/sahibi | 22 m ve üzeri (3×) | 568.890 TL |

**El koyma (donatan/sahip için):** İstihsal vasıtalarına evet — Marmara Denizi, İstanbul ve Çanakkale Boğazlarında **zapt ve mülkiyet kamuya geçirme**. **Tekrarında** (2 yıl içinde): **1-3 yıl hapis + 5.000-10.000 gün adli para cezası**, ürün ve istihsal vasıtalarına (gemi dahil) el konularak müsadere — *(bu ağır ceza, doğrudan Kanun m.36/l metninden gelmektedir).*

**Ruhsat geri alma:** 1. kez 1 ay, 2. kez 3 ay, 3. kez iptal. *(Not: Yönetmelik m.41'in lafzı bu yaptırımı açıkça m.24-b [dip trolü] için öngörmektedir; m.24-a için Excel'in bu yaptırımı da uygulaması idarenin genişletici bir pratiği olabilir — bkz. doğrulama notları.)*

### L.2) Dip Trolüne İlişkin Yasakların İhlali (Kanun m.24/b, Tebliğ m.10)

| Sorumlu | İPC Tutarı |
| :--- | :---: |
| Kişi (tayfa) | 23.692 TL *(sabit)* |
| Donatan/sahip — <12 m | 66.357 TL |
| Donatan/sahip — 12-22 m (2×) | 132.714 TL |
| Donatan/sahip — 22 m ve üzeri (3×) | 199.071 TL |

**El koyma:** Ürüne evet; istihsal vasıtasına evet (gemi hariç). **Ruhsat geri alma:** 1 ay / 3 ay / iptal.

### L.3) Ortasu Trolüne İlişkin Yasakların İhlali (Kanun m.24/c → m.23 hükümleri, Tebliğ m.11)

> ✅ **Doğrulama:** Kanun m.24/c açıkça "Orta su trolu hakkında **23 üncü madde hükümleri uygulanır**" demektedir. Bu nedenle ortasu trolü ihlalleri, dip trolünün özel 7.000 TL'lik cezası yerine, m.23'ün **genel k-bendi tutarlarını** (1.700 TL kişi / 2.500 TL gemi) alır. Excel bu ayrımı **doğru** uygulamıştır.

| Sorumlu | İPC Tutarı |
| :--- | :---: |
| Kişi (tayfa) | 16.106 TL *(1.700 TL tabanı — m.23 kişi cezası)* |
| Donatan/sahip | 23.692 TL *(2.500 TL tabanı — m.23 gemi cezası)* |

**El koyma:** Ürüne evet; istihsal vasıtasına evet (gemi hariç). **Ruhsat geri alma:** 1 ay / 3 ay / iptal.

---

## M) YASAK ÜRÜN TİCARETİ, İZİNSİZ İTHALAT/İHRACAT (Kanun m.36/m)

### M.1) Genel Ticaret İhlalleri
*İlgili madde: Kanun m.25*

| İhlal | İPC Tutarı |
| :--- | :---: |
| Yasak su ürünlerinin satışı, nakli vb. (av sezonunda) | 47.397 TL |
| Yasak su ürünlerinin satışı, nakli vb. (yasak zamanda) | 47.397 TL |
| Avlanması yasak su ürünlerinin imalatta kullanılması/işlenmesi/muhafazası | 94.811 TL |
| Yasak vasıta/usullerle izinsiz ilmi-teknik çalışma yapmak *(Kanun m.29)* | 8.048 TL |
| Kotaya tabi ürünün belgesiz nakli *(Tebliğ m.46/4)* | 47.397 TL |

**El koyma:** Genel ticaret ihlallerinde ürüne evet. İlmi-teknik çalışma ihlalinde de ihlale neden olan araç/eşyaya el koyma ve kamuya geçirme uygulanır. Kotalı ürün nakli ihlalinde ürüne evet, istihsal vasıtasına hayır.

### M.2) İzinsiz İhracat (Kanun m.25/3 — miktar/tür bazlı kademeli)

| Ürün / Miktar | İPC Tutarı |
| :--- | :---: |
| Deniz patlıcanı, 500 gr - 10 kg'a kadar | 237.034 TL |
| Deniz patlıcanı, 10 kg dahil - 100 kg'a kadar | 474.079 TL |
| Deniz patlıcanı, 100 kg dahil ve fazlası | 948.169 TL |
| Çift kabuklu yumuşakça, 2-100 kg'a kadar | 94.811 TL |
| Çift kabuklu yumuşakça, 100 kg dahil - 300 kg'a kadar | 284.449 TL |
| Çift kabuklu yumuşakça, 300 kg dahil ve fazlası | 948.169 TL |
| Sülük, 10-100 adete kadar | 94.811 TL |
| Sülük, 100 adet dahil ve fazlası | 474.079 TL |
| Endemik veya koruma altındaki türleri canlı olarak | 474.079 TL |

**El koyma:** Ürün ve araca (araç dahil) zapt ve kamuya geçirme.

### M.3) İzinsiz İthalat (Yurt İçine Sokma — adet bazlı kademeli)

| Miktar | İPC Tutarı |
| :--- | :---: |
| 1.000 adete kadar | 47.397 TL |
| 1.000 dahil - 3.000 adete kadar | 94.811 TL |
| 3.000 dahil - 5.000 adete kadar | 142.217 TL |
| 5.000 adet dahil ve fazlası | 189.630 TL |

**El koyma:** Ürün ve araca (araç dahil) zapt ve kamuya geçirme.

---

## N) BİLGİ/BELGE VERME VE HEDEF DIŞI AV BİLDİRİM İHLALLERİ (Kanun m.36/n)

*İlgili madde: Kanun m.28*

| İhlal | Tekne Boyu | İPC Tutarı |
| :--- | :--- | :---: |
| Bilgi/belge vermeme (seyir defteri) | <12 m | 6.627 TL |
| Bilgi/belge vermeme (seyir defteri) | 12-22 m (2×) | 13.254 TL |
| Bilgi/belge vermeme (seyir defteri) | 22 m ve üzeri (3×) | 19.881 TL |
| Hedef dışı türün e-seyirde bildirilmemesi *(Tebliğ m.18-b)* | <12 m | 6.627 TL |
| Hedef dışı türün e-seyirde bildirilmemesi | 12-22 m (2×) | 13.254 TL |
| Hedef dışı türün e-seyirde bildirilmemesi | 22 m ve üzeri (3×) | 19.881 TL |

**El koyma:** Yok.

---

## O) BİLİMSEL/TEKNİK ÇALIŞMA İZNİ İHLALİ (Kanun m.36/o)

*(Bu kalem M bölümünde "Yasak vasıta ve usullerle izinsiz ilmi teknik çalışma yapmak" olarak Excel'de m bendine sınıflandırılmıştır; Kanun'un asıl metninde bu ihlal **o bendi** kapsamındadır — Kanun m.29. Excel'in bent sınıflandırmasında küçük bir tutarsızlık olabilir, ancak tutar [8.048 TL = 850 TL × 9,48] Kanun m.36/o ile birebir uyuşmaktadır.)*

---

## P) BAGİS (BALIKÇI GEMİLERİNİ İZLEME SİSTEMİ) İHLALLERİ (Kanun m.36/p)

*İlgili madde: Kanun Ek Madde 4, Yönetmelik m.13, BAGİS Tebliği*

| İhlal | Tekne Boyu <12 m | Tekne Boyu 12-22 m | Tekne Boyu 22 m ve üzeri |
| :--- | :---: | :---: | :---: |
| BAGİS'in afet vb. durumda işlevsiz olduğunu 15 gün içinde bildirmeme *(BAGİS Tebliği m.9/3)* | 9.473 TL | 15.098 TL | 22.647 TL |
| BAGİS arızasını bildirmeme, 12 saat içinde *(BAGİS Tebliği m.8/1)* | 16.106 TL | 32.212 TL | 48.318 TL |
| BAGİS cihazını 15 gün içinde teslim etmeme *(BAGİS Tebliği m.9/1)* | 47.397 TL | 94.397 TL | 142.191 TL |
| BAGİS cihazını takmama/çalıştırmama *(BAGİS Tebliği m.7/1)* | 47.397 TL | 94.397 TL | 142.191 TL |
| BAGİS arızası giderilmeden avcılık yapma *(BAGİS Tebliği m.8/2)* | 16.106 TL | 32.212 TL | ⚠️22.647 TL *(bkz. tutarsızlık notu)* |

---

## R) KARAYA ÇIKIŞ VE NAKİL BELGESİ İHLALLERİ (Kanun m.36/r)

*İlgili madde: Kanun Ek Madde 5, Tebliğ m.46, 49/26*

| İhlal | Tekne Boyu | İPC Tutarı |
| :--- | :--- | :---: |
| İstihsal edilen ürünü karaya çıkış noktalarından boşaltmamak | <12 m | 9.473 TL |
| İstihsal edilen ürünü karaya çıkış noktalarından boşaltmamak | 12-22 m | 28.433 TL |
| İstihsal edilen ürünü karaya çıkış noktalarından boşaltmamak | 22 m ve üzeri | 47.397 TL |
| Nakil belgesi bulundurmamak | — | 18.954 TL |
| Nakil belgesini istenilen şekil/zamanda göndermemek | — | 9.473 TL |

---

## S) İZİNSİZ BALIKLANDIRMA (Kanun m.36/s)

*İlgili madde: Kanun Ek Madde 6, Tebliğ m.49/22*

| Sorumlu | İPC Tutarı |
| :--- | :---: |
| Gerçek kişi | 94.811 TL |
| Tüzel kişi | 189.630 TL |

---

## T) ULUSLARARASI SULARDA İZİNSİZ AVCILIK (Kanun m.36/t)

*İlgili madde: Kanun Ek Madde 7, Yönetmelik m.18, Tebliğ m.50/4*

| Gemi Durumu | Tekne Boyu | İPC Tutarı |
| :--- | :--- | :---: |
| Ruhsatlı balıkçı gemisi | <12 m | 94.811 TL |
| Ruhsatlı balıkçı gemisi | 12-22 m | 189.630 TL |
| Ruhsatlı balıkçı gemisi | 22 m ve üzeri | 284.449 TL |
| Ruhsatsız gemi | <12 m | 189.630 TL |
| Ruhsatsız gemi | 12-22 m | 379.267 TL |
| Ruhsatsız gemi | 22 m ve üzeri | 474.079 TL |

---

## SONUÇ: GENEL DOĞRULAMA DEĞERLENDİRMESİ

Excel dosyasındaki **~45 farklı ihlal senaryosunun büyük çoğunluğu** (yaklaşık %90'ı), 1380 Sayılı Kanun'un 36. maddesi, Su Ürünleri Yönetmeliği ve 6/1-6/2 Numaralı Tebliğlerin ilgili maddeleriyle **birebir tutarlı** bulunmuştur; tutarlar tutarlı bir ~9,48 kat yeniden değerleme oranıyla güncellenmiştir. Tespit edilen birkaç küçük tutarsızlık (yukarıda ⚠️ işaretiyle belirtilmiştir) muhtemelen Excel'in hazırlanması sırasındaki veri girişi hatalarıdır ve kaynak mevzuatın kendisiyle ilgili değildir. Elimizde tam metni bulunmayan üç alt yönetmeliğe (kiralama, balıkçı barınakları, yetiştiricilik) dayanan kalemler ise yapısal olarak Kanun m.36 ile uyumlu görünse de, alt yönetmelik madde numaraları teyit edilememiştir.

*İlgili genel ceza sistemi ve Kanun m.36'nın ham/orijinal metni için Dosya 06'ya bakınız.*
