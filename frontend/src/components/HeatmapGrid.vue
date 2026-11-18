<template>
    <!-- 绑定动态样式，控制容器高度 -->
    <div class="heat-wrap" :style="wrapStyle">
        <div class="heat-scroll">
            <table class="heat-table">
                <thead>
                    <tr>
                        <th class="sticky-col col-time">时间\日期</th>
                        <template v-if="mode === 'spread'">
                            <th class="sticky-col col-stat" style="left: 60px;">正价差占比</th>
                            <th class="sticky-col col-stat" style="left: 130px;">价差总和</th>
                        </template>
                        <th v-for="d in dates" :key="'h-' + d">{{ shortDate(d) }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(h, hIdx) in displayHours" :key="'r-' + hIdx">
                        <td class="sticky-col col-time">{{ h }}</td>
                        <template v-if="mode === 'spread'">
                            <!-- 将原来的 :style="{ background: ratioBg(...) }" 替换为： -->
                            <td class="sticky-col col-stat" style="left: 60px;" :style="ratioStyle(rowPosRatio[hIdx])">
                                {{ rowPosRatio[hIdx] }}
                            </td>
                            <td class="sticky-col col-stat" style="left: 130px;" :style="sumStyle(rowSum[hIdx])">
                                {{ rowSum[hIdx] }}
                            </td>
                        </template>
                        <td v-for="(d, dIdx) in dates" :key="'c-' + hIdx + '-' + dIdx"
                            :class="{ 'empty-cell': displayMatrix[hIdx]?.[dIdx] == null }"
                            :style="{ background: cellBg(displayMatrix[hIdx]?.[dIdx]) }">
                            <div class="cell-content">
                                {{ formatCell(displayMatrix[hIdx]?.[dIdx]) }}
                            </div>
                        </td>
                    </tr>
                </tbody>
                <tfoot v-if="showDailyAvg && realDailyAvg.length">
                    <!-- 日均值行 -->
                    <tr class="sticky-bottom-row">
                        <td class="sticky-col col-time" style="background: #ecf5ff; color: #2d6cdf; font-weight: 600;">
                            日均</td>
                        <template v-if="mode === 'spread'">
                            <td class="sticky-col col-stat" style="left: 60px; background: #ecf5ff;"></td>
                            <td class="sticky-col col-stat" style="left: 130px; background: #ecf5ff;"></td>
                        </template>
                        <td v-for="(d, dIdx) in dates" :key="'avg-' + dIdx"
                            :class="{ 'empty-cell': realDailyAvg[dIdx] == null }"
                            :style="{ background: cellBg(realDailyAvg[dIdx], true) }">
                            <div class="cell-content">{{ formatCell(realDailyAvg[dIdx]) }}</div>
                        </td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <!-- 底部：图例 + 总均值 -->
        <div class="bottom-bar">
            <div class="legend">
                <template v-if="mode === 'price'">
                    <div class="legend-block">
                        <span class="legend-label">低于 {{ basePrice }}</span>
                        <div class="legend-bar price-low"></div>
                    </div>
                    <div class="legend-block">
                        <span class="legend-label">高于 {{ basePrice }}</span>
                        <div class="legend-bar price-high"></div>
                    </div>
                </template>
                <template v-else>
                    <!-- 调整图例顺序与颜色：日前高为绿，实时高为红 -->
                    <div class="legend-block">
                        <span class="legend-label">日前 &gt; 实时（绿）</span>
                        <div class="legend-bar spread-pos"></div>
                    </div>
                    <div class="legend-block">
                        <span class="legend-label">实时 &gt; 日前（红）</span>
                        <div class="legend-bar spread-neg"></div>
                    </div>
                </template>
            </div>

            <div v-if="overallAvg != null" class="overall-avg">
                全部时段总均值：
                <strong>{{ overallAvg.toFixed(3) }}</strong> 元/MWh
                <span v-if="dailyAvg.length" class="avg-count">
                    （{{ cellCount }} 个有效时段）
                </span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, type CSSProperties } from 'vue'


interface Props {
    dates: string[]
    hours: string[]
    matrix: (number | null)[][]
    mode?: 'price' | 'spread'
    basePrice?: number
    showDailyAvg?: boolean
    dailyAvg?: (number | null)[],
    showPositiveRatio?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    mode: 'price',
    basePrice: 350,
    showDailyAvg: true,
    dailyAvg: () => [],
    showPositiveRatio: false,
})

/* ---------------- 过滤掉末尾多余的空行 & 深度清洗数据 ---------------- */
const displayMatrix = computed(() => {
    const len = Math.min(props.hours.length, props.matrix.length)
    // ⭐ 核心：深度清洗，把所有的字符串、空值、NaN 都转为 null，保证全是纯数字
    let m = props.matrix.slice(0, len).map(row =>
        row.map(v => {
            if (v == null) return null
            const num = Number(v)
            return isNaN(num) ? null : num
        })

    )
    if (m.length > 1 && m[m.length - 1].every((v) => v == null)) {
        m = m.slice(0, -1)
    }
    return m
})

const displayHours = computed(() => {
    return props.hours.slice(0, displayMatrix.value.length)
})
/* ---------------- ⭐ 内部重算日均值（彻底解决 - 的问题） ---------------- */
const realDailyAvg = computed<(number | null)[]>(() => {
    return props.dates.map((_, dIdx) => {
        const col = displayMatrix.value
            .map((row) => row[dIdx])
            .filter((v): v is number => v !== null)
        if (!col.length) return null
        const sum = col.reduce((a, b) => a + b, 0)
        if (!isFinite(sum)) return null
        return Math.round((sum / col.length) * 1000) / 1000
    })
})

/* ---------------- 动态高度策略 ---------------- */
const wrapStyle = computed<CSSProperties>(() => {
    return { height: 'calc(100vh - 210px)', display: 'flex', flexDirection: 'column' }
})


/* ---------------- 布局：行高列宽自动均分 ---------------- */
const gridStyle = computed(() => {
    const cols = props.dates.length
    const rows = displayHours.value.length + (props.showDailyAvg && realDailyAvg.value.length ? 1 : 0)
    return {
        // ⭐ 增加 48px 时间列 + 70px 占比列 + 70px 总和列 + 日期列
        gridTemplateColumns: `48px 70px 70px repeat(${cols}, minmax(0, 1fr))`,
        gridTemplateRows: `24px repeat(${rows}, minmax(0, 1fr))`,
    }
})

/* ---------------- 单元格字号：日期越多越小 ---------------- */
const cellFontSize = computed(() => {
    const cols = props.dates.length
    if (cols <= 10) return '10px'
    if (cols <= 20) return '9px'
    if (cols <= 40) return '8px'
    return '7px'
})

/* ---------------- 悬浮放大：尺寸计算 ---------------- */
const HOVER_FONT_SIZE = 13
const HOVER_EXTRA_RATIO = 1.15
const HOVER_TARGET_WIDTH = 56
const gridRef = ref<HTMLElement | null>(null)
const gridWidth = ref(0)
let ro: ResizeObserver | null = null

const cellWidth = computed(() => {
    const cols = props.dates.length
    if (!cols) return 30
    const total = gridWidth.value || 900
    const avail = total - 48 - cols
    return Math.max(avail / cols, 8)
})

/* ---------------- 数字格式：日期多时只显示整数 ---------------- */
const decimalDigits = computed(() => {
    return props.dates.length <= 15 ? 1 : 0
})

const rowStats = computed(() => {
    const posRatio: string[] = []
    const sum: string[] = []
    for (let i = 0; i < displayMatrix.value.length; i++) {
        let valid = 0, positive = 0, total = 0
        for (const v of displayMatrix.value[i]) {
            if (v != null) {
                valid++
                if (v > 0) positive++
                total += v
            }
        }
        posRatio.push(valid === 0 ? '-' : ((positive / valid) * 100).toFixed(2) + '%')
        sum.push(valid === 0 ? '-' : total.toFixed(2))
    }
    return { posRatio, sum }
})
const rowPosRatio = computed(() => rowStats.value.posRatio)
const rowSum = computed(() => rowStats.value.sum)

function formatCell(v: number | string | null | undefined): string {
    if (v == null || v === '') return ''
    const num = Number(v)
    if (isNaN(num)) return '' // 如果是无法转成数字的字符串，直接显示空白，不再显示 '-'
    return num.toFixed(decimalDigits.value)
}

/* ---------------- 日期简写 ---------------- */
function shortDate(d: string): string {
    if (!d) return ''
    return d.slice(5).replace('-', '/')
}

/* ---------------- 有效单元格数 / 均值 / 色阶范围 ---------------- */
const cellCount = computed(() => {
    let n = 0
    for (const row of displayMatrix.value) {
        for (const v of row) {
            if (v != null) n++
        }
    }
    return n
})

const overallAvg = computed<number | null>(() => {
    const vals: number[] = []
    for (const row of displayMatrix.value) {
        for (const v of row) {
            if (v != null) vals.push(v) // 直接用清洗后的数据
        }
    }
    if (!vals.length) return null
    const sum = vals.reduce((a, b) => a + b, 0)
    return Math.round((sum / vals.length) * 1000) / 1000
})

const priceRange = computed(() => {
    const base = props.basePrice
    let maxAbove = 1
    let maxBelow = 1
    for (const row of displayMatrix.value) {
        for (const v of row) {
            if (v == null) continue
            const d = v - base // 直接用清洗后的数据
            if (d > 0 && d > maxAbove) maxAbove = d
            if (d < 0 && -d > maxBelow) maxBelow = -d
        }
    }
    return { base, maxAbove, maxBelow }
})

const spreadRange = computed(() => {
    let maxPos = 0.001
    let maxNeg = 0.001
    for (const row of displayMatrix.value) {
        for (const v of row) {
            if (v == null) continue
            if (v > maxPos) maxPos = v // 直接用清洗后的数据
            if (v < 0 && -v > maxNeg) maxNeg = -v
        }
    }
    return { maxPos, maxNeg }
})

// 记录价差总和的极值，用于色阶映射
const sumAbsMax = computed(() => {
    let max = 1
    for (const s of rowSum.value) {
        if (s !== '-') {
            const v = Math.abs(Number(s))
            if (v > max) max = v
        }
    }
    return max
})

// ⭐ 正价差占比色阶（以 50% 为基准，深红/深绿底 + 白字）
function ratioStyle(ratioStr: string) {
    if (ratioStr === '-') return { background: '#fafbfc', color: 'transparent' }
    const ratio = parseFloat(ratioStr)
    const delta = ratio - 50
    const t = Math.min(1, Math.abs(delta) / 50)
    const l = 85 - 45 * t
    const s = Math.max(40, 50 + 40 * t)

    // ⭐ 强制黑色加粗
    const textStyle = { color: '#000000', fontWeight: 'bold' }
    if (delta > 0) return { background: `hsl(0, ${s}%, ${l}%)`, ...textStyle }
    if (delta < 0) return { background: `hsl(130, ${s}%, ${l}%)`, ...textStyle }
    return { background: '#eef0f3', ...textStyle }
}
// ⭐ 价差总和色阶（以 0 为基准，深红/深绿底 + 白字）
function sumStyle(sumStr: string) {
    if (sumStr === '-') return { background: '#fafbfc', color: 'transparent' }
    const sum = Number(sumStr)
    if (Math.abs(sum) < 0.01) return { background: '#eef0f3', color: '#000000', fontWeight: 'bold' }

    const t = Math.min(1, Math.abs(sum) / (sumAbsMax.value || 1))
    const l = 85 - 45 * t
    const s = Math.max(40, 50 + 40 * t)

    // ⭐ 强制黑色加粗
    const textStyle = { color: '#000000', fontWeight: 'bold' }
    if (sum > 0) return { background: `hsl(0, ${s}%, ${l}%)`, ...textStyle }
    return { background: `hsl(130, ${s}%, ${l}%)`, ...textStyle }
}
/* ---------------- 单元格背景色（简化判断逻辑） ---------------- */
function cellBg(v: number | null, isAvg = false): string {
    if (v == null) return '#f5f7fa' // 因为传进来的值已经是 number | null 了

    if (props.mode === 'price') {
        const { base, maxAbove, maxBelow } = priceRange.value
        const delta = v - base
        if (Math.abs(delta) < 0.01) return '#eef0f3'

        const satAdj = isAvg ? -20 : 0

        if (delta > 0) {
            const t = Math.min(1, delta / maxAbove)
            const s = Math.max(20, 65 + 30 * t + satAdj)
            const l = 92 - 46 * t
            return `hsl(0, ${s}%, ${l}%)`
        } else {
            const t = Math.min(1, -delta / maxBelow)
            const s = Math.max(20, 55 + 30 * t + satAdj)
            const l = 92 - 46 * t
            return `hsl(130, ${s}%, ${l}%)`
        }
    }

    // ==== 价差模式色阶 ====
    const { maxPos, maxNeg } = spreadRange.value
    const satAdj = isAvg ? -20 : 0

    if (v > 0) {
        const t = Math.min(1, v / maxPos)
        const s = Math.max(20, 55 + 30 * t + satAdj)
        const l = 92 - 46 * t
        return `hsl(130, ${s}%, ${l}%)`
    } else if (v < 0) {
        const t = Math.min(1, -v / maxNeg)
        const s = Math.max(20, 65 + 30 * t + satAdj)
        const l = 92 - 46 * t
        return `hsl(0, ${s}%, ${l}%)`
    }
    return '#eef0f3'
}

onMounted(() => {
    if (!gridRef.value) return
    gridWidth.value = gridRef.value.clientWidth
    if (typeof ResizeObserver !== 'undefined') {
        ro = new ResizeObserver((entries) => {
            const w = entries[0]?.contentRect.width ?? 0
            if (w) gridWidth.value = w
        })
        ro.observe(gridRef.value)
    }
})
onBeforeUnmount(() => {
    ro?.disconnect()
    ro = null
})
</script>

<style scoped>
.heat-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
    background: #fff;
    border-radius: 6px;
    padding: 10px 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.heat-scroll {
    flex: 1;
    overflow: auto;
    border: 1px solid #eef0f3;
    border-radius: 4px;
    position: relative;
}

.heat-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 11px;
    text-align: center;
    table-layout: fixed;
}

.heat-table th,
.heat-table td {
    border-right: 1px solid #eef0f3;
    border-bottom: 1px solid #eef0f3;
    height: 26px;
    padding: 0 4px;
    min-width: 60px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.heat-table th {
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 10;
}

.heat-table tr:hover td {
    background-color: rgba(0, 0, 0, 0.02);
}

/* 冻结列 */
.sticky-col {
    position: sticky;
    background: #f8f9fb;
    z-index: 11;
    font-weight: 500;
}

.col-time {
    left: 0;
    width: 60px;
    min-width: 60px;
}

.col-stat {
    width: 70px;
    min-width: 70px;
    background: #fdf6ec;
    color: #e6a23c;
    font-weight: 600;
}

/* 冻结表头和表头的左上交叉 */
.heat-table th.sticky-col {
    z-index: 20;
    background: #f5f7fa;
}

.heat-table th.col-stat {
    background: #fdf6ec;
}

/* 冻结底部行 */
.sticky-bottom-row td {
    position: sticky;
    bottom: 0;
    z-index: 11;
    background: #fff;
    border-top: 2px solid #dcdfe6;
}

.sticky-bottom-row .sticky-col {
    z-index: 20;
}

/* 悬浮放大效果 */
.cell-content {
    display: inline-block;
    padding: 2px 4px;
    border-radius: 2px;
    transition: transform 0.1s;
}

td:hover .cell-content {
    transform: scale(1.4);
    background: inherit;
    font-weight: bold;
    position: relative;
    z-index: 30;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    outline: 1px solid #1f2d3d;
}

.empty-cell {
    background: #fafbfc !important;
    color: transparent;
}

/* ============ 底部：图例 + 总均值 ============ */
.bottom-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
    padding-top: 4px;
    border-top: 1px solid #f0f2f5;
    font-size: 12px;
    color: #606266;
}

.legend {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}

.legend-block {
    display: flex;
    align-items: center;
    gap: 8px;
}

.legend-label {
    font-size: 12px;
    color: #606266;
    white-space: nowrap;
}

.legend-bar {
    width: 130px;
    height: 12px;
    border-radius: 6px;
    border: 1px solid #ebeef5;
}

/* 修正图例的色带：绿和红的分配 */
.legend-bar.price-low,
.legend-bar.spread-pos {
    background: linear-gradient(90deg, hsl(130, 25%, 92%), hsl(130, 85%, 46%));
}

.legend-bar.price-high,
.legend-bar.spread-neg {
    background: linear-gradient(90deg, hsl(0, 35%, 92%), hsl(0, 95%, 46%));
}

.overall-avg {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}

.overall-avg strong {
    color: #2d6cdf;
    font-size: 14px;
    font-weight: 700;
}

.avg-count {
    margin-left: 6px;
    color: #909399;
    font-size: 12px;
}

.stat-cell {
    background: #fdf6ec;
    color: #e6a23c;
    font-weight: 600;
}
</style>