# EndNote → Zotero 遷移

把 EndNote 的**文獻、PDF 附件與分組階層**完整搬到 Zotero：**手冊 ＋ 腳本 ＋ AI skill**。

實戰驗證：2,257 筆文獻、30 個 group set / 366 個 group、1,952 個 PDF，分組 100% 重建。

## 👉 先讀這裡

| 你的情況 | 從這開始 | PDF 版 |
|---|---|---|
| **手上有正在寫的 Word 論文稿** | 📄 **[Word 舊稿必讀](docs/01_Word舊稿必讀.md)** ← **最急，先看這個** | [PDF](pdf/01_Word舊稿必讀.pdf) |
| 要搬文獻庫 | 📘 **[遷移手冊](docs/02_遷移手冊.md)** | [PDF](pdf/02_遷移手冊.pdf) |
| 只想要一張紙照著勾 | — | ⭐ **[一頁快查 PDF](pdf/00_一頁快查.pdf)**（剛好 1 頁，印出來貼螢幕旁） |
| 只想拿腳本 | 見下方「腳本」 | — |

> **手冊完全不需要程式基礎**——裡面有純 GUI 的「路徑 B」，只要會用滑鼠就能走完。
> 腳本（路徑 A）是給分組很多、想省時間的人用的加速器，不是必要條件。

> 📌 **Markdown 是正本，PDF 是轉出來的。**
> 內容有更新一律改 `docs/*.md`，再跑 `python tools/build_pdf.py` 重新產生 PDF。
> 不要直接改 PDF。

---

## 為什麼需要這些腳本？

Zotero 匯入 EndNote XML 時，**書目與 PDF 會過去，但分組（Groups）不會**。
官方做法是「逐 Group 匯出成一個 XML 再逐一匯入」——分組數量少時可行，
但幾十上百組時要重複幾十上百次，而且跨組文獻會被重複匯入。

這組腳本改成：**整庫匯出一次 → 從 EndNote 資料庫讀出分組結構 → 在 Zotero 端用腳本重建**。

---

## 先確認你需不需要腳本

| 你的情況 | 建議 |
|---|---|
| 分組不多（< 10 組），或根本沒用分組 | **不需要這些腳本**。直接逐 Group 匯出 XML 再匯入即可 |
| 分組很多，且電腦能裝 Python | 用這組腳本 |
| 分組很多，但不想碰程式 | 逐 Group 匯出仍然可行，只是要重複很多次 |

> ⚠️ 逐 Group 匯出得到的是**單層**平鋪 collection；
> 本腳本重建的是 **group set → group 兩層**結構，與 EndNote 原本一致。

---

## 環境需求

- **Python 3.10 以上**（腳本用到 `dict | None` 型別語法）
- Zotero 7 以上（`Tools → Developer → Run JavaScript` 需存在）
- EndNote X9.3 以上（更早的版本 library 不是 SQLite 格式，本工具讀不到）

不需要安裝任何 Python 套件，全部使用標準庫。

---

## 安全性

**這組腳本不會修改你的 EndNote library。**

| 腳本 | 對 EndNote | 對 Zotero |
|---|---|---|
| `export_endnote_groups.py` | 唯讀開啟（SQLite `mode=ro`，由資料庫層強制） | 不碰 |
| `verify_export_xml.py` | 只讀 XML 與檢查檔案是否存在 | 不碰 |
| `build_collection_plan.py` | 不碰 | 唯讀開啟（`immutable=1`） |
| `rebuild_collections.js` | 不碰 | **新增** collection 並指派文獻；不刪除、不修改文獻內容 |
| `cleanup_endnote_notes.js` | 不碰 | 把匯入殘留 note **移到垃圾桶**（可還原） |
| `rename_attachments.js` | 不碰 | 只改 stored PDF 附件**檔名**；跳過 linked file，衝突時加流水號不覆蓋 |

即使中途出錯，EndNote 原庫都是完好的，可以重來。

---

## 完整流程

### 0. 前置：找出「現役」的 library

⚠️ **電腦上常有多份 EndNote library**（舊備份、不同年份的副本）。
分析錯一份會白做一輪。判別方式：

- 登錄檔 `HKCU\Software\ISI ResearchSoft\EndNote\Recent Libraries`
- 比對各份 `<library>.Data\sdb\sdb.eni` 的修改時間，最新的通常是現役

找到後記下兩個路徑（後面一直會用到）：

```
<library>.Data\sdb\sdb.eni      ← EndNote 資料庫
<library>.Data\                 ← 資料夾本身（底下有 PDF 子資料夾）
```

### 1. 匯出分組快照（EndNote 端，唯讀）

```bash
python scripts/export_endnote_groups.py "<...>.Data\sdb\sdb.eni" snapshot.json
```

會印出筆數、group 數、group set 數。**先核對這些數字跟 EndNote 畫面上看到的一致**，
不一致代表你抓到的是錯的 library，回第 0 步。

> Windows 若中文組名印出來亂碼／報錯，指令前加 `set PYTHONIOENCODING=utf-8`（cmd）
> 或 `$env:PYTHONIOENCODING='utf-8'`（PowerShell）。

### 2. 整庫匯出 XML（EndNote 端，手動）

1. EndNote → 左側點 **All References** → `Ctrl+A` 全選
2. `File → Export…`，Save as type 選 **XML**
3. **儲存位置必須在 `<library>.Data` 資料夾內**

> 🔴 **最容易踩的雷**：XML 存錯位置，匯入後**書目都在但 PDF 全部不見**。
> Zotero 靠 XML 裡的相對路徑找附件，路徑是相對於 `.Data` 資料夾算的。

### 3. 驗證匯出結果

```bash
python scripts/verify_export_xml.py export-all.xml snapshot.json "<...>.Data"
```

三個要看的數字：
- `records in XML` 應接近 `active refs in snapshot`
- `snapshot active ids NOT in XML` 應為 0（或很小）
- `internal-pdf resolved OK` 應接近附件總數，**`missing` 應為 0**

`missing` 不是 0 → XML 存錯位置了，回第 2 步。

### 4. 匯入 Zotero（手動）

1. `Edit → Settings → Sync`，**暫時取消勾選自動同步**
2. `File → Import…` → 選 XML → 勾「Place imported collections and items into new collection」
3. 匯入完成後核對筆數

> 庫很大時 Zotero 可能跑很久。若卡死，回 EndNote 分段選取（每批 500–1000 筆）分次匯出匯入。

### 5. 產生分組重建計畫

**先關閉 Zotero**（腳本以 `immutable=1` 讀 `zotero.sqlite`，開著讀可能拿到不一致的資料）。

```bash
python scripts/build_collection_plan.py snapshot.json "<Zotero資料目錄>\zotero.sqlite" plan.json
```

可選第 4 個參數指定最上層 collection 名稱（預設 `EndNote分組`）：

```bash
python scripts/build_collection_plan.py snapshot.json zotero.sqlite plan.json "我的舊分組"
```

輸出會列出 `unmatched refs`——這些是在 Zotero 找不到對應的文獻（通常是匯入時漏掉或標題差異太大），
數量少可以事後手動處理，數量大代表匯入不完整，先回第 4 步。

### 6. 重建分組（Zotero 端）

1. 開啟 Zotero → `Tools → Developer → Run JavaScript`
2. **勾選「Run as async function」**
3. 打開 `scripts/rebuild_collections.js`，**改第一行 `planPath` 成你的 plan.json 路徑**
4. 全文貼上 → Run

可安全重跑：已存在的 collection 會沿用、已指派的項目會跳過，中斷後直接再跑一次即可。

核對：collection 數量與第 1 步的 group 數一致，抽查幾組成員數。

### 7. 清理

- **合併重複**：安裝 [Zoplicate](https://github.com/ChenglongMa/zoplicate) 外掛批次合併
  （跨組文獻若被重複匯入，合併後 collection 取聯集，分組不會掉）
- **清殘留 note**：Run JavaScript 執行 `scripts/cleanup_endnote_notes.js`
- **統一附件檔名**（選配）：Run JavaScript 執行 `scripts/rename_attachments.js`

### 8. 收尾

- 重新開啟 auto-sync
- 抽查 10–20 筆：PDF 開得起來、分組正確
- **做一份雲端備份**（Google Drive／OneDrive 同步 Zotero 資料目錄）

---

## 常見錯誤

| 症狀 | 原因 | 解法 |
|---|---|---|
| 書目有了但 PDF 全沒跟來 | XML 沒存在 `.Data` 資料夾內 | 刪除該批匯入，把 XML 移進 `.Data` 重新匯入 |
| 分組全部消失 | 這是正常的 | Zotero 匯入不帶分組，要靠第 5–6 步重建 |
| 匯入極慢／卡死 | 一次匯太多 + sync 開著 | 關 sync、分批（500–1000 筆） |
| 多出一堆奇怪的 note | EndNote 不支援欄位被塞成 note | 執行 `cleanup_endnote_notes.js` |
| 中文書目亂碼 | XML 編碼問題 | 確認 EndNote 匯出編碼為 Unicode (UTF-8) |
| Python 印中文報錯 | Windows console 預設 cp950 | 設 `PYTHONIOENCODING=utf-8` |
| 腳本數字跟 EndNote 畫面對不上 | 抓到舊備份 library | 回第 0 步重新確認現役 library |

---

## 用 AI agent 輔助（選配）

repo 內建 agent 指示，**AI 會照本手冊的九步驟帶你走**，每一關數字不對就停下來。

> ⚠️ **需要付費的 Claude 訂閱（Pro/Max）或 API 計費，約 US$20/月。**
> **沒有也完全沒關係**——手冊的每一步都設計成可以自己走完，AI 只是加速，不是必要條件。
> 尤其**路徑 B 完全不需要 AI，也不需要 Python**。

### 三個步驟

**1. 把 repo 下載到本機**

```bash
git clone https://github.com/a0972210123/endnote-to-zotero-migration.git
cd endnote-to-zotero-migration
```

（不會用 git 的話：網頁上點 **Code → Download ZIP**，解壓縮後進到那個資料夾。）

**2. 在「這個資料夾裡面」啟動你的 AI**

```bash
claude      # Claude Code
codex       # Codex
```

> 🔴 **一定要在 repo 資料夾裡面啟動**，AI 才讀得到指示檔。
> 在別的地方啟動，它不會知道要照這套流程走。

| 工具 | 讀哪個檔 | 需要設定嗎 |
|---|---|---|
| **Claude Code** | `.claude/skills/endnote-to-zotero/SKILL.md` | 不用，自動載入 |
| **Codex** | `AGENTS.md` | 不用，自動載入 |
| 其他 AI 工具 | 手動貼 `AGENTS.md` 的內容給它 | 要 |

**3. 貼上開場指令**

### 範例指令

**開場**（直接複製，把數字換成你的）：

```
我要把 EndNote 搬到 Zotero，請照這個 repo 的流程帶我走。
我的 EndNote 大概 2000 筆、100 個分組左右，作業系統是 Windows。
我不太會用命令列，請一步一步來，每一步等我回報再往下。
```

**它會先問你有沒有正在寫的 Word 論文稿**——那題比搬文獻庫更急，先照它說的處理。

**卡住的時候**（把實際訊息貼給它）：

```
我卡在驗證那步，跑出來是 missing: 1952，這是什麼意思？要怎麼修？
```

**看不懂的時候**（隨時可以問，不要硬做）：

```
你剛剛那步在做什麼？為什麼要先關掉 Zotero？
```

**中斷後回來**：

```
我昨天做到匯入完成，snapshot.json 和 plan.json 都還在，接下來要做什麼？
```

### 用 AI 的三個提醒

1. **AI 也會出錯。** 它每一步都會請你確認——**看不懂就問「這步在做什麼」，不要因為是 AI 說的就直接按下去。**
2. **它不會碰你的 EndNote 原庫。** 腳本對 EndNote 是資料庫層強制唯讀，就算 AI 想寫也寫不進去。
3. **數字不對它應該要停。** 如果它在數字對不上時還說「沒關係我們繼續」，**那是錯的，請它停下來重查**。

---

## 維護：更新文件後重新產生 PDF

**Markdown 是正本。** 改完 `docs/*.md` 之後：

```bash
pip install markdown          # 只需第一次
python tools/build_pdf.py
```

會重新產生 `pdf/` 底下三份：一頁快查、Word 舊稿必讀、遷移手冊。
用 Chrome（或 Edge）headless 列印，中文走系統的微軟正黑體，不必額外裝字型。

> 「一頁快查」是從手冊中自動抽出來的（抓 `# 📄 一頁快查` 到 `# 第 0 章` 之間）。
> 改動手冊的章節標題時要留意這個對應關係。

---

## 授權與免責

MIT License — 詳見 [LICENSE](LICENSE)。作者：Ching-Wei Ye（葉淨維）。

使用前請自行備份 EndNote library 與 Zotero 資料目錄。
腳本雖然對 EndNote 是唯讀、對 Zotero 只做新增與可還原操作，但**資料遷移一律先備份**。
