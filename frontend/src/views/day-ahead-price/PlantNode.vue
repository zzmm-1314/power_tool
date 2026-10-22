<template>
    <PageContainer title="日前电价 · 电厂节点">
        <template #extra>
            <!-- 组 1：操作 -->
            <div class="extra-group">
                <button class="btn-upload" @click="appStore.openUpload('day-ahead-plant')">
                    📤 上传 Excel
                </button>
                <DataSourceTag :source="source" />
                <button class="btn" @click="refreshAll">刷新</button>
            </div>

            <!-- 组 2：节点 -->
            <div class="extra-group">
                <label class="lbl">节点</label>
                <select v-model="nodeName" class="input select" :disabled="!nodes.length" @change="load">
                    <option value="">
                        {{ nodes.length ? '请选择电厂节点' : '暂无可用节点' }}
                    </option>
                    <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>

            <!-- 组 3：日期 -->
            <div class="extra-group extra-group-break">
                <label class="lbl">日期</label>
                <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                    @update:end="dateEnd = $event" />
            </div>
        </template>

        <p v-if="!nodes.length" class="empty-tip">
            暂无节点数据，请点击右上角「📤 上传 Excel」上传
            <code>日前市场出清节点电价YYYYMMDD.xlsx</code>
        </p>

        <p v-else-if="!nodeName" class="empty-tip">请选择上方节点后查看热力图</p>

        <p v-else-if="!heatmap.dates.length" class="empty-tip">
            节点「{{ nodeName }}」在该时间段内无数据
        </p>

        <div v-else class="table-wrap" :class="{ loading }">
            <table class="price-table">
                <thead>
                    <tr>
                        <th class="sticky-col corner">时间 \ 日期</th>
                        <th v-for="d in heatmap.dates" :key="d" class="date-th">{{ d }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(hour, hIdx) in heatmap.hours" :key="hour">
                        <td class="sticky-col hour-td">{{ hour }}</td>
                        <td v-for="(d, dIdx) in heatmap.dates" :key="d" class="value-td"
                            :class="{ empty: heatmap.matrix[hIdx][dIdx] == null }" :style="{
                                background: cellBg(heatmap.matrix[hIdx][dIdx]),
                                color: cellFg(heatmap.matrix[hIdx][dIdx]),
                            }" :title="`${d} ${hour}：${formatVal(heatmap.matrix[hIdx][dIdx])} 元/MWh`">
                            {{ formatVal(heatmap.matrix[hIdx][dIdx]) }}
                        </td>
                    </tr>

                    <tr class="avg-row">
                        <td class="sticky-col avg-label">
                            <span class="avg-icon">∑</span> 日均值
                        </td>
                        <td v-for="(d, dIdx) in heatmap.dates" :key="d" class="value-td avg-value" :style="{
                            background: cellBg(dailyAvg[dIdx], true),
                            color: cellFg(dailyAvg[dIdx], true),
                        }" :title="`${d} 日均值：${formatVal(dailyAvg[dIdx])} 元/MWh`">
                            {{ formatVal(dailyAvg[dIdx]) }}
                        </td>
                    </tr>
                </tbody>
            </table>

            <div class="overall-avg">
                节点「{{ nodeName }}」全部时段总均值：
                <strong>{{ formatVal(overallAvg) }}</strong> 元/MWh
            </div>
        </div>

        <div v-if="heatmap.dates.length" class="legend-bar-wrap">
            <span class="legend-label">低</span>
            <div class="legend-bar"></div>
            <span class="legend-label">高</span>
            <span class="legend-range">
                {{ heatmap.minValue }} ~ {{ heatmap.maxValue }} 元/MWh
            </span>
        </div>

        <TempDataPanel data-type="day-ahead" sub-type="plant" :node-name="nodeName" />
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import DataSourceTag from '@/components/DataSourceTag.vue'
import TempDataPanel from '@/components/TempDataPanel.vue'
import {
    fetchPlantHeatmap,
    fetchPlantNodes,
    type HeatmapData,
} from '@/api/modules/price'
import type { DataSource } from '@/types'
import { useAppStore } from '@/stores/app'
import { listPlantNodes } from '@/api/modules/nodes'
import DateRangeInput from '@/components/DateRangeInput.vue'
const appStore = useAppStore()

const loading = ref(false)
const dateStart = ref('')
const dateEnd = ref('')
const nodes = ref<string[]>([])
const nodeName = ref('')
const source = ref<DataSource>('empty')
const heatmap = ref<HeatmapData>({
    dates: [],
    hours: [],
    matrix: [],
    source: 'empty',
    minValue: 0,
    maxValue: 0,
})

/* ---------- 每日均值（3 位） ---------- */
const dailyAvg = computed<(number | null)[]>(() => {
    return heatmap.value.dates.map((_, dIdx) => {
        const col = heatmap.value.matrix
            .map((row) => row[dIdx])
            .filter((v): v is number => v != null)
        if (!col.length) return null
        const sum = col.reduce((a, b) => a + b, 0)
        return Math.round((sum / col.length) * 1000) / 1000
    })
})

/* ---------- 总均值（3 位） ---------- */
const overallAvg = computed<number | null>(() => {
    const all: number[] = []
    heatmap.value.matrix.forEach((row) => {
        row.forEach((v) => {
            if (v != null) all.push(v)
        })
    })
    if (!all.length) return null
    return Math.round((all.reduce((a, b) => a + b, 0) / all.length) * 1000) / 1000
})

/* ---------- 色阶（与统一结算点保持一致） ---------- */
const range = computed(() => {
    const min = heatmap.value.minValue
    const max = heatmap.value.maxValue
    return { min, max, span: max - min || 1 }
})
// 初始化：默认最近 14 天（含今天）
function initDateRange() {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 13)
    dateEnd.value = fmtDate(end)
    dateStart.value = fmtDate(start)
}

function fmtDate(d: Date): string {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${dd}`
}
function cellBg(v: number | null, isAvg = false): string {
    if (v == null) return '#fafbfc'
    const { min, span } = range.value
    const t = Math.max(0, Math.min(1, (v - min) / span))
    const satAdj = isAvg ? -18 : 0
    if (t < 0.5) {
        const k = t / 0.5
        const h = 120 - 65 * k
        const s = 62 + 23 * k + satAdj
        return `hsl(${h}, ${Math.max(20, s)}%, 86%)`
    }
    const k = (t - 0.5) / 0.5
    const h = 55 - 55 * k
    const s = 85 - 15 * k + satAdj
    return `hsl(${h}, ${Math.max(20, s)}%, 88%)`
}

function cellFg(v: number | null, isAvg = false): string {
    if (v == null) return '#c0c4cc'
    const { min, span } = range.value
    const t = Math.max(0, Math.min(1, (v - min) / span))
    if (isAvg) return '#1f2d3d'
    return t > 0.98 ? '#fff' : '#303133'
}

function formatVal(v: number | null): string {
    if (v == null) return '—'
    return v.toFixed(3)
}

/* ---------- 数据加载 ---------- */
async function loadNodes() {
    try {
        const list = await listPlantNodes()
        nodes.value = list.map((n) => n.name)
        if (!nodeName.value && nodes.value.length) {
            nodeName.value = nodes.value[0]
        }
    } catch {
        nodes.value = []
    }
}

async function load() {
    if (!nodeName.value) {
        heatmap.value = {
            dates: [],
            hours: [],
            matrix: [],
            source: 'empty',
            minValue: 0,
            maxValue: 0,
        }
        return
    }

    loading.value = true
    try {
        const data = await fetchPlantHeatmap({
            nodeName: nodeName.value,
            startDate: dateStart.value,
            endDate: dateEnd.value,
        })
        heatmap.value = data
        source.value = data.source
    } catch (e) {
        console.error(e)
        source.value = 'empty'
        heatmap.value = {
            dates: [],
            hours: [],
            matrix: [],
            source: 'empty',
            minValue: 0,
            maxValue: 0,
        }
    } finally {
        loading.value = false
    }
}

async function refreshAll() {
    await loadNodes()
    await load()
}

watch(() => appStore.dataVersion, () => refreshAll())

onMounted(() => {
    initDateRange()
    refreshAll()
})
</script>

<style scoped>
.extra-group {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
    min-width: 0;
}

/* 强制独占一行 */
.extra-group-break {
    flex-basis: 100%;
    justify-content: flex-end;
    width: 100%;
}

.select {
    max-width: 180px;
}

.lbl {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}

.input {
    height: 30px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
}

.input:disabled {
    background: #f5f7fa;
    color: #c0c4cc;
}

.btn {
    height: 30px;
    padding: 0 14px;
    border: none;
    border-radius: 4px;
    background: #2d6cdf;
    color: #fff;
    cursor: pointer;
}

.empty-tip {
    padding: 40px 16px;
    text-align: center;
    color: #909399;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.empty-tip code {
    padding: 1px 6px;
    background: #f4f4f5;
    border-radius: 3px;
    color: #606266;
    font-size: 12px;
}

/* ================= 表格 ================= */
.table-wrap {
    position: relative;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    overflow: auto;
    max-height: 640px;
}

.table-wrap.loading {
    opacity: 0.6;
}

.price-table {
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
    width: 100%;
}

.price-table th,
.price-table td {
    padding: 6px 10px;
    text-align: center;
    white-space: nowrap;
    border-right: 1px solid #eef0f3;
    border-bottom: 1px solid #eef0f3;
}

.price-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    font-size: 12px;
}

.price-table .date-th {
    min-width: 88px;
}

.sticky-col {
    position: sticky;
    left: 0;
    z-index: 3;
    background: #f5f7fa !important;
    color: #303133;
    font-weight: 500;
}

.corner {
    z-index: 4;
    top: 0;
    left: 0;
    min-width: 100px;
}

.value-td {
    min-width: 88px;
    font-variant-numeric: tabular-nums;
    cursor: default;
}

.value-td:hover {
    outline: 2px solid #2d6cdf;
    outline-offset: -2px;
    position: relative;
    z-index: 1;
}

.value-td.empty {
    color: #c0c4cc;
}

.avg-row td {
    border-top: 2px solid #dcdfe6;
    font-weight: 600;
}

.avg-label {
    background: #ecf5ff !important;
    color: #2d6cdf;
    font-size: 13px;
}

.avg-icon {
    font-size: 12px;
    margin-right: 2px;
    opacity: 0.75;
}

.avg-value {
    border-top: 2px solid #dcdfe6;
    font-size: 12.5px;
}

.overall-avg {
    position: sticky;
    left: 0;
    padding: 10px 16px;
    background: #fafbfc;
    border-top: 1px solid #f0f2f5;
    font-size: 12px;
    color: #606266;
}

.overall-avg strong {
    color: #2d6cdf;
    font-size: 13px;
}

/* ================= 色阶 ================= */
.legend-bar-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.legend-bar {
    flex: 0 0 260px;
    height: 14px;
    border-radius: 7px;
    background: linear-gradient(to right,
            hsl(120, 62%, 86%),
            hsl(55, 85%, 88%),
            hsl(0, 70%, 78%));
    border: 1px solid #ebeef5;
}

.legend-label {
    font-size: 12px;
    color: #606266;
}

.legend-range {
    margin-left: auto;
    font-size: 12px;
    color: #909399;
}

:deep(.date-range .input) {
    height: 30px;
    font-size: 13px;
}
</style>