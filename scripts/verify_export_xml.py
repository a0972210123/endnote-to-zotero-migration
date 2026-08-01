"""Verify an EndNote whole-library XML export against the sdb.eni snapshot.

Checks:
  1. record count vs snapshot active refs
  2. rec-number coverage vs snapshot ref ids (matching is later done by
     title+year, but coverage tells us whether rec-number == refs.id)
  3. attachment URLs (internal-pdf://) resolve to files under .Data/PDF

Usage: python verify_export_xml.py <export.xml> <snapshot.json> <data-dir>
"""
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


def text_of(elem) -> str:
    return "".join(elem.itertext()).strip() if elem is not None else ""


def main(xml_path: str, snapshot_path: str, data_dir: str) -> None:
    snap = json.load(open(snapshot_path, encoding="utf-8"))
    active_ids = {int(rid) for rid, r in snap["refs"].items() if not r["in_trash"]}

    root = ET.parse(xml_path).getroot()
    records = root.findall(".//record")
    print(f"records in XML: {len(records)}")
    print(f"active refs in snapshot: {len(active_ids)}")

    rec_numbers = set()
    pdf_urls = []
    missing_recnum = 0
    for rec in records:
        rn = text_of(rec.find("rec-number"))
        if rn:
            rec_numbers.add(int(rn))
        else:
            missing_recnum += 1
        for url in rec.findall(".//urls/pdf-urls/url"):
            u = text_of(url)
            if u:
                pdf_urls.append(u)

    print(f"records without rec-number: {missing_recnum}")
    print(f"rec-numbers matching snapshot ids: {len(rec_numbers & active_ids)}")
    print(f"rec-numbers NOT in snapshot active ids: {len(rec_numbers - active_ids)}")
    print(f"snapshot active ids NOT in XML: {len(active_ids - rec_numbers)}")

    pdf_dir = Path(data_dir)
    ok = missing = 0
    missing_examples = []
    for u in pdf_urls:
        if u.startswith("internal-pdf://"):
            rel = urllib.parse.unquote(u[len("internal-pdf://"):])
            p = pdf_dir / "PDF" / rel
            if p.exists():
                ok += 1
            else:
                missing += 1
                if len(missing_examples) < 5:
                    missing_examples.append(str(p))
    print(f"attachment links: {len(pdf_urls)} total, internal-pdf resolved OK: {ok}, missing: {missing}")
    for m in missing_examples:
        print("  missing:", m)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
