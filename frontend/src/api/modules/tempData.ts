import { request } from '../request'

export interface TempFileItem {
    path: string
    dataType: string
    subType: string
    nodeName: string
    date: string
    fileName?: string
    size: number
    uploadedAt: string
}

export interface UploadTempPayload {
    files: File[]
    dataType: string
    subType?: string
    date?: string
    nodeName?: string
}

export interface UploadItemResult {
    ok: boolean
    name: string
    path?: string
    dates?: string[]
    devices?: string[]
    nodes?: string[]
    ignoredNodes?: string[]      // ← 新增：文件中存在但未录入的节点
    count?: number
    error?: string
}

export interface UploadBatchResult {
    results: UploadItemResult[]
    total: number
    ok: number
}

export function uploadTempData(payload: UploadTempPayload) {
    const fd = new FormData()
    payload.files.forEach((f) => fd.append('files', f))
    fd.append('dataType', payload.dataType)
    fd.append('subType', payload.subType || '')
    fd.append('date', payload.date || '')
    fd.append('nodeName', payload.nodeName || '')

    return request<UploadBatchResult>({
        url: '/temp-data/upload',
        method: 'post',
        data: fd,
        headers: { 'Content-Type': 'multipart/form-data' },
        // 多文件时给更长的超时
        timeout: 5 * 60 * 1000,
    })
}

export function listTempData(params: {
    dataType?: string
    subType?: string
    date?: string
    nodeName?: string
}) {
    return request<TempFileItem[]>({
        url: '/temp-data/list',
        method: 'get',
        params,
    })
}

export function deleteTempData(path: string) {
    return request<void>({
        url: '/temp-data/delete',
        method: 'post',
        data: { path },
    })
}

export function scanTempData() {
    return request<{ removed: number }>({
        url: '/temp-data/scan',
        method: 'post',
    })
}
// 追加在文件末尾

export interface StorageConfigResult {
    tempDir: string
}

export interface StorageUpdatePayload {
    tempDir: string
    migrate?: boolean
}

export interface StorageUpdateResult {
    ok: boolean
    oldPath: string
    newPath: string
    migrated: number
    skipped: number
}

export function getStorageConfig() {
    return request<StorageConfigResult>({
        url: '/temp-data/config',
        method: 'get',
    })
}

export function updateStorageConfig(payload: StorageUpdatePayload) {
    return request<StorageUpdateResult>({
        url: '/temp-data/config',
        method: 'post',
        data: payload,
    })
}
/**
 * 单文件上传（带进度回调）
 * 前端逐个调用实现"每文件独立进度"
 */
export function uploadSingleTempFile(
    payload: {
        file: File
        dataType: string
        subType?: string
        date?: string
        nodeName?: string
    },
    onProgress?: (loaded: number, total: number, percent: number) => void,
) {
    const fd = new FormData()
    fd.append('files', payload.file)
    fd.append('dataType', payload.dataType)
    fd.append('subType', payload.subType || '')
    fd.append('date', payload.date || '')
    fd.append('nodeName', payload.nodeName || '')

    return request<UploadBatchResult>({
        url: '/temp-data/upload',
        method: 'post',
        data: fd,
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 10 * 60 * 1000, // 单文件最多 10 分钟
        onUploadProgress: (e) => {
            if (onProgress) {
                const total = e.total || 0
                const loaded = e.loaded || 0
                const percent =
                    total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 0
                onProgress(loaded, total, percent)
            }
        },
    })
}