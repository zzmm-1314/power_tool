export interface SettlementSimConfig {
    title: string
    taskType: 'simulate'
    /** 显示「年度合约来源」下拉 */
    showYearSource?: boolean
    /** 显示「固定申报功率」路径输入 */
    showFixedFile?: boolean
    /** 显示「月度」合约电价输入 */
    showMonthlyPrice?: boolean
    /** 显示「48点申报电量」粘贴/上传区 */
    showDeclaration?: boolean
    /** 节点选择器宽度，默认 250px */
    nodeWidth?: string
}