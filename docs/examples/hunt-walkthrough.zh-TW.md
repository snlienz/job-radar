# 範例：第一次執行 `/hunt`

這是一次真實 session 的去敏版本，讓你知道第一次使用時要輸入什麼、`/hunt` 會做什麼、會看到什麼結果。English version: [hunt-walkthrough.md](hunt-walkthrough.md)

**去敏說明：** 候選人、其雇主、徵才公司、職缺 ID 與所有關於候選人的數字都是虛構的。流程取自真實的 104 職缺，但公司名稱已換成虛構名稱。分數、面試機率與薪資數字僅為示意。

**起始狀態：** 已經 clone 的 repo、已用 `/scan` 建好 `data/master.yaml`、`config/profile.yaml` 的 `keywords.include` 是空的、沒有 `config/private.yaml`。

---

## 1. 啟動

**你輸入**

```
/hunt https://www.104.com.tw/jobs/search/?keyword=senior+embedded+software&area=6001001000
```

你也可以只輸入 `/hunt`（從目前進度繼續）或 `/hunt search`（直接開新搜尋）。`/hunt` 只接受 `search` 和 `key=value` 覆蓋參數，所以搜尋網址不會直接被當成搜尋條件，請把它當成關鍵字的提示。

**發生什麼事（步驟 0：環境檢查）**
- `config/profile.yaml` 存在、`data/master.yaml` 存在。
- `keywords.include` 是空的，所以 `/hunt` 會停下來問你要搜尋哪些關鍵字。你在對話中回答；選「寫入 profile」下次就不用再問。
- 它會提醒（不會中斷）：缺少 `config/private.yaml`（無法跟你目前的薪資比較），以及 104 需要 Claude in Chrome。

> 提示：include 關鍵字是以整個詞組去比對職稱或 JD，所以 `senior embedded software` 幾乎什麼都留不下。用單字（`embedded`、`firmware`）效果比較好。`/search` 可以單次覆蓋：`keywords=embedded,firmware,driver,linux`。

## 2. 搜尋

`stages` 顯示目前沒有任何待處理的職缺（沒有 tailored、research、decide、new），所以 `/hunt` 進入步驟 5，執行 `/search`。

1. 用腳本抓 104 被拒絕（`BLOCKED ... HTTP 403`）。這很正常，104 常擋腳本。`/hunt` 不會硬繞過，而是改用你的 Chrome（Claude in Chrome）。如果擴充功能沒連上，它會停下來告訴你要檢查什麼；修好之後輸入 `try again` 即可。
2. 在 Chrome 中讀取結果頁，再逐一讀取看起來與嵌入式相關職缺的 JD。
3. 硬篩選：進來 12 筆、剩 11 筆候選（1 筆沒有 include 關鍵字）。
4. 每個候選依你的 Master Resume 評 0-100 分。達 60 分以上的（這次是 7 筆）會寫成 `jobs/<公司>-<id>.md`，並重建 `jobs/INDEX.md`。

## 3. Fit Gate（由你決定）

**你會看到** 一張依分數由高到低排序的表：

| # | 分數 | 面試機率 | 公司 | 職稱 | 摘要 | 最大缺口 |
|---|---|---|---|---|---|---|
| 1 | 80 | 55-65% | Nimbus Cloud | Senior Embedded Software Engineer | 韌體、RTOS、Linux、C/C++，符合候選人的韌體與嵌入式 Linux 背景 | 沒有交換器／路由協定經驗；貼文已 5 個月 |
| 2 | 76 | 55-65% | Lumen Devices | Embedded Software Engineer | 相機影像韌體，使用 C++ 與嵌入式 Linux | 職缺定位 3-4 年：資歷過高 |
| 3 | 72 | 45-55% | Roboto Robotics | Senior Firmware & Embedded Engineer | 機器人韌體、即時系統、視覺感測器 | 沒有控制迴圈或機器人經驗 |
| ... | | | | | | |
| 6 | 64 | 35-45% | Mega Electronics | Embedded Systems Integration Engineer | 感測器韌體設定、UART/I2C/SPI 除錯 | 沒有 PID/EKF 調校 |

**你輸入** 編號來加入 shortlist：

```
把 1 加入
```

`/hunt` 會把該職缺設為 `shortlisted`（`python scripts/search_jobs.py status <key> shortlisted`），接著進入研究。沒選的職缺維持 `new`，下次還會出現。說「其他都不要」會把其餘的設為 `ignored`。

## 4. 研究（對 shortlisted 職缺自動執行）

`/research` 會在 `companies/<slug>.md` 寫出公司檔案（Company Profile），並在職缺檔加入 `## Company` 區塊、`[company]` 風險、薪資與部門傳聞。

對於很小的公司，網路上幾乎沒有公開資料，檔案會誠實寫出「不明」而不是亂猜：

- 趨勢：`unknown`（查不到營收、募資或裁員新聞；104 上約 22 人）
- 文化五個面向全部是 `不明`
- 薪資：沒有工程職回報（n=0）
- 新增風險：`[company] 只有約 22 人，穩定度無法判斷`

## 5. Company Gate（由你決定）

**你會看到** 每個研究完的職缺一列：分數、機率、公司、職稱、趨勢、職位薪資、每個文化面向一行、部門傳聞與 `[company]` 風險。接著你對每個職缺選擇：`/tailor`、丟掉（`ignored`）、或先放著。

你也可以隨時用 Fit Gate 表上的編號指定某個職缺：

```
幫我對 6 做評估
```

這會把它加入 shortlist 並跑同樣的研究。大公司的資料會完整許多：

- 趨勢：**成長**（最近一個月營收年增 51%，附來源與日期）
- 工時：混合，上班時間彈性，部分團隊被回報週末加班
- 主管：混合。升遷：負面（GoodJob 2.5/5）。彈性：正面。福利：正面。
- 薪資：公司層級的工程職回報，約 NT$95-120 萬／年（n=4，標示「僅供參考」）
- 部門傳聞：機器人中心 `查無資料`

## 6. 客製化履歷（Tailor）

**你輸入**

```
/tailor 6
```

（打錯成 `/trailor` 並不是指令。助理會先問你是不是要用 `/tailor`，確認後才會執行。）

`/tailor` 會產生 `output/<公司>-<id>/`：

| 檔案 | 內容 |
|---|---|
| `resume.docx`、`resume.pdf` | 英文客製化履歷（PDF 需要 Word） |
| `tailored.yaml` | 履歷背後的資料；每個 bullet 都指向 Master Resume 的一筆 Achievement `id` |
| `changes.md` | 選了什麼、改寫了什麼、丟掉什麼，以及**缺口** |

驗證器會檢查沒有編造內容：所有 Highlight 成就都在、職稱與日期沒被改、沒有出現 Master Resume 以外的技能。完成後職缺會被設為 `tailored`。

**請你親自檢查：** 摘要（唯一全新寫的文字）與被改寫的 bullet。最有用的是缺口清單：職缺要求、但你的 Master Resume 沒辦法支撐的項目。透過 `/scan`（Gap Interview）補上真實經驗，下一份履歷就會更好。

## 7. 本次結尾

`/hunt` 結尾會報告改了什麼，以及下次 `/hunt` 會先做什麼。這次 session 是：

- 狀態變更：1 個職缺 `shortlisted` 並完成研究，1 個職缺 `shortlisted` 後變 `tailored`
- 研究的公司：2 家（`companies/` 新增檔案）
- 產生的履歷：1 份
- 下次 `/hunt`：先問你有沒有投遞那份已客製化的職缺，再回到 Company Gate 處理另一個 shortlisted 職缺，最後是仍在 Fit Gate 等待的 5 個 `new` 職缺。

---

## 這次出過的狀況與原因

| 你看到的 | 原因 | 怎麼處理 |
|---|---|---|
| `ModuleNotFoundError: yaml`（或 `httpx`、`lxml`、`jsonschema`、`docxtpl`） | 使用的 Python 環境不是裝好專案的那個 | 啟動 `.venv`，並在開 Claude Code 前先執行 `pip install -e ".[dev]"` |
| `BLOCKED 104 ... 403` | 104 拒絕腳本存取 | 安裝 Claude in Chrome、用同一個 Claude 帳號登入、重啟 Chrome，再輸入 `try again` |
| 「Browser extension is not connected」 | 擴充功能沒執行或沒登入 | 同上；或直接把職缺文字貼到對話中 |
| 幾乎沒有職缺通過篩選 | include 關鍵字是一整句話 | 改用單字：`keywords=embedded,firmware` |
| Windows 主控台中的中文檔名亂碼 | 只是主控台的字碼頁問題 | 檔案本身沒問題（UTF-8）；設定 `PYTHONIOENCODING=utf-8` 就能在主控台正常顯示 |
| 缺少 `config/private.yaml` | 尚未建立 | 想比較自己的薪資時，複製 `config/private.example.yaml`；此檔不會被 git 追蹤 |

## 你的資料放在哪裡

`data/`、`jobs/`、`companies/`、`output/` 以及 `config/profile.yaml`、`config/private.yaml` 都在 gitignore 內。這次 session 沒有任何東西被 commit，你的履歷、薪資與研究都只留在你的電腦上。
