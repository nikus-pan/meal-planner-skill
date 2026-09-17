#!/usr/bin/env python3
"""fetch_afa.py — 抓農糧署「農產品產地產期查詢」當月產季曆。

端點：https://www.afa.gov.tw/cht/index.php?code=list&ids=1103&mod_code=search&type=2&period=<月>
用法：
  python3 fetch_afa.py            # 當前月
  python3 fetch_afa.py --month 9
  python3 fetch_afa.py --no-cache

研究依據：.scratch/meal-planner-skill/research/01-season-price-sources.md
- 單一 HTML 表格（thead: 種類/農產品/品種名稱/縣市/行政區/盛產月份）
- period= 參數 = 月（1–12）；keyword 參數不可靠（研究 01 實測），用全表掃
- 產季曆變動慢 → 快取每週一次（cache/afa-<YYYY>-W<ww>.json）
"""
import argparse, json, os, re, sys, urllib.request
from datetime import date, timedelta

BASE = "https://www.afa.gov.tw/cht/index.php?code=list&ids=1103&mod_code=search&type=2&period={month}"
TIMEOUT = 45
UA = "meal-planner-skill/1.0"
CACHE_DAYS = 7

ROW_RE = re.compile(
    r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*"
    r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
    re.S,
)

def _clean(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def fetch_month(month: int) -> dict:
    req = urllib.request.Request(BASE.format(month=month), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        html = r.read().decode("utf-8", errors="replace")
    # 表格範圍：從 table-a-products 到其 </table>
    start = html.find('class="table table-bordered')
    end = html.find("</table>", start)
    table_html = html[start:end] if start != -1 and end != -1 else html
    rows = []
    for m in ROW_RE.finditer(table_html):
        kind, product, variety, county, town, month_text = (_clean(x) for x in m.groups())
        if not product or product == "農產品":
            continue
        rows.append({
            "kind": kind,
            "product": product,
            "variety": variety,
            "county": county,
            "town": town,
            "peak_month": month_text,
        })
    # 收斂：同品項同產區的多品種 → 一筆（保留品種清單）
    by_product = {}
    for row in rows:
        key = (row["product"], row["county"], row["town"])
        by_product.setdefault(row["product"], []).append(row)
    summary = {}
    for product, rs in by_product.items():
        summary[product] = {
            "kinds": sorted(set(r["kind"] for r in rs)),
            "variants": sorted(set(r["variety"] for r in rs if r["variety"])),
            "regions": sorted(set(f"{r['county']}{r['town']}" for r in rs)),
            "peak_month": rs[0]["peak_month"],
        }
    return {
        "source": BASE,
        "month": month,
        "fetched_at": date.today().isoformat(),
        "rows": rows,
        "products": summary,
    }

def cache_path(month: int) -> str:
    d = date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return os.path.join("cache", f"afa-{iso_year}-W{iso_week:02d}-{month:02d}.json")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, default=date.today().month, help="產季曆月份 1-12（預設當前月）")
    ap.add_argument("--no-cache", action="store_true", help="跳過快取，直接抓")
    ap.add_argument("--out", help="輸出 JSON 路徑（預設 cache/ 下）")
    args = ap.parse_args()

    cp = args.out or cache_path(args.month)
    if not args.no_cache and os.path.exists(cp):
        data = json.load(open(cp))
        age_days = (date.today() - date.fromisoformat(data["fetched_at"])).days
        if age_days < CACHE_DAYS:
            data["cache_hit"] = True
            data["cache_age_days"] = age_days
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return
    data = fetch_month(args.month)
    data["cache_hit"] = False
    os.makedirs(os.path.dirname(cp) or ".", exist_ok=True)
    with open(cp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
