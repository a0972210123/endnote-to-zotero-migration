"""Extract EndNote group structure from sdb.eni (read-only) into a JSON snapshot.

EndNote (X9.3+) stores its library in SQLite:
  - refs:   one row per reference (id, author, year, title, trash_state, ...)
  - groups: custom/smart groups; `spec` is an XML blob (uuid, name, rules),
            `members` is a binary blob: 4-byte header, then little-endian
            uint32 count, then count x little-endian uint32 ref ids
  - misc (code=17): group sets; XML blob with name + member group uuids

Usage:  python export_endnote_groups.py <path-to-sdb.eni> <output.json>

Runs on Python 3.8+ (the __future__ import keeps the 3.9 annotation syntax
from being evaluated). macOS system python3 is new enough.
"""
from __future__ import annotations

import json
import re
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET


def parse_members_blob(blob: bytes) -> list[int]:
    if not blob or len(blob) < 8:
        return []
    count = struct.unpack_from("<I", blob, 4)[0]
    expected = 8 + count * 4
    if len(blob) < expected:
        raise ValueError(f"members blob too short: len={len(blob)} count={count}")
    return list(struct.unpack_from(f"<{count}I", blob, 8))


def parse_spec_xml(spec: bytes) -> dict:
    root = ET.fromstring(spec.decode("utf-8"))
    ids = root.find("ids")
    rules = [r.text or "" for r in root.iter("rule")]
    return {
        "uuid": ids.findtext("id"),
        "name": ids.findtext("name"),
        "rules": rules,
    }


def parse_groupset_xml(value: bytes) -> dict:
    root = ET.fromstring(value.decode("utf-8"))
    ids = root.find("ids")
    members = [m.text for m in root.iter("member") if m.text]
    return {
        "uuid": ids.findtext("id"),
        "name": ids.findtext("name"),
        "group_uuids": members,
    }


def main(db_path: str, out_path: str) -> None:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    refs = {}
    for rid, author, year, title, trash in con.execute(
        "SELECT id, author, year, title, trash_state FROM refs"
    ):
        first_author = (author or "").split("\r")[0].split("\n")[0].strip()
        refs[rid] = {
            "id": rid,
            "first_author": first_author,
            "year": (year or "").strip(),
            "title": re.sub(r"\s+", " ", (title or "")).strip(),
            "in_trash": bool(trash),
        }

    groups = {}
    for gid, spec, members in con.execute("SELECT group_id, spec, members FROM groups"):
        info = parse_spec_xml(spec)
        member_ids = parse_members_blob(members)
        is_custom = "TYPE;3" in info["rules"]
        groups[info["uuid"]] = {
            "group_id": gid,
            "name": info["name"],
            "is_custom": is_custom,
            "rules": info["rules"],
            "member_ref_ids": member_ids,
        }

    groupsets = []
    for _, subcode, value in con.execute(
        "SELECT code, subcode, value FROM misc WHERE code = 17 ORDER BY subcode"
    ):
        gs = parse_groupset_xml(value)
        gs["subcode"] = subcode
        groupsets.append(gs)

    assigned = {u for gs in groupsets for u in gs["group_uuids"]}
    orphan_groups = [u for u in groups if u not in assigned]

    active_refs = sum(1 for r in refs.values() if not r["in_trash"])
    snapshot = {
        "source": db_path,
        "counts": {
            "refs_total": len(refs),
            "refs_active": active_refs,
            "refs_trash": len(refs) - active_refs,
            "groups": len(groups),
            "custom_groups": sum(1 for g in groups.values() if g["is_custom"]),
            "groupsets": len(groupsets),
            "orphan_groups": len(orphan_groups),
        },
        "groupsets": groupsets,
        "groups": groups,
        "orphan_group_uuids": orphan_groups,
        "refs": refs,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)
    print(json.dumps(snapshot["counts"], ensure_ascii=False, indent=2))
    total_memberships = sum(len(g["member_ref_ids"]) for g in groups.values())
    print(f"total group memberships: {total_memberships}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
