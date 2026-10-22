import { use, registerMap } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
    LineChart,
    BarChart,
    MapChart,
    HeatmapChart,
} from 'echarts/charts'
import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
    VisualMapComponent,
} from 'echarts/components'

use([
    // 渲染器
    CanvasRenderer,
    // 图表类型
    LineChart,
    BarChart,
    MapChart,
    HeatmapChart,
    // 通用组件
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
    VisualMapComponent,
])

/** 从插件导出 registerMap，供地图页面使用（保证 MapChart 已注册） */
export { registerMap }