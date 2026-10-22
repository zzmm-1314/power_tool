import { request } from '../request'

export interface PlantNode {
    id: number
    name: string
    description: string
    createdAt: string
    updatedAt: string
}

export function listPlantNodes() {
    return request<PlantNode[]>({ url: '/nodes/plant', method: 'get' })
}

export function addPlantNode(payload: { name: string; description?: string }) {
    return request<PlantNode>({
        url: '/nodes/plant',
        method: 'post',
        data: payload,
    })
}

export function updatePlantNode(
    id: number,
    payload: { name: string; description?: string },
) {
    return request<PlantNode>({
        url: `/nodes/plant/${id}`,
        method: 'put',
        data: payload,
    })
}

export function deletePlantNode(id: number) {
    return request<void>({
        url: `/nodes/plant/${id}`,
        method: 'delete',
    })
}
export interface BatchAddResult {
    added: PlantNode[]
    skipped: { name: string; reason: string }[]
}

export function addPlantNodesBatch(payload: {
    names: string[]
    description?: string
}) {
    return request<BatchAddResult>({
        url: '/nodes/plant/batch',
        method: 'post',
        data: payload,
    })
}

export interface BatchDeleteResult {
    deleted: PlantNode[]
    count: number
}

export function deletePlantNodesBatch(ids: number[]) {
    return request<BatchDeleteResult>({
        url: '/nodes/plant/batch',
        method: 'delete',
        data: { ids },
    })
}