/// <reference types="vite/client" />
import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import type { ApiResult } from '@/types'

const service: AxiosInstance = axios.create({
    // 优先环境变量；否则跟随 Vite base（生产为 /zjPowerTool/，得到 /zjPowerTool/api）
    baseURL: import.meta.env.VITE_API_BASE_URL || `${import.meta.env.BASE_URL}api`,
    timeout: 30000,
})
service.interceptors.response.use(
    (response): any => {
        if (response.config.responseType === 'blob') {
            return response
        }
        const res = response.data as ApiResult
        if (res.code !== 0) {
            return Promise.reject(new Error(res.msg || '请求失败'))
        }
        return res.data
    },
    (error) => {
        const msg =
            error?.response?.data?.msg || error?.message || '网络异常，请稍后重试'
        return Promise.reject(new Error(msg))
    },
)

export function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
    return service.request<unknown, T>(config) as Promise<T>
}

export default service
