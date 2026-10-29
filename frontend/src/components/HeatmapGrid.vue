<template>
    <!-- 绑定动态样式，控制容器高度 -->
    <div class="heat-wrap" :style="wrapStyle">
        <div ref="gridRef" class="heat-grid" :style="gridStyle">
            <!-- 表头 -->
            <div class="cell corner">时间\日期</div>
            <div v-for="d in dates" :key="'h-' + d" class="cell date-cell" :title="d">
                {{ shortDate(d) }}
            </div>

            <!-- 行标签 + 数据行 -->
            <template v-for="(h, hIdx) in displayHours" :key="'r-' + hIdx">
                <div class="cell row-label">{{ h }}</div>
                <div v-for="(d, dIdx) in dates" :key="'c-' + hIdx + '-' + dIdx" class="cell data-cell"
                    :class="{ empty: displayMatrix[hIdx]?.[dIdx] == null }" :style="{
                        background: cellBg(displayMatrix[hIdx]?.[dIdx]),
                        fontSize: cellFontSize,
                        '--hover-inset-x': hoverInsetX,
                    }">
                    <span class="cell-num">{{ formatCell(displayMatrix[hIdx]?.[dIdx]) }}</span>
                </div>
            </template>

            <!-- 日均值行 -->
            <template v-if="showDailyAvg && dailyAvg.length">
                <div class="cell row-label avg-label">日均</div>
                <div v-for="(d, dIdx) in dates" :key="'avg-' + dIdx" class="cell data-cell avg-cell"
                    :class="{ empty: dailyAvg[dIdx] == null }" :style="{
                        background: cellBg(dailyAvg[dIdx], true),
                        fontSize: cellFontSize,
                        '--hover-inset-x': hoverInsetX,
                    }">
                    <span class="cell-num">{{ formatCell(dailyAvg[dIdx]) }}</span>
                </div>
            </template>
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
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'

interface Props {
    dates: string[]
    hours: string[]
    matrix: (number | null)[][]
    mode?: 'price' | 'spread'
    basePrice?: number
    showDailyAvg?: boolean
    dailyAvg?: (number | null)[]
}

const props = withDefaults(defineProps<Props>(), {
    mode: 'price',
    basePrice: 350,
    showDailyAvg: true,
    dailyAvg: () => [],
})

/* ---------------- 过滤掉末尾多余的空行 ---------------- */
const displayMatrix = computed(() => {
    const len = Math.min(props.hours.length, props.matrix.length)
    let m = props.matrix.slice(0, len)
    if (m.length > 1 && m[m.length - 1].every((v) => v == null)) {
        m = m.slice(0, -1)
    }
    return m
})

const displayHours = computed(() => {
    return props.hours.slice(0, displayMatrix.value.length)
})

/* ---------------- 动态高度策略 ---------------- */
// 大于24行（即48点价差数据）时，取消固定视口高度，允许随内容撑开变大
const isLargeGrid = computed(() => displayHours.value.length > 24)

const wrapStyle = computed(() => {
    return isLargeGrid.value
        ? { height: 'auto', minHeight: 'auto' }
        : { height: 'calc(100vh - 240px)', minHeight: '520px' }
})

/* ---------------- 布局：行高列宽自动均分 ---------------- */
const gridStyle = computed(() => {
    const cols = props.dates.length
    const rows = displayHours.value.length + (props.showDailyAvg && props.dailyAvg.length ? 1 : 0)

    // 48点数据时，给每行限制最小高度 24px，避免挤压；24点数据时均分充满容器
    const rowTemplate = isLargeGrid.value ? 'minmax(24px, 1fr)' : 'minmax(0, 1fr)'

    return {
        gridTemplateColumns: `48px repeat(${cols}, minmax(0, 1fr))`,
        gridTemplateRows: `24px repeat(${rows}, ${rowTemplate})`,
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

const hoverInsetX = computed(() => {
    const origFont = parseFloat(cellFontSize.value) || 10
    const ratioByFont = (HOVER_FONT_SIZE / origFont) * HOVER_EXTRA_RATIO
    const ratioByFit = HOVER_TARGET_WIDTH / cellWidth.value
    const ratio = Math.min(ratioByFont, Math.max(1, ratioByFit))
    return `-${(((ratio - 1) / 2) * 100).toFixed(1)}%`
})

/* ---------------- 数字格式：日期多时只显示整数 ---------------- */
const decimalDigits = computed(() => {
    return props.dates.length <= 15 ? 1 : 0
})

function formatCell(v: number | null): string {
    if (v == null) return ''
    return v.toFixed(decimalDigits.value)
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
            if (v != null) vals.push(v)
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
            const d = v - base
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
            if (v > maxPos) maxPos = v
            if (v < 0 && -v > maxNeg) maxNeg = -v
        }
    }
    return { maxPos, maxNeg }
})

/* ---------------- 单元格背景色 ---------------- */
function cellBg(v: number | null, isAvg = false): string {
    if (v == null) return '#f5f7fa'

    if (props.mode === 'price') {
        const { base, maxAbove, maxBelow } = priceRange.value
        const delta = v - base
        if (Math.abs(delta) < 0.01) return '#eef0f3'

        const satAdj = isAvg ? -20 : 0

        if (delta > 0) {
            const t = Math.min(1, delta / maxAbove)
            const s = Math.max(20, 65 + 30 * t + satAdj)
            const l = 92 - 46 * t
            return `hsl(0, ${s}%, ${l}%)` // 高于基准：红色
        } else {
            const t = Math.min(1, -delta / maxBelow)
            const s = Math.max(20, 55 + 30 * t + satAdj)
            const l = 92 - 46 * t
            return `hsl(130, ${s}%, ${l}%)` // 低于基准：绿色
        }
    }

    // ==== 价差模式色阶 ====
    const { maxPos, maxNeg } = spreadRange.value
    const satAdj = isAvg ? -20 : 0

    if (v > 0) {
        // 价差 > 0：日前 > 实时，绿色
        const t = Math.min(1, v / maxPos)
        const s = Math.max(20, 55 + 30 * t + satAdj)
        const l = 92 - 46 * t
        return `hsl(130, ${s}%, ${l}%)`
    } else if (v < 0) {
        // 价差 < 0：实时 > 日前，红色
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

.heat-grid {
    flex: 1;
    display: grid;
    gap: 1px;
    background: #eef0f3;
    border: 1px solid #eef0f3;
    border-radius: 4px;
    min-height: 0;
}

/* ============ 单元格通用 ============ */
.cell {
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    user-select: none;
}

/* ============ 表头 ============ */
.corner,
.date-cell {
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.corner {
    z-index: 2;
}

/* ============ 行标签（时间列） ============ */
.row-label {
    background: #f5f7fa;
    color: #303133;
    font-weight: 500;
    font-size: 11px;
}

.avg-label {
    background: #ecf5ff;
    color: #2d6cdf;
    font-weight: 600;
}

/* ============ 数据单元格 ============ */
.data-cell {
    cursor: crosshair;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
    z-index: 1;
}

.data-cell.empty {
    background: #fafbfc !important;
}

/* ============ 悬浮放大 ============ */
.data-cell:hover {
    transform: none;
    overflow: visible;
    z-index: 30;
    font-size: 13px !important;
    font-weight: 700;
}

.data-cell:hover::after {
    content: '';
    position: absolute;
    inset: -50% var(--hover-inset-x, 0);
    background: inherit;
    border-radius: 3px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.32);
    outline: 2px solid #1f2d3d;
    outline-offset: -2px;
    z-index: -1;
    pointer-events: none;
}

/* ============ 单元格数字 ============ */
.cell-num {
    font-size: inherit;
    font-weight: 500;
    color: #1f2d3d;
    pointer-events: none;
    white-space: nowrap;
    line-height: 1;
    text-shadow: 0 0 1px rgba(255, 255, 255, 0.9);
}

.data-cell.empty .cell-num {
    color: transparent;
}

/* ============ 底部：图例 + 总均值 ============ */
.bottom-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
    padding-top: 6px;
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
</style>