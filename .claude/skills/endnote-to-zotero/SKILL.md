---
name: endnote-to-zotero
description: Migrate an EndNote library to Zotero with PDFs and group hierarchy intact. Use when the user wants to move, migrate, transfer, or import their EndNote library into Zotero, mentions EndNote 搬到 Zotero / 遷移 / 轉移, asks about exporting EndNote XML, rebuilding EndNote groups as Zotero collections, or is dealing with an EndNote licence expiry.
---

# EndNote → Zotero 遷移

引導使用者把 EndNote library（文獻、PDF 附件、分組階層）完整搬到 Zotero。

**使用者多半不是工程背景，而且這是他們累積多年的文獻資產。**
說明用白話，每一步講清楚「現在要做什麼、為什麼、會發生什麼」。

---

## 🔴 安全不變量（任何情況都不得違反）

1. **EndNote 原庫只讀不寫。** 絕不修改、移動、刪除 `.enl` 或 `.Data` 內的任何既有檔案。
   唯一允許的寫入是「使用者自己在 EndNote 裡匯出的 XML 存進 `.Data`」——那是他手動做的。
2. **偵測，不要猜。** 路徑一律實際查證後再用。**絕不假設** library 在 `D:\` 或任何預設位置。
3. **找到多份 library 就停下來問人。** 不要自己挑「看起來最新的那個」。
   （這是原作者踩過的雷：分析到舊備份，白做一整輪。）
4. **每個破壞性動作前要人確認**：合併重複、刪 note、批次改名。
5. **驗收看數字，不看腳本說「成功」。** 每個關卡都要跟使用者記下的 EndNote 原始數字核對。
6. **不確定就停。** 寧可多問一句，不要弄壞使用者的文獻庫。

---

## 開場先做兩件事

### 1. 先問 Word 舊稿

> 「你手上有正在寫、11 月之後還要繼續改的 Word 論文稿嗎？」

**有** → 這件事比搬文獻庫更急，先處理。授權到期後 CWYW 失效，已插入的引用無法再重新格式化。
請他先看《Word 舊稿必讀》那份通知，或引導他做三選一決策（定稿在即／轉純文字／改用 Zotero 重插）。
**處理完再回來搬文獻庫。**

**沒有** → 繼續。

### 2. 確認前置

**這五項全部在開場就問完。** 目的是把「會讓流程中途死掉」的條件提前暴露——
底下第 3、4 項若不合格，是走到步驟 3 和步驟 7 才會炸，那時已經匯入好幾千筆了。

| # | 檢查 | 怎麼問／怎麼查 | 不合格怎麼辦 |
|---|---|---|---|
| 1 | **作業系統** | 直接問，或看環境 | **Mac → 可以走**，但指令不同，見下方「macOS」節 |
| 2 | **Python 3.8+** | Windows `python --version`／Mac `python3 --version` | **明確說「你走純 GUI 的路徑 B」**，轉手冊第 5 章。**不強推安裝** |
| 3 | **EndNote 版本 ≥ X9.3** | 請他開 EndNote 看 `Help → About`；或直接確認 `<library>.Data\sdb\sdb.eni` 這個檔案存在 | 更舊的版本 library 不是 SQLite，腳本讀不到 → **只能走路徑 B** |
| 4 | **Zotero 版本 ≥ 7** | 請他確認選單有 `Tools → Developer → Run JavaScript` | **沒有這個選單 → 請他先更新 Zotero**。路徑 A 的第 7 步完全靠它，沒有就做不了分組重建 |
| 5 | **Zotero 已安裝並登入** | 問 | 先去 zotero.org 註冊 |
| 6 | 🔴 **library 是否在雲端同步資料夾內** | 找到路徑後檢查有無 `OneDrive`／`Dropbox`／`Google Drive`／`SharePoint`／`iCloud` | **停下來先處理**，見下方「雲端同步」節 |
| 7 | **Zotero 是空的還是已有內容** | 請他看 My Library 目前幾筆 | 非空 → 後續核對筆數要用**差值**，見下方 |

> 🔴 **第 3、4 項務必在開場就確認，不要等腳本報錯才發現。**
> 這兩項不合格時，使用者仍然可以完整走完路徑 B——**要主動這樣講**，
> 不要讓他以為自己沒救了。

### 🔴 雲端同步資料夾（第 6 項）

**Clarivate 官方明確表示 EndNote 不相容於雲端同步服務**，直接從同步資料夾開啟
library 可能造成**損毀**（EndNote 存檔要依序寫多個檔案，任一個正在同步就會寫失敗）。

⚠️ **很多人不知道自己中招**：不少機構的 OneDrive 會自動接管「文件」資料夾，
而 EndNote 預設就存在那裡。**一定要實際看路徑，不要問「你有放雲端嗎」**——他多半不知道。

**發現在同步資料夾內時，引導他二選一：**

1. **複製整組（`.enl` ＋ `.Data`）到非同步位置再操作**（推薦；原本那份等於自動備份）
2. 暫停同步，做完再恢復

**選 1 之後，全程改用複本的路徑。** 要主動提醒這件事，不要一半用複本一半用原檔。

### Zotero 已有既存內容（第 7 項）

**非空庫的兩個影響，要主動說明：**

1. **核對筆數要用差值**：匯入後總數 = 他原有筆數 + EndNote 筆數。
   **後面每一個 🚦 關卡的筆數核對都要記得加上他原有的數字**，否則會誤判成匯入失敗。
2. **分組重建可能連他原有的文獻一起指派**：`build_collection_plan.py` 用標題比對，
   同一篇論文若原本 Zotero 就有，兩筆都會被放進對應分組。
   **這是預期行為不是錯誤**，第 8 章合併重複時會處理掉。事先講，不要讓他嚇到。

**同時主動安撫**：整個流程不會修改他的 EndNote library，腳本對 EndNote 是
SQLite 資料庫層強制唯讀（`mode=ro`），就算有 bug 也寫不進去。出錯就重來，原庫完好。

### macOS 使用者

**路徑 A 在 Mac 上可行**——EndNote library 格式跨平台相同（`.Data/sdb/sdb.eni` 一樣是 SQLite），
Python 腳本只讀 SQLite 與 XML，沒有任何 Windows 專屬呼叫。**差異只在指令怎麼打。**

| 項目 | Windows | macOS |
|---|---|---|
| 命令列 | PowerShell | 終端機 Terminal.app |
| Python 指令 | `python` | **`python3`** |
| 中文編碼 | 需 `PYTHONIOENCODING=utf-8` | **不需要**（預設 UTF-8） |
| 找現役 library | 登錄檔 `HKCU\...` | **`find ~ -name "sdb.eni" 2>/dev/null`** 或看 EndNote 標題列 |
| 路徑分隔 | `\` | `/` |
| 幫他取得路徑 | Shift+右鍵「複製路徑」 | **請他把檔案拖進終端機視窗**（自動輸出完整路徑） |
| Zotero 資料目錄 | `C:\Users\<name>\Zotero` | `~/Zotero` |
| `planPath` 寫法 | 反斜線加倍 `'D:\\x\\plan.json'` | **不用加倍** `'/Users/name/plan.json'` |

> ⚠️ **誠實告知使用者**：完整流程只在 Windows 上跑過 2,257 筆的實庫，
> **Mac 尚未有人從頭到尾實測**。原理上沒有障礙，但他可能是第一個。
> **請他先完整備份**，並在卡住時回報——那是要修文件的地方。
>
> **不要假裝已經測過。** 也不要因此就把他推去路徑 B——
> 條件符合的話路徑 A 仍然是比較好的選擇（兩層分組、不重複匯入）。

---

## 九個步驟

### 步驟 1：找出現役 library ⚠️ 最容易錯

**不要猜。** 依序嘗試：

**Windows**
1. 查登錄檔最近開啟紀錄：
   ```
   HKCU\Software\ISI ResearchSoft\EndNote\Recent Libraries
   ```
2. 搜尋磁碟上的 `*.Data\sdb\sdb.eni`，列出**全部**候選並比對修改時間

**macOS**
1. ```bash
   find ~ -name "sdb.eni" 2>/dev/null
   ```
2. 比對各候選的修改時間（`ls -l`）

**兩者共同**
3. 請使用者開啟 EndNote 看視窗標題列，確認檔名——**這招最可靠且跨平台**

**找到多份時：把清單（路徑＋修改時間＋大小）攤給使用者，請他確認哪一份是現役的。**

確認後記下並全程使用：
- `<library>.Data\sdb\sdb.eni`
- `<library>.Data\`（資料夾本身）

### 步驟 2：請使用者記下基準數字

請他在 EndNote 裡看並告訴你：
- 總筆數
- Group 數量（與清單）
- `.Data` 資料夾大小

**這三個數字是後面每一關的驗收依據。** 沒有就沒辦法確認搬完整。

順便確認目標硬碟剩餘空間 > `.Data` 大小 × 2。

### 步驟 3：分組快照

```bash
python scripts/export_endnote_groups.py "<sdb.eni 路徑>" snapshot.json    # Windows
python3 scripts/export_endnote_groups.py "<sdb.eni 路徑>" snapshot.json   # macOS
```

Windows 中文亂碼 → 加 `PYTHONIOENCODING=utf-8`。**Mac 不需要。**

**🚦 關卡**：印出的筆數／group 數**必須**與步驟 2 的數字相符。
不符 → 抓錯 library，回步驟 1。**不要繼續。**

### 步驟 4：使用者手動匯出 XML

這步你做不到，要引導他做。**講清楚兩個重點**：

- **格式選 XML**（不是 RIS——RIS 不帶 PDF、不帶分組）
- **🔴 必須存進 `<library>.Data\` 資料夾內**
  （XML 裡的附件路徑是相對於 `.Data` 算的；存錯位置＝書目都在但 PDF 全部不見）
- Text Encoding 選 Unicode (UTF-8)

步驟：EndNote → All References → `Ctrl+A` → `File → Export…` → XML → 存進 `.Data`

### 步驟 5：驗證匯出

```bash
python scripts/verify_export_xml.py "<export.xml>" snapshot.json "<.Data 路徑>"
```

**🚦 關卡**（三個都要過）：
- `records in XML` ≈ `active refs in snapshot`
- `snapshot active ids NOT in XML` = 0 或極小
- **`missing` = 0**

`missing` 不是 0 → XML 存錯位置。請他移進 `.Data` 重新匯出。**不要繼續。**

> **看到 `attachment links: 0 total`**：代表他的 EndNote 沒有 PDF 附件——**不是錯誤**。
> 只用 EndNote 管書目的人很常見。主動說明並讓他往下走，不要讓他以為失敗了。
> 但如果他說「我明明有附件」，那就是匯出沒帶到，或那些是 EndNote 的
> **linked file（檔案連結）而非內嵌 PDF**——後者不會跟著 XML 走，要另外手動處理。

### 步驟 6：使用者手動匯入 Zotero

引導他做：

1. **`Edit → Settings → Sync` → 取消勾選自動同步** 🔴
2. `File → Import…` → 選 XML
3. 勾「Place imported collections and items into new collection」
4. 等完成（大庫可能數小時，提醒他讓它跑完）

**🚦 關卡**：匯入後總筆數與步驟 2 相符。

> 匯入後分組不見是**正常的**，主動說明，不要讓他以為失敗了。

### 步驟 7：重建分組

**先請他關閉 Zotero**（腳本要讀 `zotero.sqlite`，開著讀可能拿到不一致的資料）。

Zotero 資料目錄：`Edit → Settings → Advanced → Files and Folders`（**問他，不要猜**）

```bash
python scripts/build_collection_plan.py snapshot.json "<zotero.sqlite>" plan.json
```

看 `unmatched refs`：個位數正常；很多 → 匯入不完整，回步驟 6。

然後引導他：
1. 開 Zotero → `Tools → Developer → Run JavaScript`
2. **勾「Run as async function」**（沒勾會報錯）
3. 把 `scripts/rebuild_collections.js` 的 `planPath` 改成他的 plan.json 路徑
   （**Windows 反斜線要打兩個**；**Mac 用正斜線、不用加倍**）
4. 貼上 → Run

**可安全重跑**——中斷了直接再跑一次，已建的沿用、已指派的跳過。

**🚦 關卡**：collection 數與步驟 3 的 group 數相符，抽查 3–5 組成員數合理。

### 步驟 8：清理（每項都要先問過）

- **合併重複**：請他用 Zoplicate 外掛。合併後 collection 取聯集，分組不會掉
- **清殘留 note**：`scripts/cleanup_endnote_notes.js`（只移到垃圾桶，可還原）
  → **執行前告訴他會影響幾筆**，執行後請他抽查垃圾桶再清空
- **統一 PDF 檔名**（選配）：`scripts/rename_attachments.js`
  → 這會改動檔名，**明確問過再跑**

### 步驟 9：收尾

- 重開 auto-sync
- **抽查 10–20 筆 PDF 打得開**（請他實際點開，不要只看有沒有附件圖示）
- 引導做 Google Drive 備份，**並提醒回網頁端核對大小**（上傳中 ≠ 完成）
- **EndNote 原庫先別刪**，留到確認一切正常

---

## 環境差異處理

| 狀況 | 怎麼辦 |
|---|---|
| 沒有 Python | 明講「你走路徑 B（純 GUI）」，轉手冊第 5 章，不強推安裝 |
| Windows 命令列中文報錯 | `PYTHONIOENCODING=utf-8` |
| EndNote 不在 D 槽 | 全部路徑用偵測結果，不假設槽別 |
| 庫很大（>3000 筆 / >5GB） | 提醒分批匯入、時間會很久、排在不用電腦的時段 |
| EndNote 版本太舊（< X9.3） | library 不是 SQLite 格式，腳本讀不到 → 只能走路徑 B |
| Zotero 沒有 `Run JavaScript` 選單 | 版本太舊（需 7 以上）→ 請他先更新，否則路徑 A 第 7 步做不了 |
| macOS | **路徑 A 可行**，指令改用 `python3`／正斜線／不需 PYTHONIOENCODING，見開場的「macOS 使用者」節 |
| EndNote 雲端／線上版（EndNote Web） | 本流程針對桌面版的本機 library；請他先在桌面版開啟並同步下來 |

---

## 語氣

- **先安心再操作**：多數人最怕「弄壞我的文獻庫」。主動說明 EndNote 原庫不會被動到。
- **一次講一步**，等他做完回報再往下。不要一口氣丟九個步驟。
- **關卡不過就停**，說明哪個數字不對、可能原因、下一步怎麼查。不要為了往前而略過驗證。
- 他說「看不懂」時，換更白話的講法，不要重複同一段。
