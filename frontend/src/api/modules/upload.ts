import { request } from '../request'

/**
 * 数据导入接口：上传 Excel → 后端即时解析入库
 * （原「临时 Excel 存储」的列表 / 删除 / 清理 / 存储目录接口已随功能移除）
 */

export interface UploadItemResult {
    ok: boolean
    name: string
    dataType?: string
    dates?: string[]
    devices?: string[]
    nodes?: string[]
    ignoredNodes?: string[] // 文件中存在但未录入的节点
    count?: number
    saved?: boolean // 是否已写入数据库；false 表示仅内存预览
    dbError?: string
    error?: string
}

export interface UploadBatchResult {
    results: UploadItemResult[]
    total: number
    ok: number
    saved?: boolean
    preview?: {
        entries: number
        totalPoints: number
        dates: string[]
        devices: string[]
    }
}

export interface UploadPayload {
    file: File
    dataType: string
    subType?: string
    date?: string
    nodeName?: string
}

/**
 * 单文件上传（带进度回调）
 * 前端逐个调用实现"每文件独立进度"
 */
export function uploadSingleFile(
    payload: UploadPayload,
    onProgress?: (loaded: number, total: number, percent: number) => void,
) {
    const fd = new FormData()
    fd.append('files', payload.file)
    fd.append('dataType', payload.dataType)
    fd.append('subType', payload.subType || '')
    fd.append('date', payload.date || '')
    fd.append('nodeName', payload.nodeName || '')

    return request<UploadBatchResult>({
        url: '/upload',
        method: 'post',
        data: fd,
        timeout: 2 * 60 * 1000, // 单文件最多 2 分钟：本地解析远超不了，超时即视为后端异常
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
