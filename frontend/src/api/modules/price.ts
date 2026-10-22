import { request } from '../request'
import type { PriceData, DataSource } from '@/types'

export function fetchDayAheadUnified(params: { date: string }) {
    return request<PriceData>({
        url: '/price/day-ahead',
        method: 'get',
        params: { ...params, nodeType: 'unified' },
    })
}

export function fetchDayAheadPlant(params: { date: string; nodeName: string }) {
    return request<PriceData>({
        url: '/price/day-ahead',
        method: 'get',
        params: { ...params, nodeType: 'plant' },
    })
}

/** 电厂节点列表（从临时数据中提取） */
export function fetchPlantNodes() {
    return request<string[]>({ url: '/price/plant-nodes', method: 'get' })
}

/** 统一结算点热力图数据 */
export interface HeatmapData {
    dates: string[]
    hours: string[]
    matrix: (number | null)[][]
    source: DataSource
    minValue: number
    maxValue: number
}

export function fetchUnifiedHeatmap(params?: {
    startDate?: string
    endDate?: string
    days?: number
}) {
    return request<HeatmapData>({
        url: '/price/day-ahead/unified-heatmap',
        method: 'get',
        params,
    })
}

/** 电厂节点热力图数据 */
export function fetchPlantHeatmap(params: {
    nodeName: string
    startDate?: string
    endDate?: string
    days?: number
}) {
    return request<HeatmapData>({
        url: '/price/day-ahead/plant-heatmap',
        method: 'get',
        params,
    })
}