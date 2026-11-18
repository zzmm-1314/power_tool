import re, glob

# 计划放进 global.css 的通用类名
CAND = [
    "input","select","textarea","file-input","hidden-input","btn","primary","ghost","small",
    "clear","btn-clear","btn-text","btn-primary","btn-upload","btn-link",
    "card","panel","form-card","filter-bar","filter-item","result-card","chart-card",
    "stat-cards","stat-card","stat-label","stat-value","table-wrap","sticky-col","corner",
    "data-table","price-table","result-table","avg-row","avg-label","avg-icon","avg-value",
    "overall-avg","legend-bar","legend-bar-wrap","legend-block","legend-label","legend-range",
    "legend-tip","msg","err","ok","hint","empty-tip","mask","modal","modal-header","modal-title",
    "modal-subtitle","modal-body","modal-footer","form-row","form-item","form-group",
    "form-actions","lbl","row","separator","action-btns","extra-group","link","title",
    "section-title","group-title","tab-btn","active","chart","upload-area","upload-content",
    "upload-item","progress-wrap","row-label","preview-meta","picker-wrap","value-td","date-th",
]

files = sorted(glob.glob("src/**/*.vue", recursive=True))
used_no_def = {}
defined = set()
for f in files:
    txt = open(f, encoding="utf-8").read()
    sm = re.search(r"<style[^>]*>(.*?)</style>", txt, re.S)
    style = sm.group(1) if sm else ""
    outside = txt[: sm.span()[0]] + txt[sm.span()[1]:] if sm else txt
    # 该文件 style 块中定义的 class token
    defs = set(re.findall(r"\.([A-Za-z][\w-]*)", re.sub(r"/\*.*?\*/", "", style, flags=re.S)))
    # 模板中出现的 class token（class="..." 与 :class 字符串）
    uses = set()
    for attr in re.findall(r'(?:"|:)class="([^"]*)"', outside):
        uses |= set(re.findall(r"[A-Za-z][\w-]*", attr))
    for s in re.findall(r"'([A-Za-z][\w-]*)'", outside):
        pass
    for c in CAND:
        if c in uses and c not in defs:
            used_no_def.setdefault(c, []).append(f)
        if c in defs:
            defined.add(c)

print("=== 模板中使用了该通用类、但本文件没有局部定义（会直接吃到全局样式）===")
for c in CAND:
    if c in used_no_def:
        print(f"{c:16s} {len(used_no_def[c])} 处: " + ", ".join(p.replace('src/', '') for p in used_no_def[c]))
print()
print("=== 从未在任何 style 块定义的候选类（可省略）===")
print(", ".join(c for c in CAND if c not in defined))
