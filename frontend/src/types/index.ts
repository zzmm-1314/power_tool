export type DataSource = 'database' | 'excel' | 'empty'
/** 通用接口返回结构 */
export interface ApiResult<T = unknown> {
    code: number
    msg: string
    data: T
}

/** 曲线点 */
export interface CurvePoint {
    time: string
    value: number
}
/** 单条负荷曲线（一台设备） */
export interface LoadSeries {
    date?: string          // ← 新增：多天查询时区分日期
    device: string
    kind: 'actual' | 'forecast' | 'pv' | 'pv_forecast'
    points: CurvePoint[]
}
/** 负荷分析数据 */
export interface LoadAnalysisData {
    startDate?: string
    endDate?: string
    date?: string
    source: DataSource
    series: LoadSeries[]
}
/** 电价数据 */
export interface PricePoint {
    time?: string
    hour?: string
    value: number
}

export interface PriceData {
    date: string
    nodeType: 'unified' | 'plant'
    nodeName?: string
    source: DataSource
    tempPath: string | null
    points: PricePoint[]
    raw?: PricePoint[]
}

/** 价差数据 */
export interface SpreadData {
    date: string
    nodeType: 'unified' | 'plant'
    nodeName?: string
    source: DataSource
    tempPath: string | null
    points: CurvePoint[]
}

/** 结算单类型 */
export type SettlementType = 'actual' | 'jiaojiang' | 'xiandai'

export interface SettlementUpdateResult {
    type: SettlementType
    updatedAt: string
    rows: number
}

/** 月报填充结果 */
export interface MonthlyReportResult {
    month: string
    filledFields: string[]
}