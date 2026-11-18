import { request } from '../request'

export type SettlementTaskType = 'actual' | 'simulate' | 'jiaojiang' | 'general'

export interface TaskProgress {
    current: number
    total: number
    percent: number
}

export interface TaskInfo {
    task_id: string
    type: SettlementTaskType
    status: 'running' | 'completed' | 'error'
    logs: string[]
    finished: boolean
    progress: TaskProgress
    createdAt: string
    finishedAt: string | null
}

export function startSettlementTask(
    taskType: SettlementTaskType,
    params: Record<string, any>,
) {
    return request<{ taskId: string }>({
        url: `/settlement/start/${taskType}`,
        method: 'post',
        data: { params },
    })
}

export function fetchTaskStatus(taskId: string) {
    return request<TaskInfo>({
        url: `/settlement/tasks/${taskId}`,
        method: 'get',
    })
}

export interface ParsedPaths {
    detail_folder: string
    spot_file: string
    fixed_file: string
    strategy_file: string
    strategy_file_v2: string
    stat_file: string
    stat_file_v2: string
    info_file: string
    info_spot_file: string
    info_contract_file: string
    target_file: string
    target_file_v2: string
}

export function parsePaths(paths: string[]) {
    return request<ParsedPaths>({
        url: '/settlement/parse-paths',
        method: 'post',
        data: { paths },
    })
}

export function browseFile() {
    return request<{ path: string }>({
        url: '/settlement/browse-file',
        method: 'post',
    })
}

export function browseFolder() {
    return request<{ path: string }>({
        url: '/settlement/browse-folder',
        method: 'post',
    })
}
export interface BuildPriceFilePayload {
    kind: 'unified' | 'plant-pair'
    nodeName?: string
    startDate: string
    endDate: string
}

export interface BuildPriceFileResult {
    ok: boolean
    path: string
    dateCount: number
    nodeName?: string
}

export function buildPriceFile(payload: BuildPriceFilePayload) {
    return request<BuildPriceFileResult>({
        url: '/settlement/build-price-file',
        method: 'post',
        data: payload,
    })
}

export interface ActualRecord {
    date: string
    online_qty: number | null
    total_fee: number | null
    da_qty: number | null; da_price: number | null; da_fee: number | null
    rt_qty: number | null; rt_price: number | null; rt_fee: number | null
    cs_qty: number | null; cs_price: number | null; cs_fee: number | null
    year_qty: number | null; year_price: number | null; year_fee: number | null
    month_qty: number | null; month_price: number | null; month_fee: number | null
    intraday_qty: number | null; intraday_price: number | null; intraday_fee: number | null
}

export function uploadActualSettlement(nodeName: string, files: File[]) {
    const fd = new FormData()
    fd.append('node_name', nodeName)
    files.forEach(f => fd.append('files', f))
    return request<{ msg: string }>({
        url: '/settlement/actual/upload',
        method: 'post',
        data: fd,
        timeout: 2 * 60 * 1000,
    })
}

export function fetchActualRecords(nodeName: string) {
    return request<ActualRecord[]>({
        url: '/settlement/actual/records',
        method: 'get',
        params: { node_name: nodeName },
    })
}

export function queryActualComparison(params: {
    month: string
    nodes: string[]   // 逗号拼接在后端完成还是前端完成？
    compensation?: number
}) {
    return request<any[]>({
        url: '/settlement/actual/query',
        method: 'get',
        params: {
            month: params.month,
            nodes: params.nodes.join(','),
            compensation: params.compensation,
        },
    })
}

export function saveOfficialPrice(payload: {
    node: string
    month: string
    officialPrice?: number | null
    diffAmount?: number | null
}) {
    return request<{ msg: string }>({
        url: '/settlement/actual/save-official',
        method: 'post',
        data: payload,
    })
}