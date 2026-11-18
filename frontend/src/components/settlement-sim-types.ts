export interface SettlementSimConfig {
    title: string
    taskType: 'simulate'
    /** 显示「年度合约来源」下拉 */
    showYearSource?: boolean
    /**
     * @deprecated 固定申报功率输入框已移除；保留字段仅为兼容历史配置，不再生效。
     * 若需填写申报电量，请使用 showDeclaration。
     */
    showFixedFile?: boolean
    /** 显示「月度」合约电价输入 */
    showMonthlyPrice?: boolean
    /** 显示「48点申报电量」粘贴区 + 下载模板按钮 */
    showDeclaration?: boolean
    /** 节点选择器宽度，默认 250px */
    nodeWidth?: string
}