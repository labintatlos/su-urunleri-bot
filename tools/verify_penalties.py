"""İdari ceza kartlarının Kanun, Yönetmelik ve Tebliğlere göre sağlaması.

    python tools/verify_penalties.py          # sağlar, yerel rapor yazar
    python tools/verify_penalties.py --check  # yalnızca sağlar

Katmanlar:
1. Kanun 36 hükümleri (LAW36) Kanun metninde birebir aranır.
2. Tablo yeniden değerleme tutarları (BASE_CURRENT) kendi içinde tutarlı mı.
3. Her kart bir hükme bağlanır; bent, tutar/aralık, boy çarpanı (×2/×3),
   gırgır 3 katı, tekrar, ruhsat ve el koyma hükümle karşılaştırılır.
4. Yönetmelik/Tebliğ atıflarının madde ve fıkrası güncel metinde var mı ve
   konusu ihlalle uyuşuyor mu.
5. Kartların 08 tablosundaki ham Excel satırıyla tutarı.
6. Kanun 36'daki her hükmün en az bir kartı var mı.

08 tablosundaki hatalar sessizce değiştirilmez: CORRECTIONS ile düzeltilir,
eski değer kartta `excel_original` alanında ve gerekçesiyle saklanır.
Tabloda bulunmayan hükümler NEW_CARDS ile Kanundan eklenir (`origin: kanun`).
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'su_urunleri_bot' / 'data'
LAW_DOC = DATA / 'markdown' / '1380 SU ÜRÜNLERİ KANUNU MARKDOWN.md'
REPORT = ROOT / 'yerel' / 'CEZA_SAGLAMA_RAPORU.md'
sys.path.insert(0, str(Path(__file__).resolve().parent))

TOL = 10  # yeniden değerlemedeki kuruş/yuvarlama farkı (TL)

# Kanun taban tutarı → 08 tablosundaki güncel karşılığı.
BASE_CURRENT = {
    250: 2356, 500: 4730, 700: 6627, 750: 7105, 850: 8048, 1000: 9473, 1700: 16106,
    2000: 18954, 2500: 23692, 3000: 28433, 4000: 37914, 5000: 47397, 7000: 66357,
    10000: 94811, 15000: 142217, 20000: 189630, 25000: 237034, 30000: 284449,
    35000: 331855, 40000: 379267, 50000: 474079, 100000: 948169, 200000: 1896350,
    250000: 2370440,
}

DOUBLE = 'Kabahatin tespitinden itibaren 2 yıl içinde tekrarında idari para cezası 2 katı uygulanır (Kanun 36 son fıkralar).'
NO_GENERAL = 'Kanun 36 son fıkralar gereği bu bentte genel tekrar artırımı (2 kat) uygulanmaz.'
LICENSE_K = ('Ruhsat tezkeresi 1. tespitte 1 ay, 2. tespitte 3 ay geri alınır; tekrarında iptal edilir ve gemi '
             'hariç istihsal vasıtalarına el konur (Kanun 36/k–l, Yönetmelik 41).')

# ── Kanun 36 hükümleri ───────────────────────────────────────────────────
# fixed: taban tutar; range: (alt, üst). vessel: boy çarpanı uygulanır.
# repeat: double | own | criminal | none. license: ruhsat geri alma hükmü var.
# seizure: Kanunda ürüne el koyma öngörülür.
LAW36 = {
    'a1_kisi': dict(bent='a', label='Ruhsatsız ticari avcılık — kişi (3/1)', range=(1000, 5000),
                    quote='ruhsat tezkeresi almadan ticari amaçlı su ürünleri avcılığı yapan kişilere bin Türk lirasından beş bin Türk lirasına kadar',
                    repeat='double', seizure=True,
                    note='Ruhsatsız elde edilen ürüne el konur. Gırgır, orta su/dip trolü, algarna veya dalarak avcılıkta istihsal vasıtalarına; diğer araçlarda ilk tespitte gemi hariç, tekrarında gemi dahil el konur.'),
    'a1_gemi': dict(bent='a', label='Ruhsatsız avcılık — gemi sahibi/donatan (3/1)', range=(5000, 50000), vessel=True,
                    quote='gemiler ve diğer su vasıtaları için sahip veya donatanlarına beş bin Türk lirasından elli bin Türk lirasına kadar',
                    repeat='double', seizure=True),
    'a2_amator_kisi': dict(bent='a', label='Amatör avcılık usul ve esaslarına aykırılık — kişi (3/2)', range=(250, 500),
                           quote='amatör avcılıkla ilgili usul ve esaslara aykırı hareket eden kişilere iki yüz elli Türk lirasından beş yüz Türk lirasına',
                           repeat='double'),
    'a2_amator_gemi': dict(bent='a', label='Amatör avcılık usul ve esaslarına aykırılık — gemi (3/2)', range=(500, 5000), vessel=True,
                           quote='amatör avcılıkta kullanılan gemiler için sahip veya donatanlarına beş yüz Türk lirasından beş bin Türk lirasına kadar',
                           repeat='double'),
    'a2_ticari_kisi': dict(bent='a', label='Ticari avcılık usul ve esaslarına (izin) aykırılık — kişi (3/2)', range=(5000, 50000),
                           quote='ticari avcılıkla ilgili usul ve esaslara aykırı hareket edenlere beş bin Türk lirasından elli bin Türk lirasına kadar',
                           repeat='double', seizure=True),
    'a2_ticari_gemi': dict(bent='a', label='Ticari avcılık usul ve esaslarına (izin) aykırılık — gemi (3/2)', range=(5000, 50000), vessel=True,
                           quote='ticari avcılıkla ilgili usul ve esaslara aykırı hareket edenlere beş bin Türk lirasından elli bin Türk lirasına kadar',
                           repeat='double'),
    'a3': dict(bent='a', label='İzin ve ruhsat tezkeresini talepte göstermeme (3/3)', fixed=1000, vessel=True,
               quote='kişilere ve gemiler için sahip veya donatanlarına bin Türk lirası idari para cezası verilir',
               repeat='double'),
    'b': dict(bent='b', label='İstihsal hakkı kiralama kurallarına aykırılık (Md.4)', range=(2500, 25000),
              quote='gerçek veya tüzel kişilere iki bin beş yüz Türk lirasından yirmi beş bin Türk lirasına kadar idarî para cezası verilir. Aynı kabahatin tekrarında',
              repeat='own', repeat_text='Tekrarında idari para cezası 2 katı uygulanır ve kira sözleşmesi iptal edilir (Kanun 36/b).',
              note='Kooperatif/birlik başkan ve yönetim kurulu üyelerine ayrı ayrı uygulanır.'),
    'c_icsu': dict(bent='c', label='İstihsal yerlerinde izinsiz değişiklik — içsu (Md.7)', fixed=10000,
                   quote='fiilin içsularda gerçekleşmesi halinde on bin Türk lirası', repeat='double', seizure=True,
                   note='Çıkarılan kum, çakıl, taş vb. maddelere el konulur; mümkünse istihsal yeri masrafı faile ait olmak üzere eski haline döndürülür.'),
    'c_deniz': dict(bent='c', label='İstihsal yerlerinde izinsiz değişiklik — deniz (Md.7)', fixed=20000,
                    quote='denizlerde vuku bulması halinde ise yirmi bin Türk lirası', repeat='double', seizure=True,
                    note='Çıkarılan kum, çakıl, taş vb. maddelere el konulur; mümkünse istihsal yeri masrafı faile ait olmak üzere eski haline döndürülür.'),
    'd': dict(bent='d', label='Sulama/enerji amaçlı su kullanımında tedbir almama (Md.9)', range=(5000, 50000),
              quote='9 uncu madde kapsamında Tarım ve Orman Bakanlığınca belirlenen tedbirleri almayanlara beş bin Türk lirasından elli bin Türk lirasına kadar',
              repeat='double'),
    'e1': dict(bent='e', label='Kanun 13/1’e aykırı (izinsiz) yetiştiricilik tesisi', range=(10000, 100000),
               quote='tesis sahiplerine on bin Türk lirasından yüz bin Türk lirasına kadar',
               repeat='own', repeat_text='Tesise 90 gün süre verilir; aykırılık sürerse ilk cezanın 2 katı uygulanır ve 30 gün daha süre verilir; yine sürerse 3 katı uygulanır ve tesis mülki amirce kapatılır (Kanun 36/e). Genel tekrar artırımı uygulanmaz.'),
    'e2': dict(bent='e', label='Kanun 13’e göre çıkarılan yönetmelik hükümlerine aykırılık', range=(5000, 50000),
               quote='13 üncü maddeye göre çıkarılan yönetmelik hükümlerine aykırı hareket edenlere beş bin Türk lirasından elli bin Türk lirasına kadar',
               repeat='none'),
    'f': dict(bent='f', label='Kanun 17’ye dayanan yönetmelik (balıkçı barınakları) hükümlerine aykırılık', range=(2500, 25000),
              quote='17 nci maddeye dayanılarak çıkarılan yönetmelik hükümlerine aykırı hareket eden',
              repeat='own', repeat_text='Tekrarında idari para cezası 2 katı uygulanır ve kira sözleşmesi iptal edilir (Kanun 36/f).'),
    'g': dict(bent='g', label='Patlayıcı, zehirli madde, elektrik vb. ile avcılık (Md.19)', fixed=10000,
              quote='19 uncu maddeye aykırı hareket edenlere on bin Türk lirası', repeat='double', seizure=True,
              note='Ürün ile aykırılığa neden olan eşya, alet, edevat ve teçhizata el konulur.'),
    'h_kisi': dict(bent='h', label='Sulara zararlı madde dökülmesi — kişi (Md.20)', fixed=5000,
                   quote='20 nci maddeye göre çıkarılan yönetmelikteki yasak, sınırlama ve yükümlülüklere aykırı hareket edenlere beş bin Türk lirası',
                   repeat='double'),
    'h_tesis': dict(bent='h', label='Sulara zararlı madde dökülmesi — fabrika/imalathane/atölye (Md.20)', range=(5000, 50000),
                    quote='imalathane ve atölye gibi tesis sahipleri ve bunların sorumlu kıldığı kişiler tarafından işlendiği takdirde, beş bin Türk lirasından elli bin Türk lirasına kadar',
                    repeat='double',
                    note='Aykırılık belirlenen sürede giderilmezse faaliyet durdurulur ve tesis masrafı sahibine ait olmak üzere zararsız hale getirilir.'),
    'i': dict(bent='i', label='Yabancıların karasuları/içsularda avcılığı (Md.21/1)', fixed=20000,
              quote='21 inci maddenin birinci fıkrasına aykırı hareket edenlere yirmi bin Türk lirası', repeat='double', seizure=True,
              note='Ürün ve istihsal vasıtalarına el konulur.'),
    'j1': dict(bent='j', label='Akarsularda izinsiz engel (ağ, bent, çit) (Md.22/1)', fixed=1700,
               quote='22 nci maddenin birinci fıkrasına aykırı hareket edenlere bin yedi yüz Türk lirası', repeat='double',
               note='Faaliyet durdurulur; engeller masrafı faile ait olmak üzere kaldırılır.'),
    'j2_gecit': dict(bent='j', label='Balık geçidi yapmama / istenen tedbiri almama (Md.22/2)', range=(100000, 250000),
                     quote='yüz bin Türk lirasından iki yüz elli bin Türk lirasına kadar idarî para cezası verilir',
                     repeat='own', repeat_text='Aykırılığın giderilmesi için 18 ayı geçmeyen süre verilir; müteakip kontrollerde giderilmemişse bir önceki cezanın 2 katı uygulanır. Genel tekrar artırımı uygulanmaz (Kanun 36/j ikinci paragraf).'),
    'j2_calistirma': dict(bent='j', label='Balık geçidini çalıştırmama, taşıma yapmama, tedbirleri yerine getirmeme (Md.22/2)', fixed=50000,
                          quote='Bakanlığınca öngörülen tedbirleri yerine getirmeyenlere, elli bin Türk lirası',
                          repeat='own', repeat_text='Genel tekrar artırımı uygulanmaz (Kanun 36/j ikinci paragraf).'),
    'k1_kisi': dict(bent='k', label='Ticari avcılık yönetmelik hükümlerine aykırılık — kişi (Md.23)', fixed=1700,
                    quote='yönetmelikle getirilen hükümlere aykırı hareket edenlere bin yedi yüz Türk lirası',
                    repeat='double', license=True, seizure=True),
    'k1_gemi': dict(bent='k', label='Ticari avcılık yönetmelik hükümlerine aykırılık — gemi sahibi/donatan (Md.23)', fixed=2500,
                    vessel=True, purse=True,
                    quote='kullanılan gemiler için sahip veya donatanlarına iki bin beş yüz Türk lirası',
                    repeat='double', license=True, seizure=True,
                    note='Gırgır gemisiyle işlenirse gemi sahibine 3 katı. Bölge, zaman veya av aracı vasıflarına aykırılıkta gemi hariç istihsal vasıtalarına da el konur.'),
    'k2_isik': dict(bent='k', label='Işıkla avlanma / ışık donanımı bulundurma (İçsu, Karadeniz, Marmara) (Md.23)', fixed=50000, vessel=True,
                    quote='ışık donanımı bulunduran gemiler için sahip veya donatanlarına elli bin Türk lirası',
                    repeat='double', license=True, seizure=True,
                    note='Ürüne ve gemi hariç avcılık amacıyla ışık sağlayan her türlü su vasıtası ve edevata el konur.'),
    'k3_amator_kisi': dict(bent='k', label='Amatör avcılık yönetmelik hükümlerine aykırılık — kişi (Md.23)', fixed=500,
                           quote='amatör amaçla yapılacak avcılık faaliyetlerine yönelik olarak yönetmelikle getirilen hükümlere aykırı hareket edenlere beş yüz Türk lirası',
                           repeat='double', seizure=True,
                           note='Ürüne ve gemi hariç kullanımı yasak vasıtalara el konur; tekrarında gemi hariç tüm istihsal vasıtalarına. Ticari/amatör ayrımı 6/2 Tebliğ Md.19’a göre yapılır.'),
    'k3_amator_gemi': dict(bent='k', label='Amatör avcılık yönetmelik hükümlerine aykırılık — gemi (Md.23)', fixed=750, vessel=True,
                           quote='kullanılan gemiler için sahip veya donatanlarına yedi yüz elli Türk lirası',
                           repeat='double', seizure=True),
    'l1_kisi': dict(bent='l', label='İçsu, Marmara ve boğazlarda trol — kişi (Md.24/a)', fixed=10000,
                    quote='trol ile su ürünleri istihsalinde bulunanlara on bin Türk lirası', repeat='double', seizure=True),
    'l1_gemi': dict(bent='l', label='İçsu, Marmara ve boğazlarda trol — gemi sahibi/donatan (Md.24/a)', fixed=20000, vessel=True,
                    quote='kullanılan gemiler için sahip veya donatanlarına yirmi bin Türk lirası', seizure=True,
                    repeat='criminal', repeat_text='Fiilin 2 yıl içinde tekrarında gemi sahibi/donatana 1–3 yıl hapis ve 5.000–10.000 gün adli para cezası verilir; ürün ve istihsal vasıtaları müsadere edilir (Kanun 36/l). Adli makamlara bildirilir.',
                    note='Ürün ve istihsal vasıtalarına (gemi dahil) el konur.'),
    'l2_kisi': dict(bent='l', label='Dip trolü yasak, sınırlama ve yükümlülüklerine aykırılık — kişi (Md.24/b)', fixed=7000,
                    quote='dip trolüne ilişkin yasak, sınırlama ve yükümlülüklere aykırı hareket edenlere ve kullanılan gemiler için sahip veya donatanlarına yedi bin Türk lirası',
                    repeat='double', license=True, seizure=True,
                    note='Yasak yer/zamanda dip trol ağı denizde veya bordada bulunması, küçük göz açıklıklı dip trolü bulundurma, orta su/kombine trolü dip trolü olarak kullanma da bu cezaya tabidir.'),
    'l2_gemi': dict(bent='l', label='Dip trolü yasak, sınırlama ve yükümlülüklerine aykırılık — gemi (Md.24/b)', fixed=7000, vessel=True,
                    quote='dip trolüne ilişkin yasak, sınırlama ve yükümlülüklere aykırı hareket edenlere ve kullanılan gemiler için sahip veya donatanlarına yedi bin Türk lirası',
                    repeat='double', license=True, seizure=True),
    'm1_nakil': dict(bent='m', label='Yasak su ürününü nakletme veya satma (Md.23–25)', fixed=5000,
                     quote='nakledenlere, satanlara beş bin Türk lirası', repeat='double', seizure=True),
    'm1_imalat': dict(bent='m', label='Yasak su ürününü imalatta kullanma, işleme, muhafaza, ihraç (Md.23–25)', fixed=10000,
                      quote='imalatta kullananlara, işleyenlere, muhafaza edenlere ve ihraç edenlere on bin Türk lirası',
                      repeat='double', seizure=True, note='Ürüne ve yapılan imalata el konulur.'),
    'm3': dict(bent='m', label='Su ürünlerini izinsiz yurt dışına çıkarma / canlı yurda sokma (Md.25/3)', range=(5000, 100000),
               quote='25 inci maddenin üçüncü fıkrasına aykırı hareket edenlere beş bin Türk lirasından yüz bin Türk lirasına kadar',
               seizure=True, repeat='criminal',
               repeat_text='Fiilin 2 yıl içinde tekrarında 1–3 yıl hapis ve 5.000–10.000 gün adli para cezası verilir; ürün, istihsal ve nakil vasıtaları müsadere edilir (Kanun 36/m). Adli makamlara bildirilir.',
               note='Ürüne, istihsal ve nakil vasıtalarına el konulur.'),
    'n': dict(bent='n', label='Bilgi ve belgeleri zamanında ve doğru vermeme (Md.28)', fixed=700, vessel=True,
              quote='zamanında ve doğru olarak vermeyenlere, yedi yüz Türk lirası', repeat='double'),
    'o': dict(bent='o', label='İzinsiz yasak vasıta/usulle ilmi-teknik çalışma (Md.29)', fixed=850,
              quote='29 uncu madde hükümlerine aykırı hareket edenlere, sekiz yüz elli Türk lirası', repeat='double',
              note='Kabahat konusu yasak vasıtalara el konulur.'),
    'p_gemi': dict(bent='p', label='İzleme sistemi (BAGİS) yükümlülüğü — gemi (Ek Md.4)', range=(1000, 5000), vessel=True,
                   quote='yükümlülüklere uymayan gemiler için sahip veya donatanlarına bin Türk lirasından beş bin Türk lirasına kadar',
                   repeat='double', note='Aykırılık giderilinceye kadar faaliyete izin verilmez (Kanun Ek Md.4).'),
    'p_tesis': dict(bent='p', label='İzleme sistemi yükümlülüğü — yetiştiricilik tesisi (Ek Md.4)', range=(5000, 25000),
                    quote='yetiştiricilik tesisleri sahiplerine ise beş bin Türk lirasından yirmi beş bin Türk lirasına kadar',
                    repeat='double', note='Aykırılık giderilinceye kadar faaliyete izin verilmez (Kanun Ek Md.4).'),
    'r_gemi': dict(bent='r', label='Karaya çıkış noktası dışında boşaltma — gemi (Ek Md.5)', range=(1000, 5000), vessel=True,
                   quote='boşaltmayan gemiler için sahip veya donatanlarına bin Türk lirasından beş bin Türk lirasına kadar',
                   repeat='double'),
    'r_nakil': dict(bent='r', label='Nakil belgesi yükümlülüklerine aykırılık (Ek Md.5)', range=(1000, 5000),
                    quote='Ek 5 inci maddede yer alan yükümlülüklere aykırı hareket edenlere', repeat='double',
                    note='Kotaya tabi, izleme programındaki ve kiralık alanlardan elde edilen türlerde belgesiz ürün yasadışı kabul edilir ve 36/m uygulanır (6/1 Tebliğ 46/4).'),
    's_gercek': dict(bent='s', label='İzinsiz balıklandırma — gerçek kişi (Ek Md.6)', fixed=10000,
                     quote='gerçek kişilere on bin Türk lirası', repeat='double'),
    's_tuzel': dict(bent='s', label='İzinsiz balıklandırma — tüzel kişi (Ek Md.6)', fixed=20000,
                    quote='tüzel kişilere yirmi bin Türk lirası', repeat='double'),
    't_ruhsatli': dict(bent='t', label='Başka ülke suları/uluslararası sularda şartlara aykırı avcılık — ruhsatlı gemi (Ek Md.7)',
                       range=(10000, 30000), vessel=True,
                       quote='on bin Türk lirasından otuz bin Türk lirasına kadar', repeat='double'),
    't_ruhsatsiz': dict(bent='t', label='Başka ülke suları/uluslararası sularda avcılık — ruhsatsız gemi (Ek Md.7)',
                        range=(20000, 50000), vessel=True,
                        quote='yirmi bin Türk lirasından elli bin Türk lirasına kadar', repeat='double'),
    'askida': dict(bent='genel', label='Ruhsat tezkeresi geçici geri alınmış gemiyle avcılık (Kanun 36 son fıkralar)', none=True,
                   quote='Ruhsat tezkerelerine geçici süre ile el konulan balıkçı gemilerinin bu süre içerisinde avcılık yapmaları halinde',
                   repeat='none',
                   note='Gemiye avlanma araçları ve donanımıyla birlikte el konulur; kamuya geçirilen geminin tüm izin ve ruhsatları iptal edilmiş sayılır.'),
}

GENERAL_QUOTES = {
    'boy çarpanı': 'tam boyu oniki metre dahil yirmiiki metreye kadar olan gemiler için iki katı, yirmiiki metre ve daha uzun gemiler için üç katı',
    'tekrar tanımı': 'kabahatin tespit edildiği tarihten itibaren iki yıl içinde',
    'tekrar artırımı': '(b), (e) ve (f) bentleri ile (j) bendinin ikinci paragrafı hariç olmak üzere, idarî para cezaları iki katı',
    'gırgır 3 katı': 'bu gemiler için sahip veya donatanlarına ceza üç katı olarak uygulanır',
    'kamuya geçen gemi': 'tüm izin ve ruhsat tezkereleri de iptal edilmiş sayılır',
}

CARD_PROVISION = {
    **{i: 'a1_kisi' for i in (1, 2, 3, 4)}, **{i: 'a1_gemi' for i in range(5, 12)},
    12: 'a2_amator_kisi', 15: 'a2_amator_kisi', **{i: 'a2_amator_gemi' for i in (13, 14, 16, 17)},
    18: 'a2_ticari_kisi', **{i: 'a2_ticari_gemi' for i in (19, 20, 21, 22, 23, 24, 25, 26, 27)},
    28: 'a3', 154: 'a3', 29: 'c_icsu', 30: 'c_deniz', **{i: 'd' for i in (31, 32, 33, 34)},
    35: 'g', 36: 'h_kisi', 37: 'h_tesis', 38: 'h_tesis', 39: 'i', 40: 'j1', 41: 'j2_gecit', 42: 'j2_gecit',
    43: 'j2_calistirma', 44: 'k3_amator_kisi', 45: 'k3_amator_gemi', 46: 'k1_kisi', 76: 'k1_kisi',
    **{i: 'k1_gemi' for i in list(range(47, 71)) + [77, 116]}, 71: 'k2_isik',
    72: 'l1_kisi', 73: 'l1_gemi', 74: 'l2_kisi', 75: 'l2_gemi', 78: 'n', 115: 'n',
    79: 'm1_nakil', 80: 'm1_nakil', 114: 'm1_nakil', 81: 'm1_imalat', 155: 'm1_imalat',
    82: 'o', **{i: 'm3' for i in range(83, 96)}, **{i: 'p_gemi' for i in range(96, 101)}, 156: 'p_tesis',
    101: 'r_gemi', 102: 'r_gemi', 103: 'r_gemi', 112: 'r_nakil', 113: 'r_nakil',
    104: 't_ruhsatli', 105: 't_ruhsatli', 106: 't_ruhsatli', 107: 't_ruhsatsiz', 108: 't_ruhsatsiz', 109: 't_ruhsatsiz',
    110: 's_gercek', 111: 's_tuzel', **{i: 'b' for i in range(117, 124)}, **{i: 'f' for i in range(124, 130)},
    **{i: 'e1' for i in range(130, 138)}, **{i: 'e2' for i in range(138, 154)}, 157: 'askida',
}

K_TIER_AMOUNTS = {'<12 m': 23692, '12–<22 m': 47384, '≥22 m': 71076}

# (kart, alan, alt anahtar, 08 tablosundaki değer, düzeltilmiş değer, gerekçe)
CORRECTIONS = [
    (69, 'amounts', 'Gırgır', 56640, 71076,
     'Kanun 36/k: gırgır gemisi sahibine ceza 3 katı (23.692 × 3 = 71.076 TL); 08 belgesi de bu değeri olası veri girişi hatası olarak işaretler.'),
    (70, 'amounts', 'Gırgır', 56640, 71076,
     'Kanun 36/k: gırgır gemisi sahibine ceza 3 katı (23.692 × 3 = 71.076 TL); 08 belgesi de bu değeri olası veri girişi hatası olarak işaretler.'),
    (74, 'base_ipc', None, 23692, 66357,
     'Kanun 36/l ikinci paragraf dip trolü yasaklarına aykırı hareket edenlere ve gemi sahibine aynı 7.000 TL’yi öngörür (66.357 TL); tablo 36/k gemi tutarını yazmıştı.'),
    (96, 'amounts', '12–<22 m', 15098, 18946,
     'Kanun 36/p asgari 1.000 TL (9.473 TL) × 2 = 18.946 TL; tablo değeri kanuni asgarinin altındaydı.'),
    (96, 'amounts', '≥22 m', 22647, 28419,
     'Kanun 36/p asgari 1.000 TL (9.473 TL) × 3 = 28.419 TL; tablo değeri kanuni asgarinin altındaydı.'),
    (98, 'amounts', '12–<22 m', 94397, 94794, 'Boy çarpanı: 47.397 × 2 = 94.794 TL (tabloda yazım hatası).'),
    (99, 'amounts', '12–<22 m', 94397, 94794, 'Boy çarpanı: 47.397 × 2 = 94.794 TL (tabloda yazım hatası).'),
    (100, 'amounts', '≥22 m', 22647, 48318,
     'Boy çarpanı: 16.106 × 3 = 48.318 TL; tablo değeri 12–22 m tutarından da düşüktü (08 belgesi de işaretler).'),
    (109, 'base_ipc', None, 474079, 568890,
     'Kanun 36/t ruhsatsız gemi asgari 20.000 TL (189.630 TL) × 3 (≥22 m) = 568.890 TL; tablo değeri kanuni asgarinin altındaydı. Kart 107–108 ile aynı “asgari × boy çarpanı” yöntemi.'),
    (140, 'art36', None, '-', 'e', 'Kanun 13’e göre çıkarılan yönetmelik hükmüne aykırılık Kanun 36/e ikinci paragraftadır (5.000–50.000 TL).'),
    (141, 'art36', None, '-', 'e', 'Kanun 13’e göre çıkarılan yönetmelik hükmüne aykırılık Kanun 36/e ikinci paragraftadır (5.000–50.000 TL).'),
    (78, 'teblig', None, '48/10', '49/9',
     'E-seyir defteri yükümlülüğü güncel 6/1 Tebliğde Md.49/9’dadır; 48/10 eski tebliğin numarasıdır (güncel Md.48 turizm faaliyetidir).'),
    (44, 'teblig', None, None, '6/2 Tebliğ 19/3',
     'Amatör/ticari ayrımı ve 36/k amatör yaptırımı 6/2 Tebliğ Md.19’da düzenlenir.'),
    (45, 'teblig', None, None, '6/2 Tebliğ 19/3',
     'Amatör/ticari ayrımı ve 36/k amatör yaptırımı 6/2 Tebliğ Md.19’da düzenlenir.'),
    (45, 'amounts', None, {}, {'<12 m': 7105, '12–<22 m': 14210, '≥22 m': 21315},
     'Kanun 36 boy çarpanı amatör avcılıkta kullanılan geminin sahibine de uygulanır: 7.105 TL; ×2 = 14.210 TL; ×3 = 21.315 TL.'),
    (68, 'amounts', None, {}, dict(K_TIER_AMOUNTS),
     'Kanun 36/k gemi sahibi tutarı boy çarpanıyla: 23.692 / 47.384 / 71.076 TL (diğer 36/k kalemleriyle aynı).'),
]

ALIASES = {
    43: 'tasima gecit tedbir calistirmama',
    71: 'isik donanimi bulundurma jenerator lamba',
    74: 'bordaya dip trol agi kucuk goz acikligi kombine trol ortasu trolunu dip trolu olarak',
    75: 'bordaya dip trol agi kucuk goz acikligi kombine trol ortasu trolunu dip trolu olarak',
}

LAW_SOURCE = '1380 SU ÜRÜNLERİ KANUNU MARKDOWN.md'
NEW_CARDS = [
    {'id': 154, 'violation': 'İzin ve ruhsat belgesini göstermeme — gemi sahibi/donatan', 'option': 'Boy kademeli (Kanun 36 boy çarpanı)',
     'law': '3', 'regulation': '4', 'teblig': None, 'art36': 'a', 'base_ipc': 9473,
     'amounts': {'<12 m': 9473, '12–<22 m': 18946, '≥22 m': 28419}, 'product_seizure': 'Hayır', 'means_seizure': 'Hayır',
     'aliases': 'belge izin ruhsat tezkeresi gostermeme donatan gemi sahibi'},
    {'id': 155, 'violation': 'Yasak su ürününü işleme, muhafaza etme veya ihraç etme', 'option': None,
     'law': '23-24, 25/1', 'regulation': '16', 'teblig': '49/20', 'art36': 'm', 'base_ipc': 94811, 'amounts': {},
     'product_seizure': 'Evet (ürün ve yapılan imalat)', 'means_seizure': 'Hayır',
     'aliases': 'isleme muhafaza ihrac depo soguk hava yasak urun'},
    {'id': 156, 'violation': 'Yetiştiricilik tesisinde istenen izleme sistem ve cihazlarını bulundurmama veya işler durumda tutmama',
     'option': 'Tesis sahibi', 'law': 'Ek madde - 4', 'regulation': None, 'teblig': None, 'art36': 'p', 'base_ipc': 47397,
     'amount_range': [47397, 237034], 'amounts': {}, 'product_seizure': None, 'means_seizure': None,
     'aliases': 'yetistiricilik tesis balik ciftligi izleme kamera cihaz sistem kayit'},
    {'id': 157, 'violation': 'Ruhsat tezkeresi geçici geri alınmış (askıdaki) gemiyle avcılık', 'option': None,
     'law': '36 (son fıkralar)', 'regulation': '41', 'teblig': '49/5', 'art36': 'genel', 'base_ipc': None, 'amounts': {},
     'amount_note': 'Bu hükümde ayrı idari para cezası yoktur; avcılıkta tespit edilen aykırılığın bendine göre ceza, askıya alma dikkate alınmaksızın ayrıca uygulanır (6/1 Tebliğ 49/5).',
     'product_seizure': None,
     'means_seizure': 'Gemiye, avlanma araçları ve donanımıyla birlikte el konularak mülkiyetin kamuya geçirilmesine karar verilir.',
     'aliases': 'askida askiya alinmis geri alinmis ruhsat tezkeresi el konulan gemi'},
]

# Tebliğ atıflarında beklenen konu sözcüğü (madde başlığı + fıkra metninde aranır).
TEBLIG_TOPIC = {
    44: 'amatör', 45: 'amatör', 47: 'gırgır', 48: 'Ağ Ölçüm', 49: 'kalkan', 50: 'salyangoz', 51: 'algarna',
    52: '90 kulaç', 53: 'derinlik', 54: 'yasağı süresince', 55: 'zıpkın', 56: 'misina', 57: 'markala',
    58: 'sürütme', 60: 'av aracı', 61: 'Tırıvırı', 62: 'salyangoz', 63: 'kum midyesi', 64: 'Kalkan',
    65: 'Palamut', 66: 'akarsu', 67: 'barınak', 68: 'serpme', 69: 'yasak', 70: 'boy', 71: 'ışık', 72: 'trol',
    73: 'trol', 74: 'Dip trol', 75: 'Dip trol', 76: 'rtasu', 77: 'rtasu', 78: 'seyir', 79: 'yasak', 80: 'yasak',
    81: 'yasak', 82: 'bilimsel', 96: 'doğal afet', 97: 'on iki saat', 98: 'on beş gün', 99: 'çalışır',
    100: 'arıza', 101: 'karaya çıkar', 102: 'karaya çıkar', 103: 'karaya çıkar', 104: 'uluslararası',
    105: 'uluslararası', 106: 'uluslararası', 107: 'uluslararası', 108: 'uluslararası', 109: 'uluslararası',
    110: 'damızlık', 111: 'damızlık', 112: 'Nakil', 113: 'Nakil', 114: 'Nakil', 115: 'Hedef dışı',
    116: 'Yetiştiricilik', 155: 'Av yasağı', 157: 'askıya',
}
EXTERNAL_REG = ('Yönetmeliğ', 'yön.', 'Yön.')

STATUS_LABEL = {'uyumlu': '✅ Kanuna uygun', 'duzeltildi': '🛠️ Kanuna göre düzeltildi',
                'eklendi': '➕ Kanundan eklendi (08 tablosunda yok)', 'uyari': '⚠️ Uygulama notu'}


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def tl(value):
    return f'{int(round(value)):,}'.replace(',', '.') + ' TL'


def flat(text):
    return ' '.join(str(text or '').replace('*', '').split())


def mult_for(label):
    return {'<12 m': 1, '12–<22 m': 2, '≥22 m': 3}.get(label)


def band_mults(low, high):
    lo = 1 if low < 12 else 2 if low < 22 else 3
    top = float('inf') if high is None else high
    hi = 1 if top <= 12 else 2 if top <= 22 else 3
    return lo, hi


def amount_text(p):
    if p.get('none'):
        return 'Ayrı idari para cezası yok'
    if 'fixed' in p:
        return f'{tl(p["fixed"])} taban → {tl(BASE_CURRENT[p["fixed"]])}'
    low, high = p['range']
    return f'{tl(low)}–{tl(high)} → {tl(BASE_CURRENT[low])}–{tl(BASE_CURRENT[high])}'


# ── Uygulama: düzeltmeler, eksik hükümler, tekrar/ruhsat metinleri ─────────
def apply(cards):
    cards = [c for c in cards if c.get('origin') != 'kanun']
    by_id = {c['id']: c for c in cards}
    for card_id, field, key, old, new, reason in CORRECTIONS:
        card = by_id[card_id]
        original = card.setdefault('excel_original', {})
        label = f'{field}.{key}' if key else field
        original[label] = old
        if key:
            card.setdefault(field, {})[key] = new
        else:
            card[field] = copy.deepcopy(new)
        fixes = card.setdefault('law_corrections', [])
        if reason not in fixes:
            fixes.append(reason)
    for card_id, extra in ALIASES.items():
        words = set((by_id[card_id].get('aliases') or '').split()) | set(extra.split())
        by_id[card_id]['aliases'] = ' '.join(sorted(words))
    for template in NEW_CARDS:
        card = {'source_row': None, 'repeat': None, 'license_action': None, 'notes': None, 'layout': 'kanun',
                'scope': 'sea_or_general', 'source_doc': LAW_SOURCE, 'origin': 'kanun', **copy.deepcopy(template)}
        cards.append(card)
        by_id[card['id']] = card
    for card in cards:
        pid = CARD_PROVISION.get(card['id'])
        if not pid:
            continue
        p = LAW36[pid]
        if p['repeat'] in ('own', 'criminal'):
            card['repeat'] = p['repeat_text']
        elif p['repeat'] == 'none' and pid != 'askida':
            card['repeat'] = NO_GENERAL
        elif p['repeat'] == 'double' and not card.get('repeat'):
            card['repeat'] = DOUBLE
        if p.get('license') and not card.get('license_action'):
            card['license_action'] = LICENSE_K
    cards.sort(key=lambda c: c['id'])
    return cards


# ── Sağlama ───────────────────────────────────────────────────────────────
def fikra(body, number):
    match = re.search(r'\(%s\)(.*?)(?=\(\d+\)|$)' % number, body, re.S)
    return match.group(1) if match else None


def parse_refs(card):
    """Tebliğ atıflarını (kaynak, madde, fıkra) listesine çevirir."""
    text = str(card.get('teblig') or '')
    source = 'bagis' if card.get('art36') == 'p' else '61'
    if '6/2' in text:
        source = '62'
        text = text.replace('6/2 Tebliğ', '').replace('6/2 tebliğ', '')
    # "(4)" alt bent numarasıdır; "16-17" iki ayrı maddedir, fıkra yalnızca "/" ile ayrılır.
    text = re.sub(r'\(\d+\)', '', text)
    refs = []
    for match in re.finditer(r'(?<![/\d])(\d+)\s*(?:/\s*(\d+))?', text):
        refs.append((source, match.group(1), match.group(2)))
    return refs


def verify(cards):
    law = flat(LAW_DOC.read_text(encoding='utf-8'))
    articles = {(a['source'], str(a['article'])): a for a in load('articles.json')}
    raw_rows = {r['source_row']: r for r in load('raw_excel_rows.json')}
    from build_penalty_links import TIERS
    errors, provisions_seen = [], {}

    # 1. Kanun alıntıları
    for pid, p in LAW36.items():
        if flat(p['quote']) not in law:
            errors.append(f'Kanun metninde bulunamadı ({pid}): {p["quote"][:60]}')
    for name, quote in GENERAL_QUOTES.items():
        if flat(quote) not in law:
            errors.append(f'Kanun metninde bulunamadı ({name})')
    # 2. Yeniden değerleme tutarlılığı
    previous = 0
    for base, current in sorted(BASE_CURRENT.items()):
        ratio = current / base
        if not 9.40 <= ratio <= 9.50 or current <= previous:
            errors.append(f'yeniden değerleme tutarsız: {base} → {current} (oran {ratio:.3f})')
        previous = current

    ids = {c['id'] for c in cards}
    for card in cards:
        cid = card['id']
        pid = CARD_PROVISION.get(cid)
        warnings, fails = [], []
        if not pid:
            errors.append(f'kart {cid}: Kanun 36 hükmüne bağlanmamış')
            continue
        p = LAW36[pid]
        provisions_seen.setdefault(pid, []).append(cid)
        # 3a. bent
        if (card.get('art36') or '-') != p['bent']:
            fails.append(f'bent {card.get("art36")} ≠ 36/{p["bent"]}')
        # 3b. tutar
        amounts = card.get('amounts') or {}
        if p.get('none'):
            if card.get('base_ipc') is not None or amounts:
                fails.append('hükümde idari para cezası yok, kartta tutar var')
        elif card.get('amount_range'):
            if card['amount_range'] != [BASE_CURRENT[p['range'][0]], BASE_CURRENT[p['range'][1]]]:
                fails.append('aralık Kanun aralığıyla uyuşmuyor')
        else:
            values = [(label, value) for label, value in amounts.items()] or [(None, card.get('base_ipc'))]
            tier = TIERS.get(cid)
            for label, value in values:
                if value is None:
                    fails.append('tutar yok')
                    continue
                if label == 'Gırgır':
                    if p.get('purse'):
                        if abs(value - 3 * BASE_CURRENT[p['fixed']]) > TOL:
                            fails.append(f'gırgır tutarı {tl(value)} ≠ 3 × {tl(BASE_CURRENT[p["fixed"]])}')
                    else:
                        warnings.append(f'Kanun bu hükümde gırgır 3 katı öngörmez; tablo gırgır için {tl(value)} yazar (≥22 m tutarı).')
                    continue
                if label:
                    lo = hi = mult_for(label) if p.get('vessel') else 1
                    if not p.get('vessel'):
                        warnings.append('boy kademesi kişi/tesis hükmünde gösterilmiş')
                elif tier:
                    lo, hi = band_mults(*tier)
                elif p.get('vessel'):
                    lo, hi = 1, 3
                else:
                    lo = hi = 1
                if 'fixed' in p:
                    expected = BASE_CURRENT[p['fixed']]
                    if label or tier:
                        if abs(value - expected * lo) > TOL:
                            fails.append(f'{label or "kademe"} {tl(value)} ≠ {tl(expected)} × {lo}')
                    elif abs(value - expected) > TOL:
                        fails.append(f'{tl(value)} ≠ Kanun karşılığı {tl(expected)}')
                    elif p.get('vessel') and cid not in (28, 59):
                        warnings.append('gemi sahibi için boy kademesi tabloda yok; 12–22 m ×2, ≥22 m ×3 uygulanır')
                else:
                    low, high = (BASE_CURRENT[x] for x in p['range'])
                    if label or tier:
                        floor, ceil = low * lo, high * hi
                    elif p.get('vessel'):
                        floor, ceil = low * 3, high  # boyu bilinmeyen gemi: her boyda geçerli olmalı
                    else:
                        floor, ceil = low, high
                    if not floor - TOL <= value <= ceil + TOL:
                        if label or tier or not p.get('vessel'):
                            fails.append(f'{label or ""} {tl(value)} Kanun aralığı dışında ({tl(floor)}–{tl(ceil)})'.strip())
                        else:
                            warnings.append(f'boy kademesi yok; {tl(value)} büyük gemide çarpanlı aralığın dışında kalabilir')
            if p.get('vessel') and amounts:
                base = amounts.get('<12 m')
                for label, factor in (('12–<22 m', 2), ('≥22 m', 3)):
                    if base and label in amounts and 'range' not in p and abs(amounts[label] - base * factor) > TOL:
                        fails.append(f'{label} {tl(amounts[label])} ≠ {tl(base)} × {factor}')
        # 3c. tekrar ve ruhsat
        repeat = card.get('repeat') or ''
        if p['repeat'] == 'double' and '2 kat' not in repeat:
            fails.append('tekrar hükmü (2 kat) eksik')
        if p['repeat'] == 'criminal' and 'hapis' not in repeat:
            fails.append('tekrarda adli yaptırım eksik')
        if p['repeat'] in ('own', 'none') and pid != 'askida' and repeat not in (p.get('repeat_text'), NO_GENERAL):
            fails.append('tekrar metni bent hükmüyle uyuşmuyor')
        licence = card.get('license_action') or ''
        if p.get('license') and '1 ay' not in licence:
            fails.append('ruhsat geri alma hükmü eksik')
        if licence and not p.get('license'):
            warnings.append('Kanun bu bentte ruhsat geri almayı saymaz; Yönetmelik 41 yalnızca Kanun 23/a–b ve 24/b ihlallerini sayar. Tablodaki ruhsat işlemi idari uygulamadır.')
        # 3d. el koyma
        if p.get('seizure') and not str(card.get('product_seizure') or '').startswith('Evet'):
            warnings.append('Kanun el koymayı fiile bağlar; bu satırda ürüne el koyma “Hayır/—” yazılı. Aynı olayın gemi/donatan satırıyla birlikte değerlendirilmelidir.')
        # 4. atıflar
        topic = TEBLIG_TOPIC.get(cid)
        texts = []
        for source, number, sub in parse_refs(card):
            article = articles.get((source, number))
            if not article:
                fails.append(f'Tebliğ atfı yok: {source} Md.{number}')
                continue
            body = article['body']
            if sub:
                part = fikra(body, sub)
                if part is None and source != '62':
                    fails.append(f'Tebliğ atfı fıkrası yok: {source} Md.{number}/{sub}')
                texts.append(article['title'] + ' ' + (part or body))
            else:
                texts.append(article['title'] + ' ' + body)
        # PDF'ten gelen metinde kelimeler bölünmüş olabilir ("çı kış"); boşluksuz karşılaştırılır.
        squeeze = lambda value: flat(value).casefold().replace(' ', '')
        if card.get('teblig') and texts and topic and not any(squeeze(topic) in squeeze(t) for t in texts):
            fails.append(f'Tebliğ atfı konusu uyuşmuyor (beklenen “{topic}”)')
        regulation = str(card.get('regulation') or '')
        if regulation and not any(marker in regulation for marker in EXTERNAL_REG):
            for number in re.findall(r'\d+', regulation):
                if ('reg', number) not in articles:
                    fails.append(f'Yönetmelik atfı yok: Md.{number}')
        elif regulation:
            warnings.append('Dayanak alt yönetmelik (kiralama, balıkçı barınakları veya yetiştiricilik) sistem kaynaklarında yok; madde numarası doğrulanamadı, tutar Kanun aralığıyla sağlandı.')
        # 5. Excel satırı
        if card.get('origin') != 'kanun' and card.get('layout') != 'block':
            original = card.get('excel_original', {})
            excel_value = original.get('base_ipc', card.get('base_ipc'))
            row_no = card.get('source_row')
            # smallblock kalemlerinde tutar başlığın altındaki komşu satırlardadır.
            window = range(row_no - 3, row_no + 9) if card.get('layout') == 'smallblock' else [row_no]
            rows = [raw_rows[n]['search_text'].replace('.', '') for n in window if n in raw_rows]
            if not rows:
                fails.append('Excel ham satırı yok')
            elif excel_value is not None and not any(str(int(excel_value)) in text for text in rows):
                fails.append(f'Excel satırında {int(excel_value)} bulunamadı')
        status = 'eklendi' if card.get('origin') == 'kanun' else 'duzeltildi' if card.get('law_corrections') else \
            'uyari' if warnings else 'uyumlu'
        text = [STATUS_LABEL[status], f'Kanun 36/{p["bent"]} — {p["label"]}: {amount_text(p)}']
        if p.get('vessel') and not p.get('none'):
            text.append('Gemi sahibi/donatan için 12–22 m ×2, ≥22 m ×3')
        if p.get('purse'):
            text.append('gırgır gemisinde 3 katı')
        for cid_label, old in (card.get('excel_original') or {}).items():
            text.append(f'08 tablosundaki değer: {cid_label} = {tl(old) if isinstance(old, int) else (old or "boş")}')
        text += card.get('law_corrections') or []
        if p.get('note'):
            text.append(p['note'])
        text += sorted(set(warnings))
        card['law_check'] = {'status': status, 'provision': pid, 'text': ' · '.join(text)}
        errors += [f'kart {cid}: {f}' for f in fails]

    # 6. kapsam
    for pid in LAW36:
        if pid not in provisions_seen:
            errors.append(f'Kanun 36 hükmünün kartı yok: {pid}')
    for cid in CARD_PROVISION:
        if cid not in ids:
            errors.append(f'eşleştirmedeki kart yok: {cid}')
    return errors


def provision_rows(cards):
    """Ceza Rehberi 'Kanun 36 Sağlaması' tablosu için satırlar."""
    by_pid = {}
    for card in cards:
        check = card.get('law_check') or {}
        by_pid.setdefault(check.get('provision'), []).append(card)
    rows = []
    for pid, p in LAW36.items():
        group = by_pid.get(pid, [])
        statuses = {c['law_check']['status'] for c in group}
        state = ('🛠️ Düzeltme var' if 'duzeltildi' in statuses else '➕ Kanundan eklendi' if statuses == {'eklendi'}
                 else '✅ Uyumlu')
        repeat = {'double': '2 yıl içinde 2 kat', 'criminal': 'Tekrarında adli yaptırım (hapis)',
                  'own': p.get('repeat_text', ''), 'none': 'Genel artırım yok'}[p['repeat']]
        # items_table satır başlığını göstermez; hüküm adı ayrı sütundur.
        details = {'Hüküm': p['label'], 'Kanun Bendi': f'36/{p["bent"]}', 'Kanun Tutarı': amount_text(p),
                   'Boy Çarpanı': ('12–22 m ×2, ≥22 m ×3' + (' · gırgır ×3' if p.get('purse') else '')) if p.get('vessel') else '—',
                   'Tekrar': repeat, 'Ruhsat': 'Geri alma / iptal' if p.get('license') else '—',
                   'Kartlar': ', '.join(str(c['id']) for c in group), 'Sağlama': state}
        if p.get('note'):
            details['Not'] = p['note']
        rows.append((p['label'], details))
    return rows


def report(cards, errors):
    lines = ['# Ceza Dosyası Sağlama Raporu', '',
             f'Kart sayısı: {len(cards)} · Kanun 36 hükmü: {len(LAW36)} · Hata: {len(errors)}', '']
    counts = {}
    for card in cards:
        counts[card['law_check']['status']] = counts.get(card['law_check']['status'], 0) + 1
    lines += [f'- {STATUS_LABEL[k]}: {v}' for k, v in sorted(counts.items())] + ['', '## Hükümler', '']
    for label, details in provision_rows(cards):
        lines.append(f'- **{label}** — ' + ' · '.join(f'{k}: {v}' for k, v in details.items()))
    lines += ['', '## Kartlar', '']
    for card in cards:
        if card['law_check']['status'] != 'uyumlu':
            lines.append(f'- Kart {card["id"]} ({card["violation"][:60]}): {card["law_check"]["text"]}')
    if errors:
        lines += ['', '## Hatalar', ''] + [f'- {e}' for e in errors]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    cards = load('penalty_cards.json')
    fresh = apply(copy.deepcopy(cards))
    errors = verify(fresh)
    if fresh != cards:
        errors.append('penalty_cards.json sağlama sonucuyla güncel değil: python tools/rebuild_structured_data.py')
    if not args.check and REPORT.parent.exists():
        REPORT.write_text(report(fresh, errors), encoding='utf-8')
    for error in errors:
        print('HATA:', error)
    print(f'ceza sağlaması: {len(fresh)} kart, {len(LAW36)} Kanun 36 hükmü, {len(errors)} hata')
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
