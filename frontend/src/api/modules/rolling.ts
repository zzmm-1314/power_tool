import { request } from '../request'

export interface RollingRow {
    hour: number
    hour_label: string
    latest: number | null
    bid3: number | null
    bid3_vol: number | null
    bid2: number | null
    bid2_vol: number | null
    bid1: number | null
    bid1_vol: number | null
    ask1: number | null
    ask1_vol: number | null
    ask2: number | null
    ask2_vol: number | null
    ask3: number | null
    ask3_vol: number | null
    unfilled: number | null
    direction: string
    buyable: number | null
    sellable: number | null
    orderable: number | null
    avg_price: number | null
    bid1_diff: number | null
    ask1_diff: number | null
}

export interface RollingResult {
    dates_used: string[]
    avg_days: number
    rows: RollingRow[]
}

export function analyzeRolling(payload: {
    html: string
    avgDays: number
    refDate?: string
}) {
    return request<RollingResult>({
        url: '/rolling/analyze',
        method: 'post',
        data: payload,
    })
}

export async function exportRolling(payload: {
    html: string
    avgDays: number
    refDate?: string
}) {
    const res = await fetch('/api/rolling/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
    if (!res.ok) {
        let msg = '导出失败'
        try {
            const data = await res.json()
            msg = data.msg || msg
        } catch (_) {
            /* ignore */
        }
        throw new Error(msg)
    }
    const blob = await res.blob()
    const cd = res.headers.get('Content-Disposition') || ''
    let filename = '滚撮分析.xlsx'
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    if (m) filename = decodeURIComponent(m[1])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
}