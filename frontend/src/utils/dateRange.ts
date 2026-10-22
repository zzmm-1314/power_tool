/**
 * 把 [start, end] 展开为日期字符串数组（包含两端）
 * 若 start/end 缺失或格式不合法 → 返回 []
 */
export function expandDateRange(start: string, end: string): string[] {
    if (!start || !end) return []
    const s = new Date(start)
    const e = new Date(end)
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return []

    const from = s <= e ? s : e
    const to = s <= e ? e : s

    const result: string[] = []
    const cur = new Date(from)
    let guard = 0
    while (cur <= to && guard < 400) {
        const y = cur.getFullYear()
        const m = String(cur.getMonth() + 1).padStart(2, '0')
        const d = String(cur.getDate()).padStart(2, '0')
        result.push(`${y}-${m}-${d}`)
        cur.setDate(cur.getDate() + 1)
        guard++
    }
    return result
}