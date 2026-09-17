# meal-planner 使用手冊

本手冊說明 `meal-planner` skill 的功能、使用方法，以及 15 個使用範例。
skill 主文件為同目錄下 `SKILL.md`（agent 執行用）；本手冊是給「人」讀的操作說明。

---

## 1. 功能總覽

| 功能 | 說明 |
|---|---|
| 每日三餐規劃 | 早餐/午餐/晚餐（＋配菜、湯、飯），可指定單餐或全日 |
| 多人家庭規劃 | 依 `profiles.json` 家庭成員＋健康標籤，取 strict 交集、advisory 最嚴 |
| 健康條件過濾 | 糖尿病（T1–T7）、高血壓（H1–H3）、過敏原（A1–A7），依 `references/dietary-rules/` 自動替換或剔除 |
| 當季低價食材 | 蔬果走 `fetch_moa.py`（農業部 API，近 7 日窗）、漁類走 `fetch_fish.py`（opendata.vip 每日牌價） |
| 採買地點 | 7 地區（屏東、台北、高雄、台中、台南、新竹、南投）市場資訊，見 `references/shopping-hints/` |
| 現有食材填單 | 輸入冰箱現有食材，agent 填進菜單、缺料列採購清單 |
| 口述菜譜 | 未命中現有菜譜庫時走 fallback：模糊匹配→websearch 1 次→回寫→即時解析 |
| 多日規劃 | 1–7 日，每日各 1 組菜單、採購清單跨日匯總、高鈉品項跨日提醒勿堆疊 |

---

## 2. 資料來源與檔案

| 路徑 | 內容 |
|---|---|
| `SKILL.md` | skill 主文件（agent 依此執行 5 步驟） |
| `references/recipes/` | 道譜 YAML＋`index.yaml`（v1–v7 累計擴充） |
| `references/dietary-rules/` | 糖尿病/高血壓/過敏原 strict＋advisory 規則、品名對照表 |
| `references/shopping-hints/` | `7 個地區市場 YAML`（hsinchu、kaohsiung、nantou、pingtung、taichung、tainan、taipei） |
| `scripts/fetch_moa.py` | 農業部蔬果批發價（`--market <地區>` 過濾） |
| `scripts/fetch_fish.py` | 漁類每日牌價（opendata.vip） |
| `scripts/fetch_afa.py` | 農糧署產季曆 |
| `scripts/sync.sh` | 同步三 runtime（排除 `state/`、`cache/`） |
| `state/profiles.json` | 家庭成員＋健康標籤＋`shopping_region`（各 runtime 獨立，不同步） |

---

## 3. 產出格式

每次規劃產出 **4 個區塊**（有採買地點時加第 5 區塊）：

1. **菜單**（單日＝一組；多日＝Day 1…Day N 每日各 1 組，跨日共用健康提醒/替代建議）
2. **採購清單**（跨日匯總，含實測價/牌價欄）
3. **健康提醒**（全日限制、strict violation 說明）
4. **替代建議**（品項→替代→觸發）

末行固定：「以上為飲食建議，非醫療診斷；請依醫師/營養師指引調整。」

產出 4 區塊後 agent 主動問一次「要附上製作過程嗎？」，答「是」→ 追加 `製作過程` 區塊（依 `steps` 欄，多日 = 全部日別後 1 段）。

---

## 4. 使用範例

**範例 1：單日規劃（最簡單）**

> 使用者：「幫我規劃今天的三餐。」

Agent step 1 問當日輸入（現有食材？指定菜？天數？採買地點？），全答「無/預設」→ 走 1 日、無採買地點。產出 4 區塊（菜單、採購清單、健康提醒、替代建議）＋主動問「要附上製作過程嗎？」

**範例 2：家庭多人＋糖尿病/高血壓 strict 交集**

> 使用者：「阿公有糖尿病和高血壓，媽媽有花生過敏，我沒有。規劃這三天，家裡有兩顆蛋和一把青菜。」

Agent 建 strict 交集（T2 禁含糖飲料＋H1 鈉≤2300＋A5 花生禁忌），規劃 3 日，每日各 1 組菜單，採購清單跨日匯總，高鈉品項跨日提醒「勿重複堆疊」。

**範例 3：指定菜譜＋健康條件自動替換**

> 使用者：「我想吃麻婆豆腐，但我有高血壓，幫我調整。再配一飯一青菜，給我今天的菜單。」

Agent 讀 `麻婆豆腐.yaml`，偵測 strict violation（豆瓣醬鈉高→H1），自動替換（豆瓣醬減量或低鈉版），保留菜框架、附註原/替；搭配燙青菜（去鈉洗滌法）與飯。

**範例 4：有採買地點（高雄）＋漁類牌價**

> 使用者：「規劃 7 天，採買地點是高雄。」

Step 2 蔬果走 `fetch_moa.py --market 高雄`、魚貝類走 `fetch_fish.py`；step 4 產出加第 5 區塊「⑤ 採買建議」：列高雄 3 市場＋漁類實測牌價（例：鯛 梓官 201.6 元/kg）；干貝等貝類標「無獨立牌價（fog），走固定估算價」。

**範例 5：現有食材填菜單＋未命中菜走 fallback**

> 使用者：「家裡有剩飯、半顆高麗菜、一把豆腐、三顆蛋，幫我想辦法做成今天的三餐。」

Agent 把現有食材填進菜單（剩飯→台式炒飯、高麗菜→燙青菜、豆腐→小魚炒豆腐、蛋→菜脯蛋），缺料補購走採購清單；若口述的菜名不在現有菜譜庫內→模糊匹配→websearch 1 次→回寫 references→即時解析，不停下。

**範例 6：只有我自己吃（單人、無家庭 profiles）**

> 使用者：「只有我自己吃，幫我規劃今天的三餐，我無特殊健康狀況。」

Agent step 1 偵測到輸入與 profiles 差異（profiles 記 3 人家庭，本次只有 1 人），列出差異，問「要更新既有紀錄嗎？(更新／保留舊的)」；若「保留舊的」→ 本次按 1 人份算、profiles 不動；若「更新」→ 寫回 profiles 成員=我 1 份。無健康標籤 → strict 交集為空，菜單按當季低價＋無禁忌產出；份量 = 1。

**範例 7：單獨一餐（只規劃一餐，不三餐）**

> 使用者：「我中午想吃碗牛肉麵，幫我看看這餐有沒有超量（我有高血壓），下午不用吃。」

Agent step 1 規劃天數=1、時段=午餐（單餐，非全日三餐）；step 3 口述「牛肉麵」未命中現有菜譜庫 → 模糊匹配→websearch 1 次→回寫 references→即時解析（牛肉麵含滷汁/醬油鈉高 → H1 strict violation，預設替換：高湯去油、滷汁減半、勿加味精）；產出 4 區塊但「菜單」只列午餐 1 組、採購清單只含該餐缺料、健康提醒註記「下午不吃→晚餐建議清淡（例：燙青菜＋無糖湯），避免隔日堆疊」。

**範例 8：新增家庭成員（改 profiles 成員數據）**

> 使用者：「弟弟要來住一陣子，他有低血糖，幫我把他加進來，之後規劃都算他的份量。」

Agent step 1 差異偵測：profiles 無此成員 → 列出「新增成員：弟弟（低血糖、1 份）」，寫回 `state/profiles.json`；low-blood-sugar 非既有 strict 標籤（diabetes 標籤係高血糖 T1–T7），先核 `references/dietary-rules/diabetes.yaml` 是否有對應 advisory，無 → 標「自訂提醒：定時進食、避免空腹，餐間可備 1 片葡萄糖」（依使用者口述，不進 dietary-rules 正式規則），健康提醒區塊列出。

**範例 9：修改成員健康標籤（改 profiles 成員數據）**

> 使用者：「媽媽的高血壓控制得好了，医生說可以正常食鹽量，把她的 H1 標籤拿掉。」

Agent step 1 差異偵測：媽媽 conditions 由 `[高血壓]` → `[]` → 列出差異、問「要更新既有紀錄嗎？(更新／保留舊的)」；「更新」→ 寫回 profiles、重算 strict 交集（H1 仍因阿公保留在全家交集＝「多人取 strict 交集、advisory 取最嚴」，阿公 H1 未變 → 全家 H1 仍生效，只是媽媽個人不再標 H1）；健康提醒註記「H1 依阿公保留（最嚴交集），媽媽個人可正常食鹽量」。

**範例 10：刪除家庭成員（改 profiles 成員數據）**

> 使用者：「阿公搬去南部和妹妹住，之後規劃不用算他了。」

Agent step 1 差異偵測：阿公將移除 → 列出差異、問「要更新既有紀錄嗎？(更新／保留舊的)」；「更新」→ 寫回 profiles（成員減為 2 人）；strict 交集重算（阿公 T 標籤移除 → T2/T3 是否保留，視剩餘成員；媽媽無 T → T strict 全除）；本次規劃起份量 = 2。

**範例 11：變更採買地點（改 profiles 的 shopping_region 數據）**

> 使用者：「我們搬來住台北了，之後採買都在台北。」

Agent step 1 差異偵測：`shopping_region` 屏東 → 台北 → 列出差異、問「要更新既有紀錄嗎？(更新／保留舊的)」；「更新」→ 寫回 profiles `shopping_region=台北`；step 2 `fetch_moa.py --market 台北`（對照 `references/shopping-hints/taipei.yaml`：雙連、士林、濱江果菜）；step 4 第 5 區塊改列台北 2–3 市場實測價。

**範例 12：新增自訂市場（改 shopping-hints 的 custom_markets 數據）**

> 使用者：「我們常用的是社區旁的「幸福夜市」，把它加進屏東的採買清單，它只有週末開。」

Agent 讀 `references/shopping-hints/pingtung.yaml`，`custom_markets` 追加：`{ name: 幸福夜市, address: 使用者提供（無則問）, hours: 週五至週日 18:00–23:00, note: 自加市場，無實測價 }`，寫回該 YAML；step 4 第 5 區塊一併列出（標「自加市場，無實測價」）；本次菜單「週六晚餐前可去幸福夜市補鮮蚵」（鮮蚵無每日牌價＝fog，依 v7 票 01 固定估算價）。

**範例 13：新增菜譜（改 references/recipes 數據）**

> 使用者：「教我媽媽拿手的『蝦米蒸蛋』，以後规划到它就要用我的食譜，不是搜尋來的。」

Agent 依 step 3 fallback 鏈：「蝦米蒸蛋」未命中現有菜譜庫 → 依使用者口述/提供之食譜直接寫 `references/recipes/蝦米蒸蛋.yaml`（格式同既有：meta/ingredients/steps/health_flags；stage 非遞減、cooking_time_min＝steps 加總），回寫 `index.yaml`（標「使用者自訂」），並告知「已存庫，日後『蝦米蒸蛋』直接用此版」；本次 menu 若含此菜 → 附製作過程（依新 YAML steps 列）。

**範例 14：修改既有菜譜（改 recipe YAML 的配料／健康標記）**

> 使用者：「台式炒飯以後不要放蝦仁，蝦仁太貴，改成只放肉絲和蛋就好，寫進食譜。」

Agent 讀 `references/recipes/台式炒飯.yaml`，將 `蝦仁` 由配方移除（保留 `豬瘦肉絲`＋`雞蛋`），同步更新：
- `strict_sensitive` 去掉 `allergens:A1`（海鮮）
- `health_flags` 去掉蝦仁對應的 A1 列
- `cooking_time_min` 與 `steps` 不變（蝦仁原 5 分已併入肉絲步驟，不需改分鐘數；若步骤文字提及蝦仁→改寫）
- 回寫 `index.yaml`（sensitive 欄同步去 A1）
- 跑 `sync.sh` 同步三 runtime＋獨立目錄
- 告知「已改，下次規劃台式炒飯不再含蝦仁」

**範例 15：刪除菜譜（移除既有 recipe YAML）**

> 使用者：「蝦卷不要了，以後規劃不要出現蝦卷，把食譜庫裡的蝦卷拿掉。」

Agent 依使用者明確指示：`references/recipes/蝦卷.yaml` 移出 `index.yaml`（index 移除 1 道），YAML 檔保留於 `references/recipes/` 但 index 不列（＝規劃時不命中）；告知「已從 index 移除，檔案保留可隨時恢復」；若使用者要求連檔一起刪 → 刪 YAML 檔＋index，同步三 runtime。

---

## 5. 已知限制（fog）

- **干貝／貝類**無獨立每日牌價來源（v7 票 01 fog 確認）→ 走固定估算價，干貝註記「時價波動大，取保守值」。
- **opendata.vip 未覆蓋之漁類品項**（如秋刀魚在高雄地區無該日數據）→ 標「無牌價（fog）」，fallback 同蔬果三層。
- **>7 日規劃**超出範圍（v6 票 04 決策建議：短期拆兩段各 ≤7 日、中期再考慮趨勢外推）。
- 即時價格推送、地圖整合、GPS 解析 = out of scope。
