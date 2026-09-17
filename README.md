# meal-planner

一個 agent skill：規劃每日三餐飲食，優先選用當季最便宜食材，依個人健康狀況（糖尿病、高血壓）與食物禁忌自動過濾搭配；支援輸入現有食材、口述菜譜、多日規劃與地區採買建議。

## 內容

| 路徑 | 說明 |
|---|---|
| `SKILL.md` | skill 主文件（agent 依此執行 5 步驟流程） |
| `MANUAL.md` | **使用手冊**：功能總覽、資料來源、產出格式、15 個使用範例、已知限制 |
| `references/recipes/` | 台味家常菜食譜庫（YAML，含 `steps` 烹調步驟）＋ `index.yaml` |
| `references/dietary-rules/` | 糖尿病／高血壓／過敏原 strict＋advisory 規則、品名對照表 |
| `references/shopping-hints/` | 7 地區市場資訊（屏東、台北、高雄、台中、台南、新竹、南投） |
| `scripts/fetch_moa.py` | 農業部蔬果批發價（近 7 日窗，`--market <地區>` 過濾） |
| `scripts/fetch_fish.py` | 漁類每日牌價（opendata.vip） |
| `scripts/fetch_afa.py` | 農糧署產季曆 |

> 本倉庫為獨立快照：不含 `state/`（家庭 profiles，各環境獨立維護）與 `scripts/cache/`（暫存檔）。

## 安裝

放進 agent runtime 的 skill 目錄（需目錄名 `meal-planner`）：

```bash
git clone https://github.com/<your-username>/meal-planner-skill
cp -r meal-planner-skill <runtime>/skills/meal-planner
```

## 使用

安裝後，直接對 agent 說自然語言即可，例如：

- 「幫我規劃今天的三餐。」
- 「我有糖尿病，這道菜能不能吃？」
- 「冰箱有剩飯、豆腐、蛋，幫我搭配今天的菜單。」
- 「規劃 7 天，採買地點是高雄。」

完整操作說明與 15 個範例見 [`MANUAL.md`](MANUAL.md)。

## 資料來源

| 來源 | 用途 | 限制 |
|---|---|---|
| 農業部價格 API（`fetch_moa.py`） | 蔬果／豆類／菌菇 近 7 日批發價 | 無漁類；無特定品項走三層 fallback |
| opendata.vip（`fetch_fish.py`） | 漁類每日牌價（市場／品項／上下中價／交易量） | 第三方匯集站；部分品項（干貝等貝類）未覆蓋 → 走固定估算價 |
| 農糧署產季曆（`fetch_afa.py`） | 產季參考 | — |
| 各縣市集發展局／市場處公開資訊 | 市場地址與營業時間（`shopping-hints/`） | 營業時間以現場為準 |

## 健康邊界

本 skill 產出為**飲食建議，非醫療診斷**；健康規則（糖尿病 T1–T7、高血壓 H1–H3、過敏原 A1–A7）依 `references/dietary-rules/` 定義，請依醫師／營養師指引調整。
