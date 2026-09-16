"""Kontrol maddelerini güncel ceza tablosuna bağlar ve eşleştirmeyi sağlar.

    python tools/build_penalty_links.py           # data/penalty_links.json üretir
    python tools/build_penalty_links.py --check   # dosya güncel mi (smoke_test de çağırır)

Her tekne föyü maddesi, yönlendirilmiş denetim sorusu ve otomatik mevzuat
uyarısı bir veya birden fazla "yaptırım profiline" bağlanır. Profil ya 08
numaralı güncel idari ceza tablosundaki kartları (penalty_cards.json), ya Kanun
36/k genel tutarını, ya da açıkça "yaptırım yok / tabloda kalem yok" bilgisini
taşır. Sistem tahmini tutar üretmez.

Sağlama (hata varsa dosya yazılmaz):
  1. Her föy maddesi, soru ve uyarı tam bir eşleştirmeye sahip; fazla anahtar yok.
  2. Profildeki her kart var ve Kanun 36 bendi profilin bendiyle aynı.
  3. Boy kademeli kartlarda kademe sınırları kartın seçenek metniyle aynı.
  4. 36/k gemi tutarları (<12 m, 12–<22 m, ≥22 m) bütün 36/k kartlarında aynı.
  5. Maddenin dayanağı (Kanun/Yönetmelik/Tebliğ maddesi) eşlenen kartlardan en az
     birinin madde alanlarıyla uyuşur ya da kart o alanı belirtmeyen genel kalemdir;
     uyuşmayanlar ACCEPTED_BASIS içinde gerekçesiyle kabul edilmiş olmalıdır.
Rapor: yerel/ klasörü varsa yerel/YAPTIRIM_ESLESTIRME_RAPORU.md yazılır.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'su_urunleri_bot' / 'data'
SCREENS = ROOT / 'su_urunleri_bot' / 'screens' / '__init__.py'
OUTPUT = DATA / 'penalty_links.json'
REPORT = ROOT / 'yerel' / 'YAPTIRIM_ESLESTIRME_RAPORU.md'

K_TIERS = ('<12 m', '12–<22 m', '≥22 m')

# ── Yaptırım profilleri ───────────────────────────────────────────────────
# kind: cards (08 tablosundaki kartlar), k_general (36/k genel tutarı), none.
PROFILES = {
    'ruhsat_kisi': {'kind': 'cards', 'bent': 'a', 'cards': [1, 2, 3, 4],
                    'label': 'Ruhsat tezkeresi olmadan ticari avcılık — kişi',
                    'note': 'Yeniletmeden, içsuda, denizde veya dalarak avcılık durumuna uyan satır uygulanır.'},
    'ruhsat_gemi': {'kind': 'cards', 'bent': 'a', 'cards': [5, 6, 7, 8, 9, 10, 11],
                    'label': 'Ruhsat tezkeresi olmadan avcılık — gemi',
                    'note': 'Gırgır, ortasu/dip trolü, algarna veya dalarak avcılıkta gemi dahil tüm istihsal vasıtalarına el konur.'},
    'ruhsat_goster': {'kind': 'cards', 'bent': 'a', 'cards': [28, 154], 'label': 'İzin ve ruhsat belgesini talepte göstermeme'},
    'plaka': {'kind': 'cards', 'bent': 'a', 'cards': [26, 27], 'label': 'Ruhsat kod numarasının gemiye yazılmaması'},
    'izin': {'kind': 'cards', 'bent': 'a', 'cards': [18, 19, 20, 21, 22, 23, 24, 25],
             'label': 'Av miktarı, bölge ve av aracına ait izne aykırı faaliyet',
             'note': 'Ek-2 izin belgesi, kota veya izinli bölge dışına çıkılması gibi izin koşullarına aykırılıklarda kişi ve gemi için ayrı uygulanır.'},
    'k_genel': {'kind': 'k_general', 'bent': 'k', 'cards': [46],
                'label': 'Ticari avcılık usul ve esaslarına aykırılık (Kanun 23, 36/k)',
                'note': 'Bu hüküm için tabloda ayrı satır yoktur; Kanun 36/k genel tutarları gösterilir. Aykırılık gırgır gemisiyle işlenmişse gemi sahibine 3 kat uygulanır; ruhsat 1 ay / 3 ay geri alınır, tekrarında iptal edilir.'},
    'girgir_zaman': {'kind': 'cards', 'bent': 'k', 'cards': [47]},
    'girgir_olcum': {'kind': 'cards', 'bent': 'k', 'cards': [48]},
    'kalkan_parakete': {'kind': 'cards', 'bent': 'k', 'cards': [49]},
    'salyangoz_saat': {'kind': 'cards', 'bent': 'k', 'cards': [50]},
    'algarna_birden': {'kind': 'cards', 'bent': 'k', 'cards': [51]},
    'girgir_derin': {'kind': 'cards', 'bent': 'k', 'cards': [52]},
    'derinlik': {'kind': 'cards', 'bent': 'k', 'cards': [53]},
    'yasak_donem_arac': {'kind': 'cards', 'bent': 'k', 'cards': [54]},
    'tup_zipkin': {'kind': 'cards', 'bent': 'k', 'cards': [55]},
    'misina': {'kind': 'cards', 'bent': 'k', 'cards': [56]},
    'markasiz': {'kind': 'cards', 'bent': 'k', 'cards': [57]},
    'kiyi_surutme': {'kind': 'cards', 'bent': 'k', 'cards': [58]},
    'girgir_12m': {'kind': 'cards', 'bent': 'k', 'cards': [59]},
    'ikinci_arac': {'kind': 'cards', 'bent': 'k', 'cards': [60]},
    'tirivri': {'kind': 'cards', 'bent': 'k', 'cards': [61]},
    'salyangoz_zaman_yer': {'kind': 'cards', 'bent': 'k', 'cards': [62]},
    'kum_midyesi': {'kind': 'cards', 'bent': 'k', 'cards': [63]},
    'kalkan': {'kind': 'cards', 'bent': 'k', 'cards': [64]},
    'mansap': {'kind': 'cards', 'bent': 'k', 'cards': [66]},
    'liman': {'kind': 'cards', 'bent': 'k', 'cards': [67]},
    'serpme_icsu': {'kind': 'cards', 'bent': 'k', 'cards': [68]},
    'yasak_tur': {'kind': 'cards', 'bent': 'k', 'cards': [69]},
    'yasak_boy': {'kind': 'cards', 'bent': 'k', 'cards': [70]},
    'isik': {'kind': 'cards', 'bent': 'k', 'cards': [71],
             'note': 'Bu yüksek tutar içsular, Karadeniz, Marmara ve boğazlarda ağlarla avlanma amaçlı ışık kullanımı veya donanımı içindir; izinli bölgelerdeki ışık şartlarına aykırılıkta 36/k genel tutarı uygulanır.'},
    'yetistiricilik_mesafe': {'kind': 'cards', 'bent': 'k', 'cards': [116]},
    'amator': {'kind': 'cards', 'bent': 'k', 'cards': [44, 45], 'label': 'Amatör avcılık kurallarının ihlali'},
    'ortasu': {'kind': 'cards', 'bent': 'k', 'cards': [76, 77], 'label': 'Ortasu trolüne ilişkin yasakların ihlali'},
    'trol_marmara': {'kind': 'cards', 'bent': 'l', 'cards': [72, 73], 'label': 'İçsular, Marmara ve boğazlarda trol',
                     'note': 'İki yıl içinde tekrarında gemi sahip/donatanına hapis ve adli para cezası öngörülür (Kanun 36/l).'},
    'dip_trol': {'kind': 'cards', 'bent': 'l', 'cards': [74, 75], 'label': 'Dip trolüne ilişkin yasakların ihlali'},
    'seyir': {'kind': 'cards', 'bent': 'n', 'cards': [78]},
    'hedef_disi': {'kind': 'cards', 'bent': 'n', 'cards': [115]},
    'yasak_urun': {'kind': 'cards', 'bent': 'm', 'cards': [79, 80, 81, 155], 'label': 'Yasak su ürününün satışı, nakli, işlenmesi'},
    'kota_nakil': {'kind': 'cards', 'bent': 'm', 'cards': [114]},
    'ilmi': {'kind': 'cards', 'bent': 'o', 'cards': [82]},
    'bagis_takma': {'kind': 'cards', 'bent': 'p', 'cards': [99]},
    'bagis_ariza': {'kind': 'cards', 'bent': 'p', 'cards': [97, 100], 'label': 'BAGİS arıza bildirimi ve arızalıyken avcılık'},
    'karaya_cikis': {'kind': 'cards', 'bent': 'r', 'cards': [101, 102, 103], 'label': 'Ürünü karaya çıkış noktasından boşaltmamak'},
    'nakil': {'kind': 'cards', 'bent': 'r', 'cards': [112, 113], 'label': 'Nakil/Menşe belgesi ihlalleri'},
    'uluslararasi': {'kind': 'cards', 'bent': 't', 'cards': [104, 105, 106, 107, 108, 109],
                     'label': 'Uluslararası sular / başka ülke sularında izinsiz avcılık',
                     'note': 'Ruhsatlı ve ruhsatsız gemi için ayrı kademeler vardır.'},
    'patlayici': {'kind': 'cards', 'bent': 'g', 'cards': [35]},
    'zararli': {'kind': 'cards', 'bent': 'h', 'cards': [36, 37, 38], 'label': 'Sulara zararlı madde dökülmesi'},
    'yabanci': {'kind': 'cards', 'bent': 'i', 'cards': [39]},
    'balik_landirma': {'kind': 'cards', 'bent': 's', 'cards': [110, 111], 'label': 'İzinsiz balıklandırma'},
    'yetistiricilik_izinsiz': {'kind': 'cards', 'bent': 'e', 'cards': [130, 131, 132, 133, 134, 135, 136, 137],
                               'label': 'İzinsiz yetiştiricilik tesisi', 'note': 'Tutar tesis türü ve kapasitesine göre seçilir.'},
    'yetistiricilik_yon': {'kind': 'cards', 'bent': 'e', 'cards': [142, 143, 144, 145, 146, 147, 148, 149],
                           'label': 'Yetiştiricilik yönetmeliği hükümlerine aykırılık',
                           'note': 'Tutar tesis türü ve kapasitesine göre seçilir; dayanak alt yönetmelik sistemde yoktur.'},
    'aritma': {'kind': 'cards', 'bent': 'e', 'cards': [140, 141], 'label': 'Arıtma sistemi kurmama veya çalıştırmama'},
    'yok_usul': {'kind': 'none', 'label': 'Usul / delil maddesi',
                 'note': 'Bu maddenin eksikliği tek başına idari para cezası gerektirmez; tespit ve işlem eksiği olarak giderilir.'},
    'yok_tablo': {'kind': 'none', 'label': 'Güncel ceza tablosunda karşılığı yok',
                  'note': 'Bu hüküm için ceza tablosunda ayrı kalem bulunmuyor. Uygulanacak Kanun 36 bendi somut olaya göre belirlenmeli; sistem tahmini tutar göstermez.'},
}

# Boy kademeli kartlar: (dahil alt sınır, hariç üst sınır; None = sınırsız).
TIERS = {
    5: (0, 5), 6: (5, 10), 7: (10, 12), 8: (12, 18), 9: (18, 22), 10: (22, 35), 11: (35, None),
    19: (0, 5), 20: (5, 10), 21: (10, 12), 22: (12, 18), 23: (18, 22), 24: (22, 35), 25: (35, None),
    26: (0, 12), 27: (12, None),
    101: (0, 12), 102: (12, 22), 103: (22, None),
    104: (0, 12), 105: (12, 22), 106: (22, None), 107: (0, 12), 108: (12, 22), 109: (22, None),
}

# ── Tekne föyü maddeleri ──────────────────────────────────────────────────
# "föy numarası:madde no = profil,profil". Aynı metin ve dayanağa sahip maddeler
# (ör. her föyün ilk yedi maddesi) tek satırla bütün föylere uygulanır.
GUIDE_RULES = '''
01:1=ruhsat_gemi,plaka
01:2=ruhsat_kisi
01:3=markasiz
01:4=ikinci_arac
01:5=bagis_takma,seyir
01:6=yok_tablo
01:7=patlayici
01:8=girgir_olcum
01:9=girgir_derin
01:10=girgir_zaman
01:11=k_genel,derinlik
01:12=derinlik
01:13=izin,karaya_cikis,k_genel
01:14=isik,izin,k_genel
01:15=k_genel
01:16=k_genel
01:17=yasak_donem_arac,k_genel
01:18=k_genel
01:19=k_genel
01:20=izin,k_genel
01:21=yok_usul
02:8=trol_marmara
02:9=dip_trol
02:10=dip_trol
02:11=dip_trol
02:12=dip_trol
02:13=dip_trol
02:14=dip_trol
02:15=k_genel
02:16=dip_trol
02:17=yasak_donem_arac
02:18=ilmi
02:19=trol_marmara
03:8=ortasu,trol_marmara
03:9=ortasu
03:10=izin
03:11=ortasu
03:12=ortasu
03:13=ortasu
03:14=karaya_cikis
03:15=izin,karaya_cikis
03:16=k_genel
03:17=yasak_donem_arac
03:18=dip_trol
04:8=k_genel
04:9=k_genel
04:10=k_genel
04:11=misina
04:12=misina,izin
04:13=k_genel
04:14=kalkan
04:15=kalkan_parakete
04:16=izin
04:17=yasak_boy,hedef_disi,k_genel
04:18=k_genel
04:19=kiyi_surutme
05:8=k_genel
05:9=k_genel
05:10=k_genel
05:11=kalkan_parakete
05:12=izin,karaya_cikis,k_genel
05:13=yasak_boy,k_genel
05:14=hedef_disi,nakil
05:15=liman,yetistiricilik_mesafe,k_genel
05:16=k_genel
05:17=yok_tablo
06:8=k_genel
06:9=k_genel
06:10=k_genel
06:11=izin
06:12=k_genel,karaya_cikis
06:13=k_genel
06:14=k_genel
06:15=k_genel
06:16=hedef_disi,k_genel
06:17=yok_tablo,k_genel
07:8=kiyi_surutme
07:10=k_genel
07:11=izin
07:12=k_genel
07:13=karaya_cikis
07:14=k_genel
07:15=hedef_disi,nakil
07:16=yok_tablo
07:17=kiyi_surutme
08:8=salyangoz_zaman_yer
08:9=salyangoz_zaman_yer
08:10=salyangoz_zaman_yer
08:11=k_genel
08:12=salyangoz_zaman_yer
08:13=algarna_birden
08:14=salyangoz_zaman_yer
08:15=izin,salyangoz_saat
08:16=k_genel
09:8=kum_midyesi
09:9=kum_midyesi
09:10=izin
09:11=izin
09:12=seyir
09:13=karaya_cikis
09:14=k_genel
09:15=k_genel
09:16=kum_midyesi,algarna_birden
09:18=k_genel
09:19=k_genel
10:8=tup_zipkin
10:9=yok_tablo
10:10=k_genel
10:11=izin
10:12=k_genel
10:13=k_genel
10:14=izin,karaya_cikis,nakil
10:15=izin,nakil,k_genel
10:16=izin,k_genel
10:17=yok_tablo
11:5=isik
11:6=k_genel
11:7=isik
11:8=k_genel
11:9=k_genel
11:10=izin
11:11=k_genel
11:12=k_genel
11:13=k_genel
11:14=isik,k_genel
11:15=izin
12:8=k_genel
12:9=k_genel
12:10=k_genel
12:11=k_genel
12:12=izin,karaya_cikis
12:13=yasak_boy,k_genel
12:14=ikinci_arac
13:1=ruhsat_gemi,plaka
13:2=k_genel
13:3=k_genel
13:4=k_genel
13:5=k_genel
13:6=k_genel
13:7=k_genel
13:8=k_genel
13:9=isik,k_genel
13:10=yasak_urun,nakil,karaya_cikis
14:1=amator
14:2=amator
14:3=amator,patlayici
14:4=amator
14:5=amator
14:6=amator
14:7=amator
14:8=amator
14:9=amator
14:10=amator
14:11=k_genel
14:12=amator
14:13=k_genel
15:1=misina
15:2=misina
15:3=misina
15:4=izin
16:1=k_genel
16:2=izin
16:3=k_genel
16:4=k_genel
16:5=k_genel
16:6=k_genel
16:7=k_genel
16:8=izin,karaya_cikis
16:9=nakil
17:1=k_genel
17:2=izin
17:3=k_genel
17:4=k_genel
17:5=nakil
18:1=k_genel
18:2=k_genel
18:3=izin
18:4=k_genel
19:1=yok_tablo
19:2=yok_tablo
19:3=yok_tablo
19:4=yok_tablo
19:5=amator
20:1=k_genel,serpme_icsu
20:2=amator
20:3=amator
20:4=markasiz
21:1=k_genel
21:2=amator
21:3=amator
22:1=k_genel
22:2=k_genel
22:3=k_genel
22:4=k_genel
22:5=k_genel
23:1=yabanci
23:2=yabanci
23:3=amator
23:4=amator
23:5=ilmi
23:6=k_genel
23:7=yok_usul
24:1=uluslararasi
24:2=uluslararasi
24:3=uluslararasi
24:4=k_genel
24:5=uluslararasi
24:6=yasak_donem_arac
24:7=bagis_takma
24:8=nakil,yasak_urun
24:9=yabanci
25:1=izin
25:2=izin
25:3=k_genel
25:4=k_genel
25:5=k_genel
25:6=k_genel
25:8=yasak_boy
25:9=k_genel
25:10=k_genel
25:11=izin,karaya_cikis
25:12=k_genel
25:13=k_genel
26:1=yetistiricilik_izinsiz
26:2=yetistiricilik_yon
26:3=yok_tablo
26:4=balik_landirma
26:5=yok_tablo
26:6=yok_tablo
26:7=yok_tablo
26:8=zararli,aritma
26:9=nakil
26:10=yetistiricilik_mesafe,k_genel
26:11=k_genel
'''

# ── Yönlendirilmiş denetim soruları (etiketlerine göre) ──────────────────
QUESTION_RULES = {
    'Tesis izinleri': ['yok_tablo'],
    'Genel hijyen': ['yok_tablo'],
    'Kontrole erişim': ['yok_tablo'],
    'Yetiştiricilik izni / kapasite': ['yetistiricilik_izinsiz', 'yetistiricilik_yon'],
    'Kafes işaretlemesi': ['yok_tablo'],
    'Hastalık / karantina': ['yok_tablo'],
    'Sağlık belgesi': ['yok_tablo'],
    'Damızlık belgesi': ['yok_tablo'],
    'Koruyucu / tedavi edici maddeler': ['yok_tablo'],
    'İşleme ve ürün güvenliği': ['yok_tablo'],
    'Muhafaza / nakil şartları': ['yok_tablo'],
    'Atık ve çevre koruma': ['zararli'],
    'Atık yönetimi': ['aritma'],
    'Kişi / faaliyet ruhsatı': ['ruhsat_kisi', 'ruhsat_goster'],
    'Gemi ruhsatı / izin': ['ruhsat_gemi', 'ruhsat_goster'],
    'Ruhsat kodu / plaka': ['plaka'],
    'Personel ruhsatı': ['ruhsat_kisi'],
    '22 m+ zorunlu donanım': ['yok_tablo'],
    '12 m altı özel donanım': ['k_genel'],
    'BAGİS': ['bagis_takma', 'bagis_ariza'],
    'E-seyir': ['seyir'],
    'Av aracı markalama': ['markasiz'],
    'Birincil av aracı': ['ikinci_arac'],
    'İçsu sahası / ruhsat': ['ruhsat_kisi', 'ruhsat_gemi', 'k_genel'],
    'Yasaklanan içsular': ['k_genel'],
    'İçsu zaman yasağı': ['k_genel'],
    'İçsu av aracı şartları': ['k_genel'],
    'Dalyan açıklıkları': ['k_genel'],
    'Dalyan / lagün özel şartları': ['k_genel'],
    'Dalyan / lagün şartları': ['k_genel'],
    'Yer / saha / mesafe / derinlik': ['k_genel', 'liman', 'yetistiricilik_mesafe', 'mansap'],
    'Yasak av aracı bulundurma': ['yasak_donem_arac'],
    'MEB / diğer ülke suları izni': ['uluslararasi'],
    'Yabancıların avcılık yasağı': ['yabanci'],
    'Gırgır derinlik şartları': ['derinlik', 'girgir_derin'],
    'Ağ Ölçüm Belgesi': ['girgir_olcum'],
    'Trol teknik/saha şartları': ['dip_trol', 'ortasu'],
    'Işıkla avcılık şartları': ['isik', 'k_genel'],
    'Algarna şartları': ['k_genel', 'salyangoz_zaman_yer', 'salyangoz_saat', 'algarna_birden'],
    'Parakete şartları': ['k_genel', 'kalkan_parakete'],
    'İzleme / kayıt cihazı': ['yok_tablo'],
    'İçsu amatör av aracı': ['amator'],
    'İçsu yer / zaman yasağı': ['amator'],
    'Amatör av aracı': ['amator'],
    'Amatör yer yasağı': ['amator'],
    'İçsu ürün boy / ağırlık': ['yasak_boy'],
    'İçsu tür özel şartları': ['k_genel'],
    'Ürün boy / ağırlık': ['yasak_boy'],
    'Kota / tolerans / özel izin': ['izin', 'k_genel'],
    'İçsu amatör asgari boy': ['amator'],
    'İçsu amatör miktar': ['amator'],
    'Amatör asgari boy': ['amator'],
    'Amatör alıkonulabilir miktar': ['amator'],
    'İçsu canlı nakli / stoklama': ['k_genel'],
    'Yasak ürünün nakli / satışı': ['yasak_urun'],
    'Nakil / Menşe belgesi': ['nakil', 'kota_nakil'],
    'Karaya çıkış noktası': ['karaya_cikis'],
    'Amatör ürün satışı / canlı nakli': ['amator'],
    'Delillendirme': ['yok_usul'],
}

# ── Otomatik mevzuat uyarıları (screens.build_context_flags key=) ────────
FLAG_RULES = {
    'inland_trawl_purse': ['trol_marmara', 'k_genel'],
    'light_zone': ['isik'],
    'marmara_trawl': ['trol_marmara'],
    'algarna_zone': ['k_genel'],
    'purse_under12': ['girgir_12m'],
    'purse_closed': ['girgir_zaman'],
    'amateur_inland_gear': ['amator'],
    'amateur_longline': ['amator'],
    'amateur_tirivri': ['amator'],
    'species_time_commercial': ['k_genel'],
    'species_time_amateur': ['amator'],
}

# Dayanağı kartın madde alanlarıyla birebir uyuşmayan ama doğru olan eşleştirmeler.
ACCEPTED_BASIS = {
    ('reg', 4, 'ruhsat_kisi'): 'Personel ruhsatı Yönetmelik 4’te düzenlenir; kişi ruhsatsızlık kartları Kanun 3 / Yön. 4 dayanaklıdır.',
    ('bagis', 5, 'bagis_takma'): 'BAGİS Tebliği 5 cihaz takma zorunluluğunu, 7/1 yükümlülüğü düzenler; kart 7/1’e atıf yapar.',
    ('reg', 13, 'k_genel'): 'Yönetmelik 13 gemi/av aracı sınırlamaları Kanun 23 kapsamındadır; 36/k genel tutarı uygulanır.',
    ('reg', 18, 'uluslararasi'): 'Yönetmelik 18 uluslararası sular hükmü; kart Yön. 18 / Tebliğ 50/4 dayanaklıdır.',
    ('law', 3, 'ruhsat_kisi'): 'Kanun 3 ruhsat zorunluluğu; kişi kartları Kanun 3 dayanaklıdır.',
    ('61', 50, 'dip_trol'): 'Madde Tebliğ 9-10’daki dip trolü yasak saha ve mesafelerini denetler; kart Tebliğ 10 dayanaklıdır.',
    ('law', 36, 'trol_marmara'): 'Kanun 36/l tekrar hükmü; kart aynı bentteki Kanun 24/1-a trol yasağıdır.',
    ('law', 36, 'karaya_cikis'): 'Kanun 36/r karaya çıkış yaptırımı; kart Kanun Ek-5 / Tebliğ 49/26 dayanaklıdır.',
    ('61', 11, 'karaya_cikis'): 'Çaça için belirlenen karaya çıkış yeri; yaptırım genel karaya çıkış kalemidir (Ek-5, Tebliğ 49/26).',
    ('61', 27, 'karaya_cikis'): 'Karides için belirlenen karaya çıkış yeri; yaptırım genel karaya çıkış kalemidir (Ek-5, Tebliğ 49/26).',
    ('61', 28, 'karaya_cikis'): 'Beyaz kum midyesi karaya çıkış noktası; yaptırım genel karaya çıkış kalemidir (Ek-5, Tebliğ 49/26).',
    ('61', 11, 'yasak_donem_arac'): 'Ortasu trolünün kapalı yer/zamandan geçişi; ihlal yasak dönemde av aracı bulundurma kalemidir (Tebliğ 50/10).',
    ('reg', 18, 'yasak_donem_arac'): 'Uluslararası sulara geçişte yasak bölgede av aracı bulundurma; kart Tebliğ 50/10 dayanaklıdır.',
    ('61', 49, 'hedef_disi'): 'Hedef dışı av bildirimi Tebliğ 18’de düzenlenir; madde genel hükümler (49) altında sorulur, kart 18-b dayanaklıdır.',
    ('61', 49, 'nakil'): 'Nakil/Menşe belgesi Tebliğ 46’da düzenlenir; madde genel hükümler (49) altında sorulur.',
    ('61', 49, 'seyir'): 'E-seyir defteri güncel 6/1 Tebliğ 49/9’dadır; ceza kartı önceki tebliğ numarasını (48/10) taşır, kalem aynıdır (Kanun 28, 36/n).',
    ('61', 50, 'kum_midyesi'): 'Beyaz kum midyesi açık saha segmentleri Tebliğ 50’de ilan edilir; yer/zaman ihlali kartı Tebliğ 28 dayanaklıdır.',
    ('61', 50, 'nakil'): 'Yardımcı gemide taşınan ürünün nakil belgesi; kart Tebliğ 46 dayanaklıdır.',
    ('61', 29, 'nakil'): 'Deniz patlıcanı / denizkestanesi için Tebliğ 29’daki Nakil/Menşe zorunluluğu; kart Tebliğ 46 dayanaklıdır.',
    ('61', 48, 'amator'): 'Turizm amaçlı olta balıkçılığında (6/1 Md.48) katılımcıların amatör kural aykırılığı 36/k amatör kalemindedir; ticari/amatör ayrımı 6/2 Tebliğ Md.19’a göre yapılır.',
    ('reg', 12, 'aritma'):'Atıkların zararsız hale getirilmesi (Yön. 12); tesis arıtma kalemi yetiştiricilik mevzuatındaki arıtma hükmüne dayanır.',
    ('61', 38, 'yasak_boy'): 'İçsu asgari boy/ağırlık Tebliğ 38’dedir; yasak boy kalemi deniz için Tebliğ 17’ye atıf yapar, kalem aynıdır.',
}


def load_json(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def numbers(value):
    return {int(n) for n in re.findall(r'\d+', str(value or ''))}


def parse_guide_rules():
    rules = {}
    for line in GUIDE_RULES.strip().splitlines():
        ident, profiles = line.split('=')
        rules[ident.strip()] = [p.strip() for p in profiles.split(',') if p.strip()]
    return rules


def screen_question_tags(source):
    body = source[source.index('def build_quick_questions'):source.index('def audit_quick_start')]
    return set(re.findall(r"_q\('(?:[^'\\]|\\.)*', '(?:yes|no)', \((?:[^()]|\([^()]*\))*\), '([^']+)'", body))


def screen_flag_keys(source):
    body = source[source.index('def build_context_flags'):source.index('def build_quick_questions')]
    return set(re.findall(r"key='([a-z0-9_]+)'", body))


def basis_status(ref, profile_name, cards):
    """uyumlu / genel_kalem / uyumsuz — dayanağın kart madde alanlarıyla sağlaması."""
    profile = PROFILES[profile_name]
    source, article = ref[0], int(ref[1])
    if profile['kind'] == 'none':
        return 'yaptırımsız'
    if profile['kind'] == 'k_general':
        return 'uyumlu' if source in {'61', '62'} or (source == 'law' and article in {23, 24}) else 'uyumsuz'
    field = {'61': 'teblig', '62': 'teblig', 'bagis': 'teblig', 'reg': 'regulation', 'law': 'law'}[source]
    status = 'genel_kalem'
    for card_id in profile['cards']:
        card = cards[card_id]
        if source == '62' and profile_name == 'amator':
            return 'uyumlu'
        value = card.get(field)
        if value in (None, '-', '', '----'):
            continue
        if article in numbers(value):
            return 'uyumlu'
        status = 'uyumsuz'
    return status


def build(write_report=True):
    cards = {card['id']: card for card in load_json('penalty_cards.json')}
    guides = load_json('vessel_guides.json')
    source = SCREENS.read_text(encoding='utf-8')
    errors, report_rows = [], []

    # 2–4: profil, bent, kademe ve 36/k tutar sağlaması
    k_amounts = cards[54]['amounts']
    for name, profile in PROFILES.items():
        for card_id in profile.get('cards', []):
            card = cards.get(card_id)
            if not card:
                errors.append(f'{name}: kart {card_id} yok')
                continue
            if profile['kind'] != 'none' and (card.get('art36') or '-') != profile['bent']:
                errors.append(f'{name}: kart {card_id} bendi {card.get("art36")} ≠ {profile["bent"]}')
    for card_id, (low, high) in TIERS.items():
        text = cards[card_id].get('option') or ''
        found = numbers(text)
        expected = {n for n in (low, high) if n}
        if not expected <= found:
            errors.append(f'kart {card_id} kademe {low}-{high} seçenek metninde yok: {text}')
    for card in cards.values():
        amounts = card.get('amounts') or {}
        if card.get('art36') == 'k' and all(t in amounts for t in K_TIERS) and card['id'] not in {71, 45}:  # ışık 50.000 TL; 45 amatör gemi
            if any(amounts[t] != k_amounts[t] for t in K_TIERS):
                errors.append(f'kart {card["id"]} 36/k gemi kademeleri genel tutardan farklı')

    def check(kind, key, ref, text, profiles):
        for name in profiles:
            if name not in PROFILES:
                errors.append(f'{kind} {key}: bilinmeyen profil {name}')
                return
        statuses = {name: basis_status(ref, name, cards) for name in profiles}
        card_statuses = [s for s in statuses.values() if s != 'yaptırımsız']
        accepted = [ACCEPTED_BASIS[(ref[0], int(ref[1]), name)] for name in profiles
                    if (ref[0], int(ref[1]), name) in ACCEPTED_BASIS]
        if card_statuses and all(s == 'uyumsuz' for s in card_statuses) and not accepted:
            errors.append(f'{kind} {key}: dayanak {ref[0]}.{ref[1]} hiçbir eşlenen kartla uyuşmuyor {statuses}')
        report_rows.append((kind, key, f'{ref[0]}.{ref[1]}', text, statuses, accepted))

    # 1: föy maddeleri
    rules = parse_guide_rules()
    used, guide_links = set(), {}
    groups = {}
    for guide in guides:
        for row in guide['rows']:
            ident = f'{guide["key"].split("_")[0]}:{row["no"]}'
            groups.setdefault((row['text'], tuple(row['ref'])), []).append((guide['key'], row['no'], ident))
    for (text, ref), members in groups.items():
        matched = [m[2] for m in members if m[2] in rules]
        if len(matched) != 1:
            errors.append(f'föy maddesi eşleştirmesi {"yok" if not matched else "birden fazla: " + str(matched)}: '
                          f'{members[0][2]} {text[:60]}')
            continue
        used.add(matched[0])
        profiles = rules[matched[0]]
        for guide_key, no, _ident in members:
            guide_links[f'{guide_key}:{no}'] = profiles
        check('föy', ','.join(m[2] for m in members), ref, text, profiles)
    for stray in sorted(set(rules) - used):
        errors.append(f'fazla föy kuralı: {stray}')

    # denetim soruları ve uyarılar
    tags = screen_question_tags(source)
    for tag in sorted(tags - set(QUESTION_RULES)):
        errors.append(f'eşleştirmesi olmayan denetim sorusu: {tag}')
    for tag in sorted(set(QUESTION_RULES) - tags):
        errors.append(f'fazla soru kuralı: {tag}')
    question_refs = {}
    for match in re.finditer(r"_q\('((?:[^'\\]|\\.)*)', '(?:yes|no)', \('(\w+)', (\d+)[^)]*\), '([^']+)'", source):
        text, ref_source, ref_article, tag = match.groups()
        if tag in QUESTION_RULES and tag not in question_refs:
            question_refs[tag] = (ref_source, int(ref_article))
            check('soru', tag, (ref_source, int(ref_article)), text, QUESTION_RULES[tag])
    keys = screen_flag_keys(source)
    for key in sorted(keys ^ set(FLAG_RULES)):
        errors.append(f'uyarı anahtarı eşleşmiyor: {key}')
    for key, profiles in FLAG_RULES.items():
        for name in profiles:
            if name not in PROFILES:
                errors.append(f'uyarı {key}: bilinmeyen profil {name}')

    profiles_out = {}
    for name, profile in PROFILES.items():
        out = dict(profile)
        if profile['kind'] == 'cards' and not out.get('label'):
            out['label'] = cards[profile['cards'][0]]['violation']
        profiles_out[name] = out
    output = {
        'profiles': profiles_out,
        'guides': guide_links,
        'questions': {tag: QUESTION_RULES[tag] for tag in sorted(QUESTION_RULES)},
        'flags': FLAG_RULES,
        'tiers': {str(k): list(v) for k, v in TIERS.items()},
        'k_general': {'person_card': 46, 'vessel_amounts': {t: k_amounts[t] for t in K_TIERS},
                      'purse_seine_amount': k_amounts.get('Gırgır')},
    }
    if write_report and REPORT.parent.is_dir():
        write_markdown_report(report_rows, errors)
    return output, errors


def write_markdown_report(rows, errors):
    lines = ['# Yaptırım eşleştirme ve sağlama raporu', '',
             'Üreten: tools/build_penalty_links.py. Durumlar: uyumlu (dayanak kart madde alanında), '
             'genel_kalem (kart ilgili alanı belirtmiyor), uyumsuz (farklı madde; satırda başka uyumlu kart '
             'veya gerekçe var), yaptırımsız.', '']
    counts = {}
    for _kind, _key, _ref, _text, statuses, _acc in rows:
        for status in statuses.values():
            counts[status] = counts.get(status, 0) + 1
    lines.append('Özet: ' + ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + f', hata: {len(errors)}')
    lines += ['', '| Tür | Kimlik | Dayanak | Madde | Profil → sağlama | Gerekçe |', '|---|---|---|---|---|---|']
    for kind, key, ref, text, statuses, accepted in rows:
        cell = '; '.join(f'{name} → {status}' for name, status in statuses.items())
        lines.append(f'| {kind} | {key} | {ref} | {text.replace("|", "/")[:120]} | {cell} | {" ".join(accepted)} |')
    if errors:
        lines += ['', '## Hatalar', ''] + [f'- {e}' for e in errors]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output, errors = build()
    if errors:
        print('SAĞLAMA HATALARI:')
        for error in errors:
            print(' -', error)
        return 1
    rendered = dump(output)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != rendered:
            print('penalty_links.json güncel değil')
            return 1
        print('penalty_links.json doğrulandı')
        return 0
    OUTPUT.write_bytes(rendered)
    print(f'penalty_links.json üretildi: {len(output["guides"])} föy maddesi, '
          f'{len(output["questions"])} soru, {len(output["flags"])} uyarı, {len(output["profiles"])} profil')
    return 0


if __name__ == '__main__':
    sys.exit(main())
