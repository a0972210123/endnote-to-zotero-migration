// 清理 EndNote 匯入殘留的 note
// 用法:Zotero → Tools → Developer → Run JavaScript(勾「Run as async function」)→ 貼上 → Run
//
// 背景:EndNote XML 裡有些欄位 Zotero 沒有對應位置,匯入時會被塞成一則 note 掛在文獻底下,
//      並統一帶 tag「_EndnoteXML import」。數量多時會明顯拖慢 Zotero,建議清掉。
//
// 安全:只把這些 note「移到垃圾桶」,不是永久刪除。
//      確認沒問題後再自行清空垃圾桶;發現誤刪可從垃圾桶還原。
//      不會動到任何文獻本體、附件或你自己寫的筆記(只認這個 tag)。

var libraryID = Zotero.Libraries.userLibraryID;

var s = new Zotero.Search();
s.libraryID = libraryID;
s.addCondition('itemType', 'is', 'note');
s.addCondition('tag', 'is', '_EndnoteXML import');
var noteIDs = await s.search();

if (!noteIDs.length) {
    return 'ℹ️ 沒有找到帶「_EndnoteXML import」tag 的 note,不需要清理。';
}

await Zotero.Items.trashTx(noteIDs);
return '✅ 已把 ' + noteIDs.length + ' 個 EndNote 匯入殘留 note 移到垃圾桶。\n'
     + '請到左側「垃圾桶」抽查確認都是不需要的,再清空垃圾桶。';
