export interface HeatmapConfig {
    title: string
    /** 传给 appStore.openUpload 的 key */
    uploadKey: string
    /** 上传按钮文字，如「📤 上传 Excel」「📤 上传实时价格」 */
    uploadText: string
    /** 数据大类 */
    kind: 'day-ahead' | 'spread'
    /** 统一结算点 or 电厂节点 */
    nodeType: 'unified' | 'plant'
    /** 热力图色阶模式 */
    mode: 'price' | 'spread'
    /** price 模式的基准线，默认 350 */
    basePrice?: number
}