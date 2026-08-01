// 批次改名:所有 PDF 附件檔名 → 依 Zotero 檔名模板(預設:作者 - 年 - 標題)
// 背景:Zotero 8 起移除了右鍵選單的「Rename File from Parent Metadata」,
//       批次改名改用腳本呼叫同一套內建 API。
// 用法:Tools → Developer → Run JavaScript(勾 Run as async function)→ 貼上 → Run
// 安全:只動「stored」的 PDF 附件;linked file、快照、網頁連結一律跳過。
//       檔名衝突時自動加流水號,不會覆蓋檔案。

var lib = Zotero.Libraries.userLibraryID;
var topItems = await Zotero.Items.getAll(lib, true, false);
var renamed = 0, skipped = 0, noFile = 0;
var errors = [];

for (let item of topItems) {
    if (!item.isRegularItem()) continue;
    for (let attID of item.getAttachments()) {
        let att = Zotero.Items.get(attID);
        try {
            if (!att.isStoredFileAttachment()) { skipped++; continue; }
            if (att.attachmentContentType != 'application/pdf') { skipped++; continue; }
            let path = await att.getFilePathAsync();
            if (!path) { noFile++; continue; }
            let oldName = PathUtils.filename(path);
            let dot = oldName.lastIndexOf('.');
            let ext = dot > -1 ? oldName.slice(dot) : '';
            let base = Zotero.Attachments.getFileBaseNameFromItem(item);
            let newName = base + ext;
            if (oldName == newName) { skipped++; continue; }
            await att.renameAttachmentFile(newName, false, true);
            renamed++;
        } catch (e) {
            errors.push('att ' + att.id + ': ' + e.message);
        }
    }
}

return (errors.length ? '⚠️ 部分失敗\n' : '✅ 完成\n')
    + '已改名: ' + renamed + '\n'
    + '跳過(非stored PDF/已符合): ' + skipped + '\n'
    + '找不到檔案: ' + noFile + '\n'
    + (errors.length ? '\n錯誤(' + errors.length + ',僅列前10):\n' + errors.slice(0, 10).join('\n') : '');
