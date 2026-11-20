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
export function fetchPriceCompareDefaults() {
    return request<string[]>({
        url: '/nodes/price-compare-defaults',
        method: 'get'
    })
}

export function savePriceCompareDefaults(nodes: string[]) {
    return request<null>({
        url: '/nodes/price-compare-defaults',
        method: 'post',
        data: { nodes }
    })
}

// ⭐ 新增：全局默认节点
export function fetchGlobalNode() {
    return request<string>({
        url: '/nodes/global-node',
        method: 'get',
    })
}

export function saveGlobalNode(node: string) {
    return request<null>({
        url: '/nodes/global-node',
        method: 'post',
        data: { node },
    })
}