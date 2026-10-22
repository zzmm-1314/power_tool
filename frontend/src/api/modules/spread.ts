import { request } from '../request'
import type { SpreadData, DataSource } from '@/types'

export function fetchSpreadUnified(params: { date: string }) {
    return request<SpreadData>({
        url: '/spread/analysis',
        method: 'get',
        params: { ...params, nodeType: 'unified' },
    })
}

export function fetchSpreadPlant(params: { date: string; nodeName: string }) {
    return request<SpreadData>({
        url: '/spread/analysis',
        method: 'get',
        params: { ...params, nodeType: 'plant' },
    })
}

export interface SpreadHeatmapData {
    dates: string[]
    hours: string[]
    matrix: (number | null)[][]
    source: DataSource
    minValue: number
    maxValue: number
}

export function fetchSpreadHeatmap(params?: {
    startDate?: string
    endDate?: string
    days?: number
}) {
    return request<SpreadHeatmapData>({
        url: '/spread/unified-heatmap',
        method: 'get',
        params,
    })
}

/** 价差分析 · 电厂节点热力图 */
export function fetchSpreadPlantHeatmap(params: {
    nodeName: string
    startDate?: string
    endDate?: string
    days?: number
}) {
    return request<SpreadHeatmapData>({
        url: '/spread/plant-heatmap',
        method: 'get',
        params,
    })
}
export interface SpreadDailyPrices {
    date: string
    hours: string[]
    dayAhead: (number | null)[]
    realTime: (number | null)[]
    spread: (number | null)[]
    source: DataSource
}

export function fetchSpreadDailyPrices(params: {
    date: string
    nodeType?: 'unified' | 'plant'
    nodeName?: string
}) {
    return request<SpreadDailyPrices>({
        url: '/spread/daily-prices',
        method: 'get',
        params,
    })
}