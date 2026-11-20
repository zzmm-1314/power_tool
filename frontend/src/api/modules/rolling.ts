import { request } from '../request'

export interface RollingAnalysisRow {
    time: string
    dayAheadPrice: number | null
    /** 该小时日前价格取自哪个库 */
    dayAheadSource?: 'jiangsu' | 'zhejiang' | 'mixed' | 'none'
    d2Qty: number; d2Price: number; d2Diff: number | null
    d3Qty: number; d3Price: number; d3Diff: number | null
    d4Qty: number; d4Price: number; d4Diff: number | null
    marketQty: number; marketPrice: number; marketDiff: number | null
}
export interface RollingAnalysisResult {
    targetDate: string
    d2Date: string; d3Date: string; d4Date: string
    rows: RollingAnalysisRow[]
    /** 日前价格实际来源：江苏库 / 浙江库 / 两者混合 / 无数据 */
    dayAheadSource?: 'jiangsu' | 'zhejiang' | 'mixed' | 'none'
    /** 有日前价格的小时数，用于提示数据缺口 */
    dayAheadHours?: number
    /** D-2/D-3/D-4 三天是否存在市场滚撮数据 */
    marketDates?: { d2: boolean; d3: boolean; d4: boolean }
}
export function fetchRollingAnalysis(targetDate: string, refresh = false) {
    return request<RollingAnalysisResult>({
        url: '/rolling/analysis',
        method: 'get',
        params: refresh ? { targetDate, refresh: 1 } : { targetDate },
    })
}

export interface RollingSpotRow {
    opDate: string
    tradeDate: string
    timeType: string
    direction: string
    qty: number
    price: number
    tradeQty: number
    clearPrice: number
    priceDiff: number
    finalDiff: number
}
export function fetchRollingSpotAnalysis(params: { node: string; startDate: string; endDate: string }) {
    return request<RollingSpotRow[]>({
        url: '/rolling/spot-analysis', method: 'get', params,
    })
}