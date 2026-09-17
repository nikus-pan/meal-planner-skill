#!/usr/bin/env python3
"""fetch_moa.py — 抓農業部開放資料 API 的當季蔬果批發行情。

端點：https://data.moa.gov.tw/api/v1/AgriProductsTransType/
用法：
  python3 fetch_moa.py 甘藍 金鉤菇 秋刀魚
  python3 fetch_moa.py 高麗菜 --map ../references/dietary-rules/ingredient-map.yaml
  python3 fetch_moa.py 甘藍 --days 7 --out /tmp/moa.json

研究依據：.scratch/meal-planner-impl/research/04-moa-api-pagination.md
- 匿名只給第一頁（不傳 Page；Next=true = 截斷訊號，非游標）
- 錯誤看 body.RS 非 HTTP status
- 過濾 CropName=='休市' 或 Trans_Quantity==0 的行
- 日期 = 民國點號 Y.MM.DD（民國年 = 西元年 - 1911）
"""
import argparse, json, sys, urllib.request, urllib.parse
from datetime import date, timedelta

API = "https://data.moa.gov.tw/api/v1/AgriProductsTransType/"
TIMEOUT = 45

def simple_yaml_map(path):
    """最小 YAML 解析：只讀頂層 mappings: 下的 `俗名: 正式名` 行，不依賴 pyyaml。"""
    m = {}
    in_map = False
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s.startswith("mappings:"):
            in_map = True
            continue
        if in_map:
            if not s or s.startswith("#"):
                continue
            if s.startswith("  ") and ":" in s:
                k, v = s.strip().split(":", 1)
                m[k.strip()] = v.strip()
            elif not s.startswith("  ") and not s.startswith("#"):
                in_map = False
    return m

def iso_to_minguo(d: date) -> str:
    return f"{d.year - 1911:03d}.{d.month:02d}.{d.day:02d}"

def minguo_to_iso(s: str) -> str:
    """'115.09.16' -> '2026-09-16'（best-effort，失敗回原串）。"""
    try:
        y, m, dd = s.split(".")
        return f"{int(y) + 1911:04d}-{m}-{dd}"
    except Exception:
        return s

def fetch_one(crop: str, start: date, end: date) -> dict:
    params = urllib.parse.urlencode({
        "Start_time": iso_to_minguo(start),
        "End_time": iso_to_minguo(end),
        "CropName": crop,
        # 匿名：不傳 Page（研究 04 (a)：Page>=2 回 RS:ERROR「非會員只限回傳第一頁資料」）
    })
    req = urllib.request.Request(f"{API}?{params}",
                                 headers={"User-Agent": "meal-planner-skill/1.0"})
    out = {"query": crop, "rows": [], "per_market": {}, "hits": 0,
           "truncated": False, "error": None}
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        out["error"] = f"http: {e}"
        return out
    if body.get("RS") != "OK":
        out["error"] = f"RS:{body.get('RS')} MSG:{body.get('MSG')}"
        return out
    out["truncated"] = bool(body.get("Next"))
    data = body.get("Data") or []
    rows = []
    for d in data:
        if d.get("CropName") == "休市" or not d.get("Trans_Quantity"):
            continue  # 研究 04 (e)：休市行污染所有查詢
        try:
            vol = float(d.get("Trans_Quantity") or 0)
            # 實測欄位名（2026-09-16）：Upper_Price / Middle_Price / Lower_Price / Avg_Price
            avg = float(d.get("Avg_Price") or 0)
            low = float(d.get("Lower_Price") or 0)
            high = float(d.get("Upper_Price") or 0)
        except (TypeError, ValueError):
            continue
        if vol <= 0:
            continue
        rows.append({
            "date": minguo_to_iso(str(d.get("TransDate", ""))),
            "market": d.get("MarketName"),
            "crop": d.get("CropName"),
            "crop_code": d.get("CropCode"),
            "avg_price": avg,
            "low_price": low,
            "mid_price": float(d.get("Middle_Price") or 0),
            "high_price": high,
            "volume": vol,
        })
    out["rows"] = rows
    out["hits"] = len(rows)
    # per-market 收斂：同市場取「最新一日、全子品項」的加權均價（權重 = 交易量）
    by_mkt_day = {}
    for row in rows:
        by_mkt_day.setdefault((row["market"], row["date"]), []).append(row)
    # 每市場取最新日
    latest_day = {}
    for (mkt, day) in by_mkt_day:
        latest_day[mkt] = day if mkt not in latest_day or day > latest_day[mkt] else latest_day[mkt]
    pm = {}
    for mkt, day in sorted(latest_day.items()):
        day_rows = by_mkt_day[(mkt, day)]
        wsum = sum(r["avg_price"] * r["volume"] for r in day_rows)
        wtot = sum(r["volume"] for r in day_rows)
        pm[mkt] = {
            "date": day,
            "crops": [r["crop"] for r in day_rows],
            "weighted_avg": round(wsum / wtot, 2) if wtot else 0.0,
            "total_volume": wtot,
        }
    out["per_market"] = pm
    # 7 日走勢：全市場加權均價依日
    by_day = {}
    for row in rows:
        by_day.setdefault(row["date"], []).append(row)
    trend = []
    for day in sorted(by_day):
        rs = by_day[day]
        wsum = sum(r["avg_price"] * r["volume"] for r in rs)
        wtot = sum(r["volume"] for r in rs)
        trend.append({"date": day, "weighted_avg": round(wsum / wtot, 2) if wtot else 0.0})
    out["trend_7d"] = trend
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("crops", nargs="+", help="品名（農業部正式品名；俗名需配 --map）")
    ap.add_argument("--map", help="品名映射 YAML（俗名 -> 正式名），可選")
    ap.add_argument("--days", type=int, default=7, help="往前推 N 日（預設 7）")
    ap.add_argument("--end", help="結束日 YYYY-MM-DD（預設昨日）")
    ap.add_argument("--out", help="輸出 JSON 路徑（預設 cache/moa-<今日>.json，相對於本 script）")
    ap.add_argument("--market", help="只回傳指定市場（例：屏東市）；無該市場數據時該品項標 error")
    args = ap.parse_args()

    mp = simple_yaml_map(args.map) if args.map else {}
    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    start = end - timedelta(days=max(1, args.days - 1))

    result = {"ok": True, "generated_at": date.today().isoformat(),
              "window": {"start": iso_to_minguo(start), "end": iso_to_minguo(end)},
              "items": [], "errors": []}
    for c in args.crops:
        official = mp.get(c, c)
        item = fetch_one(official, start, end)
        if official != c:
            item["mapped_from"] = c
        if args.market:
            mkt = args.market
            mkt_pm = item.get("per_market", {}).get(mkt)
            mkt_rows = [r for r in item.get("rows", []) if r.get("market") == mkt]
            if not mkt_pm and not mkt_rows:
                item["error"] = item.get("error") or f"無 {mkt} 數據（近 7 日）"
                item["per_market"] = {}
                item["rows"] = []
                item["hits"] = 0
            else:
                item["rows"] = mkt_rows
                item["per_market"] = {k: v for k, v in item.get("per_market", {}).items() if k == mkt}
                item["hits"] = len(mkt_rows)
                # recompute trend_7d from filtered rows
                by_day = {}
                for row in mkt_rows:
                    by_day.setdefault(row["date"], []).append(row)
                trend = []
                for day in sorted(by_day):
                    rs = by_day[day]
                    wsum = sum(r["avg_price"] * r["volume"] for r in rs)
                    wtot = sum(r["volume"] for r in rs)
                    trend.append({"date": day, "weighted_avg": round(wsum/wtot,2) if wtot else 0.0})
                item["trend_7d"] = trend
        if item["error"]:
            result["errors"].append(f"{c}: {item['error']}")
            result["ok"] = False
        result["items"].append(item)

    out_path = args.out
    if not out_path:
        out_path = "cache/moa-" + date.today().isoformat() + ".json"
        os_mkdir = __import__("os").makedirs
        __import__("os").makedirs("cache", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
