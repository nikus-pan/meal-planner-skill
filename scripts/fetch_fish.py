#!/usr/bin/env python3
"""fetch_fish.py — 漁產品批發價（opendata.vip 匯集之農漁會公開牌價）

來源：https://www.opendata.vip/agriProduct/fisheryPrice
（第三方聚合站；原始資料 = 農業部漁產品批發市場公開牌價；每日更新）

用法：
  python3 fetch_fish.py 秋刀魚 魷魚 [--market 台北] [--out cache/fish-<日>.json] [--map <path>]

輸出 JSON（stdout 同時寫 cache/）：
  {
    "source": "opendata.vip",
    "url": "...",
    "fetched_at": "ISO",
    "items": [
      {"query": "秋刀魚", "mapped_from": null, "ok": true,
       "rows": [{"market":..., "crop":..., "upper":..., "middle":..., "lower":..., "avg":..., "volume_kg":...}],
       "per_market": {"台北": {"weighted_avg":..., "total_volume":..., "n_rows":...}},
       "hits": N}
    ],
    "errors": [...], "ok": true|false
  }

注意：
- 品項 substring match（「鯛」會含 18 筆）；精確品名查不到 0 筆時標 error。
- opendata.vip 無「日期」欄（牌價 = 抓取當下）；cache 檔名含日。
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request, datetime

URL = 'https://www.opendata.vip/agriProduct/fisheryPrice'

def fetch_html(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

def parse_table(html):
    """Return list of rows: [market, crop, upper, middle, lower, avg, volume_kg]."""
    m = re.search(r'<table class="myDataTable.*?</table>', html, re.S)
    if not m:
        return []
    out = []
    for row in re.findall(r'<tr>(.*?)</tr>', m.group(0), re.S):
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td.*?>(.*?)</td>', row, re.S)]
        if len(cells) < 6:
            continue
        try:
            out.append({'market': cells[0], 'crop': cells[1],
                       'upper': float(cells[2] or 0), 'middle': float(cells[3] or 0),
                       'lower': float(cells[4] or 0), 'avg': float(cells[5] or 0),
                       'volume_kg': float(cells[6] or 0) if len(cells) > 6 else 0.0})
        except ValueError:
            continue
    return out

def load_map(path):
    """Minimal YAML: mappings: <common>: <official> (同 fetch_moa.py 慣例)。"""
    mp = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r'\s*(\S+):\s*(\S+)\s*$', line)
        if m and m.group(1) not in ('mappings',):
            mp[m.group(1)] = m.group(2)
    return mp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('crops', nargs='+', help='品名（可多個）')
    ap.add_argument('--market', help='只回傳指定市場（例：台北）；無該市場數據時該品項標 error')
    ap.add_argument('--map', help='品名對照表（常用名 → 牌價品名），path')
    ap.add_argument('--out', help='輸出 JSON 路徑（預設 cache/fish-<今日>.json，相對於本 script）')
    args = ap.parse_args()

    mp = load_map(args.map) if args.map else {}
    url = URL + (f'?market_name={urllib.parse.quote(args.market)}' if args.market else '')
    html = fetch_html(url)
    rows = parse_table(html)

    result = {'source': 'opendata.vip', 'url': url,
              'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
              'items': [], 'errors': [], 'ok': True}

    for c in args.crops:
        official = mp.get(c, c)
        hits = [r for r in rows if official in r['crop']]
        item = {'query': official, 'mapped_from': c if c != official else None,
                'rows': hits, 'hits': len(hits),
                'per_market': {}}
        for r in hits:
            pm = item['per_market'].setdefault(r['market'], {'weighted_avg': 0.0, 'total_volume': 0.0, 'n_rows': 0, 'wsum': 0.0})
            pm['wsum'] += r['avg'] * r['volume_kg']
            pm['total_volume'] += r['volume_kg']
            pm['n_rows'] += 1
        for mkt, pm in item['per_market'].items():
            pm['weighted_avg'] = round(pm['wsum'] / pm['total_volume'], 2) if pm['total_volume'] else 0.0
            del pm['wsum']
        if args.market:
            item['per_market'] = {k: v for k, v in item['per_market'].items() if k == args.market}
            item['rows'] = [r for r in item['rows'] if r['market'] == args.market]
            item['hits'] = len(item['rows'])
        if item['hits'] == 0:
            item['error'] = f'無 {official} 數據（opendata.vip 牌價表）'
            result['errors'].append(f'{c}: {item["error"]}')
            result['ok'] = False
        result['items'].append(item)

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'cache', f"fish-{datetime.date.today().isoformat()}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(result, sys.stdout, ensure_ascii=False)
    print()

if __name__ == '__main__':
    main()
