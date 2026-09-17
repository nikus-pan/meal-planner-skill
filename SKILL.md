---
name: meal-planner
description: 規劃每日三餐飲食，優先選用當季最便宜食材，依個人健康狀況（糖尿病、高血壓等）與食物禁忌過濾搭配，並能輸入現有食材或口述菜譜產出建議菜單。觸發：「幫我規劃今天的三餐」「今天吃什麼」「冰箱有 XX 怎麼吃」「我糖尿病，這道菜能不能吃」
version: 1
updated: "2026-09-16"
---

> 使用手冊（給人的操作說明＋15 個使用範例）：見 `MANUAL.md`。

## Procedure

1. **確認需求並持久化**：
   - 讀 `state/profiles.json`（家庭成員：姓名、健康標籤、禁忌、份量；上次規劃日期）。檔不存在則建立空結構。
   - 問當日輸入：現有食材清單（自由文字）、指定菜譜（選用）、規劃日期（預設今天）、規劃天數（1–7 日，預設 1 日）、採買地點/地區（預設讀 `state/profiles.json` 的 `shopping_region`，無則問，例：屏東）。
   - 有採買地點時：step 2 `fetch_moa.py` 加 `--market <地區主要市場>`（地區→市場對照見 `references/shopping-hints/<region>.yaml`，例：屏東 → 屏東市）；step 4 產出追加「⑥ 採買建議」區塊。
   - 規劃天數 > 1 時：菜單 = 每日各 1 組、採購清單跨日匯總、健康提醒/替代建議跨日共用（03 定案）；strict 逐日獨立判級、高鈉品項跨日提醒「勿重複堆疊」（04 定案）。
   - **差異偵測**：本次輸入的家庭/標籤與 profiles 有差異 → 逐項列出差異，問「要更新既有紀錄嗎？(更新/保留舊的)」；更新則寫回，保留則本次依舊紀錄並註記「未更新」。
   - Done：profiles 與當日輸入齊全、差異已確認（更新/保留）。

2. **載入當季低價來源**：
   - `scripts/fetch_moa.py`（農業部價格 API，近 7 日窗）＋ `scripts/fetch_afa.py`（農糧署產季曆）＋ `scripts/fetch_fish.py`（漁類牌價，opendata.vip 匯集農漁會公開牌價；蔬果/豆類/菌菇仍走 fetch_moa.py，魚貝類改走 fetch_fish.py）。
   - 魚貝類品項（清蒸魚、小魚、魷魚等）：`fetch_fish.py <品名> [--market <市場>]` 抓牌價（上/中/下/平均價＋交易量）；找不到品名時 → 標「無牌價（fog：opendata.vip 未覆蓋此品項）」，fallback 同蔬果三層；貝類品項（干貝、鮮蚵、牡蠣、蛤、扇貝）無獨立每日牌價來源（fog 確認 2026-09-17），一律走固定估算價，干貝註記「時價波動大，估算取保守值」。
   - 失敗走三層 fallback，依序，第一層成功即停：(a) 田邊好幫手 `m.moa.gov.tw` POST；(b) skill 內建靜態產季/品名表（`references/`）；(c) websearch「品名 批發價 行情」摘要（標「非結構化、需人工核」）。
   - 過濾 `CropName=='休市'` 或 `Trans_Quantity==0` 的行（研究 04 (e)）。
   - Done：取得「當季品項 + 預估價（低/中/高）」清單。

3. **套規則與搭配**：
   - 讀 `references/dietary-rules/`（diabetes/hypertension/allergens 的 strict/advisory）＋ `references/recipes/index.yaml`（菜譜庫，口述菜名匹配；未命中走模糊→websearch 1 次→回寫→即時解析）。
   - 多人取 strict 交集、advisory 取最嚴；strict violation 預設替換（保留菜框架、換低風險食材、附註原/替），單菜 violation > 2 項 → 剔除＋建議替代。
   - 現有食材填進菜單，缺料補購走第 2 步清單。
   - Done：每時段主力/副/湯/飯確定、替代建議就位。

4. **產出**：
   - markdown 表格 4 區塊：菜單（單日 = 一日菜單；多日 = Day 1…Day N 每日各 1 組，跨日共用健康提醒/替代建議各 1 份，採購清單跨日匯總）、採購清單、健康提醒、替代建議；末行固定「以上為飲食建議，非醫療診斷；請依醫師/營養師指引調整」。
   - **採買建議**（有採買地點時，第 5 區塊）：
     - 讀 `references/shopping-hints/<region>.yaml`（依 `shopping_region` 對檔名：屏東 → pingtung.yaml）。
     - 列 1–2 家該地區市場：名稱、地址、營業時間、特色（`note` 欄）。
     - 該市場 MOA 實測價（step 2 以 `--market` 抓得）vs 全區加權均價（無 `--market` 時 `per_market` 全市場均價）：兩者皆有 → 顯示「屏東市 23.6 元/kg（全區均 18.5）」。
     - 該市場無 MOA 數據 → 標「無實測價，走一般菜市場行情（營業時間內）」；魚貝類品項改標「漁類牌價（opendata.vip，fetch_fish.py 抓得），若無覆蓋此品項 → 無牌價」。
     - `custom_markets` 非空 → 一併列出（標「自加市場，無實測價」）。
     - `<region>.yaml` 不存在 → 標「無該地區市場資訊；使用者可自加市場名稱（寫入 custom_markets）」＋ websearch 1 次補。
   - **製作過程詢問**（產出 4 區塊後）：問「要附上建議菜單上每道菜的製作過程嗎？」
     - 使用者答「是」→ 追加 `製作過程` 區塊：單日 = 當日菜單上每道菜列 1 份；多日 = 全部日別菜單結束後**1 段**（不逐日跟）。每道菜依 `references/recipes/<菜>.yaml` 的 `steps` 欄列出（stage 備料/烹調/完成，每步 1 動作＋分鐘數）；菜未命中本庫時依 step 3 fallback 解析後再列。
     - 使用者答「否」→ 不追加，產出止於 4 區塊。
     - 預設 = **主動問一次**（不自動附上、也不靜默略過）；多日規劃同樣問一次。
   - 對話內輸出，不另存檔（對照 finder-job 報告慣例）。
   - Done：4（有採買地點時 5）區塊齊全、全為 markdown 表格；製作過程區塊 = 依回答附上或略過；採買建議 = 有地點時附上。

5. **迭代**：
   - 換菜（指定菜名重排該時段）/換人（加減成員重算 strict 交集與份量，寫回 profiles）/換食材（缺料走替代建議欄）。
   - 每項迭代重跑步驟 3–4。
   - Done：使用者滿意或明確停。

## Notes

- `state/profiles.json` 放 skill 目錄下，仿 finder-job 的 `method-log.json` 自更新模式；gitignore 之；同步 `.omp/`、`.opencode/` 時 `state/` 不隨同（各自維護），只有 `references/`＋`SKILL.md`＋`scripts/` 同步。
- 品名一律用農業部正式代碼名（`references/dietary-rules/ingredient-map.yaml`）；未命中俗名先查映射表，再 websearch 核對後回寫。
- 匿名 API 只給第一頁（研究 04 (a)）：`Next=true` 當截斷訊號，縮小日期窗重查，不傳 `Page≥2`。
- 健康規則僅作飲食建議；strict 規則的 violation 判級依 `references/dietary-rules/` 的 `level` 欄，不自創規則。

## Verification

1. 資料齊全後同回合進步驟 2，無停頓；profiles 差異未確認前不進步驟 2。
2. 三層 fallback 依序，第一層成功不進後續層。
3. 產出 4 區塊全為 markdown 表格、末行有醫療邊界聲明。
4. 菜譜口述未命中時，fallback 鏈 = index → 模糊 → websearch(1 次) → 回寫 → 即時解析，不直接編造食譜。
