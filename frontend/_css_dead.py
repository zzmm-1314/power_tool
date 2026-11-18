import re, glob

files = sorted(glob.glob("src/**/*.vue", recursive=True))
report = {}
total_dead = 0

for f in files:
    txt = open(f, encoding="utf-8").read()
    sm = re.search(r"<style[^>]*>(.*?)</style>", txt, re.S)
    if not sm:
        continue
    style_span = sm.span()
    outside = txt[: style_span[0]] + txt[style_span[1] :]
    css = re.sub(r"/\*.*?\*/", "", sm.group(1), flags=re.S)

    dead = []
    for mm in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel = " ".join(mm.group(1).split())
        if not sel or sel.startswith("@"):
            continue
        # 去掉伪元素/状态，取出所有 class token
        base = re.sub(r":deep\(|::v-deep\(|\(|\)", " ", sel)
        toks = set(re.findall(r"\.([A-Za-z][\w-]*)", base))
        if not toks:
            continue
        miss = [t for t in toks if not re.search(r"[\"'\s`.]"+re.escape(t)+r"[\"'\s`,.:\[]", outside)]
        if len(miss) == len(toks):
            dead.append((sel, " ".join(mm.group(2).split())[:80]))
    if dead:
        report[f] = dead
        total_dead += len(dead)

print("总可疑死规则:", total_dead, "涉及文件:", len(report), "\n")
for f, lst in sorted(report.items(), key=lambda kv: -len(kv[1])):
    print(f"### {f}  ({len(lst)})")
    for s, b in lst:
        print(f"   {s}   {{ {b} }}")
    print()
