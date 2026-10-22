import { request } from '../request'

export type SettlementTaskType = 'actual' | 'jiaojiang' | 'xiandai'

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