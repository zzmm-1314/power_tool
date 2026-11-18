import { request } from '../request'
import { apiUrl } from '@/utils/apiBase'

export interface UnifiedPlantRow {
    id: number;
    plant: string
    unit: string
    capacity: number | null
    city: string
}

export interface ImportResult {
    ok: boolean
    path: string
    count: number
    cities: number
    plants: number
}

export function importUnifiedPlants(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    return request<ImportResult>({
        url: '/unified-plants/import',
        method: 'post',
        data: fd,
        // ✅ 不再手写 Content-Type，让 axios 自动加 boundary
        timeout: 2 * 60 * 1000,
    })
}

export function clearUnifiedPlants() {
    return request<null>({
        url: '/unified-plants/import',
        method: 'delete',
    })
}

export interface PagedResult<T> {
    total: number
    page: number
    pageSize: number
    items: T[]
}

export function fetchUnifiedPlantsPaged(params: {
    page: number
    pageSize: number
    keyword?: string
    city?: string
}) {
    return request<PagedResult<UnifiedPlantRow>>({
        url: '/unified-plants/list',
        method: 'get',
        params,
    })
}

export interface CityAggregate {
    city: string
    plantCount: number
    unitCount: number
    totalCapacity: number
}

export interface MapData {
    cities: CityAggregate[]
    maxPlantCount: number
    maxCapacity: number       // ← 新增
    totalCapacity: number     // ← 新增
    totalPlants: number
    totalUnits: number
    totalCities: number
}

export function fetchUnifiedPlantsMap() {
    return request<MapData>({
        url: '/unified-plants/map',
        method: 'get',
    })
}

export function fetchUnifiedPlantsCities() {
    return request<string[]>({
        url: '/unified-plants/cities',
        method: 'get',
    })
}

export function addUnifiedPlant(payload: {
    plant: string
    unit?: string
    capacity?: number | null
    city?: string
}) {
    return request<{ id: number }>({
        url: '/unified-plants/item',
        method: 'post',
        data: payload,
    })
}

export function updateUnifiedPlant(recordId: number, payload: {
    plant: string
    unit?: string
    capacity?: number | null
    city?: string
}) {
    return request<void>({
        url: `/unified-plants/item/${recordId}`,
        method: 'put',
        data: payload,
    })
}

export function deleteUnifiedPlantsBatch(ids: number[]) {
    return request<{ count: number }>({
        url: '/unified-plants/item/batch',
        method: 'delete',
        data: { ids },
    })
}

export function downloadUnifiedPlantsTemplate() {
    window.open(apiUrl('/unified-plants/template'), '_blank')
}