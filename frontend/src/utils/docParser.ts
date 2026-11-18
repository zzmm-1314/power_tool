import * as pdfjsLib from 'pdfjs-dist'
import * as mammoth from 'mammoth'

// 配置 PDF.js 的 worker（Vite 会自动解析这个路径）
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
).toString()

/* ================= PDF 提取核心算法 ================= */
function estimateWidth(str: string, fontSize: number) {
    let w = 0
    for (const ch of str) {
        if (/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch)) w += fontSize
        else if (ch === ' ') w += fontSize * 0.3
        else w += fontSize * 0.55
    }
    return w
}

function needSpace(prevStr: string, nextStr: string, gap: number, fontSize: number) {
    if (gap <= 0) return false
    const fs = fontSize || 10
    if (gap < fs * 0.35) return false
    const prevCh = prevStr.slice(-1)
    const nextCh = nextStr.charAt(0)
    if (!prevCh || !nextCh) return false
    const isCJK = (ch: string) => /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch)
    if (isCJK(prevCh) && isCJK(nextCh)) return false
    if (isCJK(prevCh) && /[，。！？；：、（）【】《》""''…—]/.test(nextCh)) return false
    if (/[，。！？；：、（）【】《》""''…—]/.test(prevCh) && isCJK(nextCh)) return false
    return gap >= fs * 0.5
}

function buildPageLines(items: any[], viewport: any, filterRotate: boolean) {
    const infos: any[] = []
    for (const it of items) {
        const str = it.str
        if (!str || !str.trim()) continue
        const tr = it.transform
        if (!tr || tr.length < 6) continue
        const x = tr[4], y = tr[5]
        const fontSize = Math.abs(tr[3]) || it.height || 10
        const angle = Math.atan2(tr[1], tr[0]) * 180 / Math.PI

        if (filterRotate) {
            const absA = Math.abs(angle)
            if (absA > 2 && Math.abs(absA - 180) > 2 && Math.abs(absA - 360) > 2) continue
        }
        if (fontSize < 2) continue

        let w = it.width
        if (!w || !isFinite(w)) w = estimateWidth(str, fontSize)

        infos.push({ str, x, y, w, xEnd: x + w, fontSize })
    }

    if (!infos.length) return []

    infos.sort((a, b) => (b.y - a.y) || (a.x - b.x))

    const lines: any[] = []
    let cur: any = null

    for (const inf of infos) {
        if (!cur) {
            cur = { y: inf.y, fontSize: inf.fontSize, items: [inf] }
            continue
        }
        const tol = Math.max(2, Math.min(inf.fontSize, cur.fontSize) * 0.6)
        if (Math.abs(inf.y - cur.y) <= tol) {
            cur.items.push(inf)
            cur.y = cur.items.reduce((s: number, i: any) => s + i.y, 0) / cur.items.length
            cur.fontSize = Math.max(cur.fontSize, inf.fontSize)
        } else {
            lines.push(cur)
            cur = { y: inf.y, fontSize: inf.fontSize, items: [inf] }
        }
    }
    if (cur) lines.push(cur)

    const result: string[] = []
    for (const ln of lines) {
        ln.items.sort((a: any, b: any) => a.x - b.x)
        let lineText = ''
        let prev: any = null
        for (const inf of ln.items) {
            if (prev) {
                const gap = inf.x - prev.xEnd
                if (needSpace(prev.str, inf.str, gap, prev.fontSize)) lineText += ' '
            }
            lineText += inf.str
            prev = inf
        }
        if (lineText.trim()) result.push(lineText)
    }
    return result
}

function filterHeadersFooters(pagesLines: string[][]) {
    if (pagesLines.length < 3) return pagesLines
    const normalize = (s: string) => s.replace(/\d+/g, '#').replace(/\s+/g, '').trim()
    const edgeCount: Record<string, number> = {}

    for (const lines of pagesLines) {
        if (!lines.length) continue
        const cands = new Set<string>()
        cands.add(normalize(lines[0]))
        if (lines.length > 1) cands.add(normalize(lines[lines.length - 1]))
        for (const c of cands) {
            if (!c) continue
            edgeCount[c] = (edgeCount[c] || 0) + 1
        }
    }

    const threshold = Math.ceil(pagesLines.length * 0.5)
    const toRemove = new Set<string>()
    for (const k in edgeCount) {
        if (edgeCount[k] >= threshold) toRemove.add(k)
    }
    if (!toRemove.size) return pagesLines

    return pagesLines.map(lines => lines.filter(l => !toRemove.has(normalize(l))))
}

/* ================= 对外暴露的解析入口 ================= */
export async function readAnyFile(file: File, onProgress?: (msg: string) => void): Promise<string> {
    const name = file.name.toLowerCase()

    if (name.endsWith('.pdf')) {
        if (onProgress) onProgress('正在解析 PDF 文件...')
        const buf = await file.arrayBuffer()
        const pdf = await pdfjsLib.getDocument({
            data: new Uint8Array(buf),
            disableFontFace: true
        }).promise


        const total = pdf.numPages
        const allPagesLines: string[][] = []
        for (let p = 1; p <= total; p++) {
            if (onProgress) onProgress(`解析中 ${p}/${total} 页`)
            const page = await pdf.getPage(p)
            const viewport = page.getViewport({ scale: 1 })
            const content = await page.getTextContent({ includeMarkedContent: false })
            const lines = buildPageLines(content.items, viewport, true)
            allPagesLines.push(lines)
            page.cleanup()
        }
        try { await (pdf as any).destroy?.() } catch (e) { }


        const pagesText = filterHeadersFooters(allPagesLines)
        const text = pagesText.map(l => l.join('\n')).join('\n\n').replace(/\r\n?/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
        if (!text) throw new Error('该 PDF 未提取到文字（可能是扫描件），请改用其他格式')
        return text
    }

    if (name.endsWith('.docx')) {
        if (onProgress) onProgress('正在解析 Word 文件...')
        const buf = await file.arrayBuffer()
        const res = await mammoth.extractRawText({ arrayBuffer: buf })
        return res.value || ''
    }

    // 纯文本类
    if (onProgress) onProgress('正在读取文本...')
    const buf = await file.arrayBuffer()
    let text = new TextDecoder('utf-8').decode(buf)
    const bad = (text.match(/\uFFFD/g) || []).length
    if (bad > 0) {
        try {
            const alt = new TextDecoder('gbk').decode(buf)
            if ((alt.match(/\uFFFD/g) || []).length < bad) text = alt
        } catch (e) { }
    }
    return text
}

export {
    buildPageLines,        // 已有，补充 export
    filterHeadersFooters,  // 已有，补充 export
}