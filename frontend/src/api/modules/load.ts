import { request } from '../request'
import type { LoadAnalysisData } from '@/types'

export function fetchLoadAnalysis(params: {
    date?: string
    startDate?: string
    endDate?: string
}) {
    return request<LoadAnalysisData>({
        url: '/load/analysis',
        method: 'get',
        params,
    })
}

/** 光伏出力 */
export function fetchPvAnalysis(params: {
    date?: string
    startDate?: string
    endDate?: string
}) {
    return request<LoadAnalysisData>({
        url: '/load/pv',
        method: 'get',
        params,
    })
}

export function fetchLoadDevices() {
    return request<string[]>({ url: '/load/devices', method: 'get' })
}