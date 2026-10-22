import { request } from '../request'

export interface CorrectionItem {
    period: number
    time_label: string
    base_coefficient: number
    pv_offset: number
    temp_offset: number
    humidity_offset: number
    wind_offset: number
    extreme_offset: number
    gen_risk_offset: number
    ml_offset: number
    weather_offset_total: number
    final_coefficient: number
    effective_temp: number
    humidity_contribution: number
}

export interface PredictResult {
    success: boolean
    strategy: string
    half_life: number
    target_date: string
    window_days: number
    hours: string[]
    base_coefficients: number[]
    coefficients: number[]
    correction_details: CorrectionItem[]
    weather_data: Record<string, any>[] | null
    weather_meta: Record<string, any> | null
    coeff_min: number
    coeff_max: number
}

export interface ProgressData {
    status: 'running' | 'done' | 'error'
    progress: { stage: string; current: number; total: number; message: string }
    result?: PredictResult
    error?: string
}

export function startCoefficientTask(formData: FormData) {
    return request<{ taskId: string }>({
        url: '/coefficient/predict',
        method: 'post',
        data: formData,
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 10 * 60 * 1000,
    })
}

export function fetchCoefficientProgress(taskId: string) {
    return request<ProgressData>({
        url: `/coefficient/progress/${taskId}`,
        method: 'get',
    })
}
export interface AllCoeffCurve {
    name: string
    strategy_family: string
    half_life: number
    data: (number | null)[]
}

export interface PredictResult {
    success: boolean
    strategy: string
    half_life: number
    target_date: string
    window_days: number
    hours: string[]
    base_coefficients: number[]
    coefficients: number[]
    all_coeffs_curves: AllCoeffCurve[]   // ← 新增
    correction_details: CorrectionItem[]
    weather_data: Record<string, any>[] | null
    weather_meta: Record<string, any> | null
    coeff_min: number
    coeff_max: number
}

export function fetchWeatherConfigDefaults() {
    return request<{ defaults: Record<string, any> }>({
        url: '/coefficient/weather-config',
        method: 'get',
    })
}