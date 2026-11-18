/**
 * 统一 API 基址：
 * - 未设置 VITE_API_BASE_URL 时使用 /api（走 Vite/生产代理）
 * - 设置后（如 https://api.example.com）所有请求统一拼接
 */
export function apiBase(): string {
    const raw = (import.meta.env.VITE_API_BASE_URL || '').trim()
    if (!raw) return '/api'
    return raw.replace(/\/+$/, '')
}

export function apiUrl(path: string): string {
    const p = path.startsWith('/') ? path.slice(1) : path
    return `${apiBase()}/${p}`
}