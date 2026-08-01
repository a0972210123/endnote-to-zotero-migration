"""Match EndNote group members to imported Zotero items and emit a collection plan.

Matching: normalized title, with year as tie-breaker when several distinct
works share a title. Duplicate imports of the same work all get assigned
(later duplicate-merge unions collections, so the end state is correct).

Usage: python build_collection_plan.py <snapshot.json> <zotero.sqlite> <plan.json> [root-name]

`root-name` is the top-level Zotero collection the rebuilt group tree hangs
under; defaults to ROOT_NAME below.

Read-only: zotero.sqlite is opened with immutable=1. Close Zotero before
running -- immutable assumes the file does not change while it is read.
"""
import json
import re
import sqlite3
import sys
import unicodedata

ROOT_NAME = "EndNote分組"
UNGROUPED_SET = "(未分組)"


def norm_title(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t or "")          # strip style/html tags
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"[^0-9a-z一-鿿぀-ヿ]+", "", t)
    return t


def load_zotero_items(db_path: str) -> list[dict]:
    con = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    rows = con.execute("""
        SELECT i.itemID, i.key, idv.value AS title,
               (SELECT idv2.value FROM itemData id2
                JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
                JOIN fields f2 ON id2.fieldID = f2.fieldID
                WHERE id2.itemID = i.itemID AND f2.fieldName = 'date') AS date
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemData id ON id.itemID = i.itemID
        JOIN fields f ON id.fieldID = f.fieldID
             AND f.fieldName IN ('title', 'caseName', 'subject', 'nameOfAct')
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE it.typeName NOT IN ('attachment', 'note', 'annotation')
          AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
    """).fetchall()
    items = []
    for item_id, key, title, date in rows:
        m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", date or "")
        items.append({
            "id": item_id, "key": key, "title": title,
            "norm": norm_title(title), "year": m.group(1) if m else "",
        })
    return items


def main(snapshot_path: str, db_path: str, out_path: str,
         root_name: str = ROOT_NAME) -> None:
    snap = json.load(open(snapshot_path, encoding="utf-8"))
    items = load_zotero_items(db_path)

    by_norm: dict[str, list[dict]] = {}
    for it in items:
        by_norm.setdefault(it["norm"], []).append(it)

    def match_ref(ref: dict) -> list[str]:
        cands = by_norm.get(norm_title(ref["title"]), [])
        if not cands:
            return []
        year = (ref["year"] or "").strip()
        if year and len({c["year"] for c in cands}) > 1:
            year_hits = [c for c in cands if c["year"] == year]
            if year_hits:
                cands = year_hits
        return [c["key"] for c in cands]

    refs = {int(k): v for k, v in snap["refs"].items()}
    unmatched = []
    ref_keys: dict[int, list[str]] = {}
    for rid, ref in refs.items():
        if ref["in_trash"]:
            continue
        keys = match_ref(ref)
        ref_keys[rid] = keys
        if not keys:
            unmatched.append({"ref_id": rid, "title": ref["title"],
                              "year": ref["year"], "author": ref["first_author"]})

    groups = snap["groups"]

    def group_entry(uuid: str) -> dict | None:
        g = groups.get(uuid)
        if g is None or not g["is_custom"]:
            return None
        keys = sorted({k for rid in g["member_ref_ids"] for k in ref_keys.get(rid, [])})
        skipped = sum(1 for rid in g["member_ref_ids"]
                      if rid in refs and refs[rid]["in_trash"])
        return {"name": g["name"], "itemKeys": keys,
                "endnoteMembers": len(g["member_ref_ids"]),
                "trashMembers": skipped}

    plan_sets = []
    for gs in snap["groupsets"]:
        entries = [e for u in gs["group_uuids"] if (e := group_entry(u))]
        if entries:
            plan_sets.append({"name": gs["name"], "groups": entries})

    orphan_entries = [e for u in snap["orphan_group_uuids"] if (e := group_entry(u))]
    if orphan_entries:
        plan_sets.append({"name": UNGROUPED_SET, "groups": orphan_entries})

    plan = {"root": root_name, "sets": plan_sets, "unmatched": unmatched}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)

    n_groups = sum(len(s["groups"]) for s in plan_sets)
    n_assign = sum(len(g["itemKeys"]) for s in plan_sets for g in s["groups"])
    print(f"sets: {len(plan_sets)}  groups: {n_groups}  assignments: {n_assign}")
    print(f"unmatched refs (in no collection): {len(unmatched)}")
    for u in unmatched[:10]:
        print(f"  [{u['ref_id']}] {u['author']} ({u['year']}) {u['title'][:60]}")


if __name__ == "__main__":
    if not 4 <= len(sys.argv) <= 5:
        sys.exit(__doc__)
    main(*sys.argv[1:5])
