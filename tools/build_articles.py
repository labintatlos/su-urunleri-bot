"""Mevzuat maddelerinin metnini paketlenen Markdown tam metinlerinden üretir.

    python tools/build_articles.py          # data/articles.json dosyasını yazar
    python tools/build_articles.py --check  # güncel değilse hata verir

Eski gövdeler PDF'ten çıkarılmıştı: satırlar PDF satır sonlarında kırılıyor,
kelimeler bölünüyor, tablolar düz metne dönüşüyordu. Madde ekranı artık bu
betiğin Markdown'dan aldığı paragraf ve tabloları gösterir (6.0.37). Madde
numarası ve kapsam (scope) korunur; Ek ve Geçici maddeler numaralı madde
olarak saklanmadığından alınmaz. Kılavuz kayıtlarına dokunulmaz.
"""
import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / 'su_urunleri_bot' / 'data'
MARKDOWN = DATA / 'markdown'

FILES = {
    'law': '1380 SU ÜRÜNLERİ KANUNU MARKDOWN.md',
    'reg': '1380 SU ÜRÜNLERİ YÖNETMELİĞİ MARKDOWN.md',
    '61': '6-1 TİCARİ AMAÇLI SU ÜRÜNLERİ AVCILIĞININ DÜZENLENMESİ TEBLİĞİ MARKDOWN.md',
    '62': '6-2 AMATÖR AMAÇLI SU ÜRÜNLERİ AVCILIĞININ DÜZENLENMESİ TEBLİĞİ MARKDOWN.md',
    'bagis': 'BALIKÇI GEMİLERİNİ İZLEME SİSTEMİ TEBLİĞİ MARKDOWN.md',
}

ARTICLE = re.compile(r'^\*\*(Ek |EK |Geçici |GEÇİCİ )?(?:Madde|MADDE) (\d+) –\*\*\s*(.*)$')

# Markdown'da başlığı olmayan maddeler; ad madde metninden verilir.
TITLES = {('law', 40): 'Yürürlük', ('law', 41): 'Yürütme'}


def clean_title(text):
    text = re.sub(r'^.*BÖLÜM[^:]*:\s*', '', text.strip())
    return text.rstrip(':').strip()


def parse(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    articles, heading, current = {}, None, None

    def finish():
        if current is not None:
            body = '\n'.join(current['lines']).strip()
            articles[current['number']] = {'title': current['title'], 'body': re.sub(r'\n{3,}', '\n\n', body)}

    def next_is_article(index):
        for line in lines[index + 1:]:
            if line.strip():
                return bool(ARTICLE.match(line))
        return False

    for index, line in enumerate(lines):
        match = ARTICLE.match(line)
        if match:
            finish()
            current = None
            if not match.group(1):
                number = int(match.group(2))
                if number in articles:
                    raise ValueError(f'{path.name}: Madde {number} iki kez geçiyor')
                current = {'number': number, 'title': clean_title(heading or ''), 'lines': [match.group(3)]}
            # Başlık yalnız hemen ardından gelen maddenin adıdır; başlıksız madde
            # (ör. Yönetmelik 20) önceki maddenin adını almaz.
            heading = None
            continue
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            if current is not None and level >= 4:
                # Kanunda madde adları "#### Muaflıklar:" biçimindedir; biri maddenin
                # son fıkrasından önce yazılmış olsa da sonraki maddenin adıdır.
                if text.endswith(':') or next_is_article(index):
                    heading = text
                    continue
                # 6/2 Tebliğdeki "#### Çizelge 1" başlıkları madde metninin parçasıdır.
                current['lines'].append(f'**{text}**')
                continue
            finish()
            current, heading = None, text
            continue
        if line.strip() == '---':
            finish()
            current, heading = None, None
            continue
        if current is not None:
            current['lines'].append(line)
    finish()
    return articles


def build():
    existing = json.loads((DATA / 'articles.json').read_text(encoding='utf-8'))
    parsed = {source: parse(MARKDOWN / name) for source, name in FILES.items()}
    result = []
    for row in existing:
        if row['source'] not in parsed:
            result.append(row)
            continue
        found = parsed[row['source']].pop(row['article'], None)
        if found is None:
            raise ValueError(f'Markdown metninde yok: {row["source"]} Madde {row["article"]}')
        # Eski PDF başlıkları bozuk olabilir ("yönetmelikle belirlenir."); kullanılmaz.
        title = TITLES.get((row['source'], row['article']), found['title'])
        result.append({**row, 'title': title, 'body': found['body']})
    for source, remaining in parsed.items():
        for number, found in sorted(remaining.items()):
            title = TITLES.get((source, number), found['title'])
            result.append({'source': source, 'article': number, 'title': title, 'body': found['body'],
                           'page_start': None, 'page_end': None, 'scope': 'general'})
    order = list(dict.fromkeys(row['source'] for row in result))
    result.sort(key=lambda row: (order.index(row['source']), row['article']))
    empty = [f'{row["source"]} {row["article"]}' for row in result if row['source'] in FILES and not row['body']]
    if empty:
        raise ValueError(f'Metni boş madde: {empty}')
    return result


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rendered = dump(build())
    path = DATA / 'articles.json'
    if path.read_bytes() != rendered:
        if args.check:
            raise SystemExit('articles.json Markdown metinlerine göre güncel değil')
        path.write_bytes(rendered)
        print('üretildi: articles.json')
    else:
        print('doğrulandı: articles.json')


if __name__ == '__main__':
    main()
