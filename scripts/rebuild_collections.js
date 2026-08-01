// EndNote 分組重建腳本 v2(可續跑)
// 用法:Zotero → Tools → Developer → Run JavaScript
//      勾選「Run as async function」→ 貼上全文 → Run
// v2 變更:
//  - 指派改用 item.addToCollection + item.save(相容性最好的寫法)
//  - find-or-create:已存在的 collection 直接沿用,已指派的項目跳過 → 中斷後直接重跑即可
//  - 每個 group 獨立 try/catch,單點失敗不會中斷全部,結尾回報錯誤清單
//
// ⚠️ 這支腳本會「新增」collection 並把文獻指派進去,不會刪除或修改任何文獻內容。
//    可安全重跑:已存在的 collection 沿用、已指派的項目跳過。

// ⬇️⬇️ 唯一需要你修改的一行:改成 build_collection_plan.py 產出的 plan 檔路徑
//       Windows 路徑的反斜線要寫成兩個(例:'D:\\migration\\plan.json')
var planPath = 'C:\\請改成你的路徑\\zotero-collection-plan.json';
var plan = JSON.parse(await Zotero.File.getContentsAsync(planPath));
var libraryID = Zotero.Libraries.userLibraryID;

function findChild(name, parentID) {
    return Zotero.Collections.getByLibrary(libraryID).find(c =>
        c.name == name && (parentID ? c.parentID == parentID : !c.parentID)
    );
}

async function findOrCreate(name, parentID) {
    var c = findChild(name, parentID);
    if (c) return c;
    c = new Zotero.Collection();
    c.libraryID = libraryID;
    c.name = name;
    if (parentID) c.parentID = parentID;
    await c.saveTx();
    return c;
}

var root = await findOrCreate(plan.root, null);
var nGroups = 0, nAssigned = 0, nSkipped = 0;
var missingKeys = [], errors = [];

for (let set of plan.sets) {
    let setCol = await findOrCreate(set.name, root.id);
    for (let g of set.groups) {
        try {
            let gCol = await findOrCreate(g.name, setCol.id);
            nGroups++;
            let toAdd = [];
            for (let key of g.itemKeys) {
                let item = Zotero.Items.getByLibraryAndKey(libraryID, key);
                if (!item) { missingKeys.push(key); continue; }
                if (gCol.hasItem(item)) { nSkipped++; continue; }
                toAdd.push(item);
            }
            if (toAdd.length) {
                await Zotero.DB.executeTransaction(async function () {
                    for (let item of toAdd) {
                        item.addToCollection(gCol.id);
                        await item.save();
                    }
                });
                nAssigned += toAdd.length;
            }
        } catch (e) {
            errors.push(set.name + ' / ' + g.name + ' → ' + e.message);
        }
    }
}

return (errors.length ? '⚠️ 部分失敗\n' : '✅ 完成\n')
    + 'group sets: ' + plan.sets.length + '\n'
    + 'groups 處理: ' + nGroups + '\n'
    + '本次新指派: ' + nAssigned + '(已存在跳過: ' + nSkipped + ')\n'
    + '找不到的 item key: ' + missingKeys.length + '\n'
    + (errors.length ? '\n錯誤(' + errors.length + '):\n' + errors.join('\n') : '');
