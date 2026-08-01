"""Build the distributable docs: extract the quick-reference sheet, render PDFs.

`docs/02_遷移手冊.md` is the source of truth for the quick reference -- it lives
as a section inside the manual so there is only ever one copy to maintain.
This script extracts it into a standalone file so that docs/ and pdf/ mirror
each other (a `pdf/00_*.pdf` with no `docs/00_*.md` reads like something is
missing).

Edit the .md sources, then re-run this. Never edit the generated files.

Generated (do not edit by hand):
  docs/00_一頁快查.md    extracted from 02_遷移手冊.md
  pdf/00_一頁快查.pdf    the quick-reference sheet, prints on one sheet
  pdf/01_Word舊稿必讀.pdf
  pdf/02_遷移手冊.pdf

Requires:
  pip install markdown
  Google Chrome or Microsoft Edge (used headless to print; picks up the
  system CJK fonts, which is why we do not use wkhtmltopdf/weasyprint)

Usage:  python tools/build_docs.py
"""
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "pdf"

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body {
  font-family: "Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC",
               "Segoe UI", sans-serif;
  font-size: 10.5pt; line-height: 1.65; color: #1a1a1a; margin: 0;
}
h1 { font-size: 17pt; border-bottom: 2px solid #333; padding-bottom: 4px;
     margin: 0 0 12px; page-break-after: avoid; }
h1 + p, h1 + blockquote { page-break-before: avoid; }
h2 { font-size: 13.5pt; margin: 18px 0 8px; page-break-after: avoid;
     border-left: 4px solid #555; padding-left: 8px; }
h3 { font-size: 11.5pt; margin: 14px 0 6px; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
ul, ol { padding-left: 1.5em; margin: 6px 0; }
li { margin: 2px 0; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9.5pt;
       background: #f0f0f0; padding: 1px 4px; border-radius: 3px;
       word-break: break-all; }
pre { background: #f6f6f6; border: 1px solid #ddd; border-left: 3px solid #888;
      padding: 8px 10px; border-radius: 4px; page-break-inside: avoid;
      white-space: pre-wrap; word-break: break-all; }
pre code { background: none; padding: 0; font-size: 9pt; }
blockquote { border-left: 3px solid #bbb; background: #fafafa; margin: 10px 0;
             padding: 6px 12px; page-break-inside: avoid; }
blockquote p { margin: 4px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0;
        font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 5px 7px; text-align: left;
         vertical-align: top; }
th { background: #eee; font-weight: 600; }
tr:nth-child(even) td { background: #fafafa; }
hr { border: 0; border-top: 1px solid #ccc; margin: 18px 0; }
a { color: #0b5cad; text-decoration: none; word-break: break-all; }
strong { color: #000; }
.callout { border-left: 4px solid #888; background: #f7f7f7; padding: 8px 12px;
           margin: 10px 0; border-radius: 0 4px 4px 0; page-break-inside: avoid; }
.callout-warning { border-left-color: #d9822b; background: #fff6ec; }
.callout-danger  { border-left-color: #c0392b; background: #fdecea; }
.callout-tip     { border-left-color: #27924f; background: #eefaf1; }
.callout-success { border-left-color: #27924f; background: #eefaf1; }
.callout-info    { border-left-color: #2b7cd9; background: #eef4fd; }
.callout-title { font-weight: 700; display: block; margin-bottom: 4px; }
.pagebreak { page-break-before: always; }
"""

CALLOUT_KINDS = {"warning", "danger", "tip", "success", "info", "note", "abstract"}


def convert_callouts(md_text: str) -> str:
    """Turn Obsidian '> [!kind] title' blocks into HTML divs.

    Standard markdown renders these as a blockquote containing a literal
    '[!warning]', which looks broken in print.
    """
    lines = md_text.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^>\s*\[!(\w+)\]\s*(.*)$", lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        kind = m.group(1).lower()
        title = m.group(2).strip()
        body = []
        i += 1
        while i < len(lines) and lines[i].startswith(">"):
            body.append(re.sub(r"^>\s?", "", lines[i]))
            i += 1
        cls = kind if kind in CALLOUT_KINDS else "info"
        inner = markdown.markdown("\n".join(body), extensions=["tables", "fenced_code"])
        head = f'<span class="callout-title">{title}</span>' if title else ""
        out.append(f'<div class="callout callout-{cls}">{head}{inner}</div>')
        out.append("")
    return "\n".join(out)


def strip_frontmatter(md_text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", md_text, count=1, flags=re.S)


def to_html(md_text: str, title: str) -> str:
    md_text = strip_frontmatter(md_text)
    md_text = convert_callouts(md_text)
    body = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "sane_lists", "attr_list"]
    )
    # checklist boxes -> printable squares
    body = body.replace("<li>[ ] ", "<li>☐ ").replace("<li>[x] ", "<li>☑ ")
    return (
        '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def extract_quickref(md_text: str) -> str:
    """Pull the 一頁快查 section out so it can be printed on its own."""
    m = re.search(r"(# 📄 一頁快查.*?)(?=\n# 第 0 章)", md_text, flags=re.S)
    if not m:
        raise SystemExit("找不到「一頁快查」段落，手冊結構可能改過了")
    return m.group(1)


def find_browser() -> str:
    for p in BROWSERS:
        if Path(p).exists():
            return p
    for name in ("chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("找不到 Chrome 或 Edge，無法產生 PDF")


def print_pdf(browser: str, html_path: Path, pdf_path: Path) -> None:
    url = "file:///" + urllib.parse.quote(str(html_path).replace("\\", "/"))
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", "--virtual-time-budget=4000",
         f"--print-to-pdf={pdf_path}", url],
        check=True, capture_output=True,
    )


QUICKREF_HEADER = """---
title: EndNote → Zotero 遷移　一頁快查
generated_from: 02_遷移手冊.md
---

<!-- 這個檔案是自動產生的，請不要直接編輯。 -->
<!-- 內容來源是 02_遷移手冊.md 的「一頁快查」一節；改完那裡再跑 tools/build_docs.py。 -->

# EndNote → Zotero 遷移　一頁快查

> 📌 這頁是[遷移手冊](02_遷移手冊.md)的濃縮版，**印出來貼在螢幕旁邊照著勾**
> （[PDF 版](../pdf/00_一頁快查.pdf)剛好一頁）。每一步的詳細說明都在手冊裡。
>
> ⚠️ **本檔由 `tools/build_docs.py` 自動產生，改這裡不會生效**——請改手冊。

"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    tmp = OUT / "_tmp"
    tmp.mkdir(exist_ok=True)
    browser = find_browser()
    print(f"browser: {browser}\n")

    manual = (DOCS / "02_遷移手冊.md").read_text(encoding="utf-8")

    # 抽出一頁快查，同時產出 md（給 GitHub 上直接閱讀）與 PDF（給列印）
    quickref_body = strip_frontmatter(extract_quickref(manual)).replace("# 📄 一頁快查\n", "")
    # 這行在手冊裡是導言；抽成獨立檔後「後面章節」已不存在，且與抬頭重複
    quickref_body = quickref_body.replace(
        "> 這一頁可單獨列印，貼在螢幕旁邊照著勾。細節看後面章節。\n", ""
    ).lstrip("\n")
    quickref_md = QUICKREF_HEADER + quickref_body.lstrip("\n")
    (DOCS / "00_一頁快查.md").write_text(quickref_md, encoding="utf-8", newline="\n")
    print(f"  OK  docs/00_一頁快查.md        （自動產生，勿手改）")

    jobs = [
        ("00_一頁快查", "EndNote → Zotero 遷移　一頁快查",
         "# EndNote → Zotero 遷移　一頁快查\n\n" + quickref_body),
        ("01_Word舊稿必讀", "Word 舊稿必讀",
         (DOCS / "01_Word舊稿必讀.md").read_text(encoding="utf-8")),
        ("02_遷移手冊", "EndNote → Zotero 遷移手冊", manual),
    ]

    for stem, title, text in jobs:
        html_path = tmp / f"{stem}.html"
        pdf_path = OUT / f"{stem}.pdf"
        html_path.write_text(to_html(text, title), encoding="utf-8")
        print_pdf(browser, html_path, pdf_path)
        size = pdf_path.stat().st_size
        print(f"  OK  {pdf_path.name:<28} {size/1024:7.1f} KB")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n完成，輸出於 {OUT}")


if __name__ == "__main__":
    sys.exit(main())
