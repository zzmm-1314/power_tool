import re, glob, sys

WANT = [
    ".input", ".input:focus", ".input.small", ".input:disabled",
    ".select", ".textarea", ".file-input", ".hidden-input",
    ".btn", ".btn:hover:not(:disabled)", ".btn:disabled", ".btn.small",
    ".btn.ghost", ".btn.ghost:hover:not(:disabled)",
    ".btn-primary", ".btn-primary:disabled", ".btn.primary",
    ".btn.primary:hover:not(:disabled)", ".btn-clear", ".btn-text",
    ".table-wrap", ".table-wrap.loading", ".sticky-col",
    ".data-table", ".data-table th", ".data-table td",
    ".data-table th, .data-table td", ".data-table tbody tr",
    ".price-table", ".price-table th, .price-table td", ".price-table thead th",
    ".price-table .date-th", ".result-table", ".result-table th",
    ".result-table th, .result-table td", ".value-td", ".value-td.empty",
    ".empty-tip", ".empty-tip code",
    ".msg", ".msg.err", ".msg.ok", ".hint",
    ".mask", ".modal", ".modal-header", ".modal-title", ".modal-subtitle",
    ".modal-body", ".modal-footer",
    ".form-row", ".form-row>label", ".form-item", ".form-item label",
    ".form-group", ".form-actions", ".form-card", ".lbl",
    ".tab-btn", ".tab-btn.active", ".tab-btn:hover",
    ".legend-bar", ".legend-bar.pos", ".legend-bar.neg", ".legend-bar-wrap",
    ".legend-block", ".legend-label", ".legend-range", ".legend-tip",
    ".corner", ".avg-label", ".avg-icon", ".avg-value", ".avg-row td",
    ".overall-avg", ".overall-avg strong",
    ".chart", ".chart-card", ".chart-header", ".chart-title", ".chart-body",
    ".card", ".result-card", ".stat-card", ".stat-cards", ".stat-label", ".stat-value",
    ".panel", ".panel-left", ".panel-right", ".filter-bar", ".filter-item",
    ".filter-item label", ".upload-area", ".upload-area:hover",
    ".upload-area.has-file", ".upload-content", ".upload-item",
    ".progress-wrap", ".section-title", ".group-title", ".title", ".row",
    ".row-label", ".separator", ".action-btns", ".extra-group", ".link",
    ".picker-wrap", ".preview-meta",
]

files = sorted(glob.glob("src/**/*.vue", recursive=True))
occ = {}
for f in files:
    txt = open(f, encoding="utf-8").read()
    m = re.search(r"<style[^>]*>(.*?)</style>", txt, re.S)
    if not m:
        continue
    css = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    for mm in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel = " ".join(mm.group(1).split())
        body = mm.group(2).strip()
        body = re.sub(r"\s+", " ", body)
        occ.setdefault(sel, []).append((f, body))

for s in WANT:
    lst = occ.get(s)
    if not lst:
        continue
    bodies = {}
    for f, b in lst:
        bodies.setdefault(b, []).append(f)
    print("=" * 90)
    print(f"{s}   [{len(lst)} 处 / {len(bodies)} 种写法]")
    for b, fs in sorted(bodies.items(), key=lambda kv: -len(kv[1])):
        names = ", ".join(p.replace("src/", "") for p in fs)
        print(f"  ({len(fs)}) {b}")
        print(f"      <- {names}")
