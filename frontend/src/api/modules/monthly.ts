import { request } from '../request'

export interface TemplateItem {
    name: string
    size: number
    uploadedAt: string
}

export interface FieldItem {
    key: string
    label: string
    value: string
}

export function listMonthlyTemplates() {
    return request<TemplateItem[]>({
        url: '/monthly/templates',
        method: 'get',
    })
}

export function uploadMonthlyTemplate(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    return request<{ name: string }>({
        url: '/monthly/templates',
        method: 'post',
        data: fd,
    })
}

export function deleteMonthlyTemplate(name: string) {
    return request<void>({
        url: `/monthly/templates/${encodeURIComponent(name)}`,
        method: 'delete',
    })
}

export function parseMonthlyPdf(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    return request<{ fields: FieldItem[]; raw: Record<string, any> }>({
        url: '/monthly/parse',
        method: 'post',
        data: fd,
    })
}

export interface GenerateResult {
    filename: string
    base64: string
    reportMonth: string
    plantName: string
}

export function generateMonthlyReport(file: File, templateName: string) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('templateName', templateName)
    return request<GenerateResult>({
        url: '/monthly/generate',
        method: 'post',
        data: fd,
        timeout: 5 * 60 * 1000,
    })
}