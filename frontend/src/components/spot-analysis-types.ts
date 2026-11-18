export interface SpotColumnDef {
    /** row 上的属性名；特殊值 'unitNode' 表示显示当前选中的节点名 */
    key: string
    label: string
    /** 小数位；不填则原样展示（字符串） */
    decimals?: number
    /** 是否按 finalDiff 双向着色 */
    colored?: boolean
    /** 固定展示当前节点（如「交易单元」列） */
    fixedNode?: boolean
}

export interface SpotAnalysisConfig {
    title: string
    /** 筛选栏的「节点」标签，如「电厂节点」「交易单元」 */
    nodeLabel: string
    /** 后端接口，如 /rolling/spot-analysis */
    apiUrl: string
    /** 买卖方向：用于卡片汇总过滤 */
    buyDirection: string    // '买方' | '购电'
    sellDirection: string   // '卖方' | '售电'
    /** 卡片标签：'买入' | '购电' */
    buyLabel: string
    sellLabel: string
    columns: SpotColumnDef[]
}