import { request } from '../request'

export interface RollingAnalysisRow {
    time: string
    dayAheadPrice: number | null
    d2Qty: number; d2Price: number; d2Diff: number | null
    d3Qty: number; d3Price: number; d3Diff: number | null
    d4Qty: number; d4Price: number; d4Diff: number | null
    marketQty: number; marketPrice: number; marketDiff: number | null
}
export interface RollingAnalysisResult {
    targetDate: string
    d2Date: string; d3Date: string; d4Date: string
    rows: RollingAnalysisRow[]
}
export function fetchRollingAnalysis(targetDate: string) {
    return request<RollingAnalysisResult>({
        url: '/rolling/analysis', method: 'get', params: { targetDate },
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