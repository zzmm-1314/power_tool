import re, glob, collections

files = sorted(glob.glob("src/**/*.vue", recursive=True))
sels = collections.defaultdict(set)
rules = collections.defaultdict(list)
total_css_lines = 0

for f in files:
    txt = open(f, encoding="utf-8").read()
    m = re.search(r"<style[^>]*>(.*?)</style>", txt, re.S)
    if not m:
        continue
    css = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    total_css_lines += len([l for l in m.group(1).splitlines() if l.strip()])
    for mm in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel = " ".join(mm.group(1).split())
        if not sel or sel.startswith("@") or ":deep" in sel or "::v-deep" in sel:
            continue
        sels[sel].add(f)
        rules[sel].append((f, " ".join(mm.group(2).split())))

cross = {s: fs for s, fs in sels.items() if len(fs) > 1}
print("vue files:", len(files), "| non-empty css lines:", total_css_lines)
print("distinct selectors:", len(sels), "| cross-file dup selectors:", len(cross))
print()
print("=== 跨文件重复选择器：文件数 | 不同声明体数 | 选择器 ===")
for s, fs in sorted(cross.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    bodies = len(set(b for _, b in rules[s]))
    print(f"{len(fs):2d}  {bodies:2d}  {s}")

print()
print("=== 每个文件样式行数占比（前 20） ===")
rows = []
for f in files:
    txt = open(f, encoding="utf-8").read()
    m = re.search(r"<style[^>]*>(.*?)</style>", txt, re.S)
    n = len([l for l in m.group(1).splitlines() if l.strip()]) if m else 0
    rows.append((n, len(txt.splitlines()), f))
for n, tot, f in sorted(rows, reverse=True)[:20]:
    print(f"{n:4d} / {tot:4d}  {f}")
