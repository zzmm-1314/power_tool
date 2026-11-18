/// <reference types="vite/client" />

/**
 * 统一 API 基址：
 * - 优先 VITE_API_BASE_URL
 * - 未设置时跟随 Vite base（生产 base 为 /zjPowerTool/ → /zjPowerTool/api）
 */
export function apiBase(): string {
    const raw = (import.meta.env.VITE_API_BASE_URL || '').trim()
    if (!raw) {
        return `${import.meta.env.BASE_URL}api`.replace(/\/{2,}/g, '/')
    }
    return raw.replace(/\/+$/, '')
}

export function apiUrl(path: string): string {
    const p = path.startsWith('/') ? path.slice(1) : path
    return `${apiBase()}/${p}`
}