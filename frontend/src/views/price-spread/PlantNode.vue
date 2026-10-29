<template>
    <PageContainer title="价差分析 · 电厂节点（48 点）">
        <template #extra>
            <div class="extra-group">
                <button class="btn-upload" @click="appStore.openUpload('spread-plant')">
                    📤 上传实时节点价格
                </button>
                <DataSourceTag :source="source" />
                <button class="btn" @click="refreshAll">刷新</button>
            </div>

            <div class="extra-group">
                <label class="lbl">节点</label>
                <select v-model="nodeName" class="input select" :disabled="!nodes.length" @change="load">
                    <option value="">
                        {{ nodes.length ? '请选择电厂节点' : '暂无可用节点' }}
                    </option>
                    <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>

            <div class="extra-group extra-group-break">
                <label class="lbl">日期</label>
                <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                    @update:end="dateEnd = $event" />
            </div>
        </template>

        <p v-if="!nodes.length" class="empty-tip">
            暂无节点数据，请先在「节点编辑」中添加节点，再上传日前 / 实时节点价格。
        </p>

        <p v-else-if="!nodeName" class="empty-tip">请选择上方节点后查看热力图</p>

        <p v-else-if="!heatmap.dates.length" class="empty-tip">
            节点「{{ nodeName }}」在所选时间段内没有同时存在「日前节点」和「实时节点」的数据
        </p>
        <template v-else>
            <!-- ===== 新增：日前 vs 实时 折线图 ===== -->
            <div class="daily-chart-card">
                <div class="daily-chart-header">
                    <span class="daily-chart-title">
                        「{{ nodeName }}」日前 vs 实时价格曲线
                    </span>
                    <div class="daily-chart-controls">
                        <label class="daily-lbl">日期</label>
                        <select v-model="dailyDate" class="input" @change="loadDailyPrices">
                            <option v-for="d in heatmap.dates" :key="d" :value="d">
                                {{ d }}
                            </option>
                        </select>
                        <span v-if="dailyLoading" class="daily-loading">加载中...</span>
                    </div>
                </div>
                <div class="daily-chart-body">
                    <VChart v-if="dailyPrices.dayAhead.length" :option="lineChartOption" autoresize
                        class="daily-chart" />
                    <div v-else class="daily-chart-empty">该日期无日前 / 实时数据</div>
                </div>
            </div>

            <!-- ===== 新热力图 ===== -->
            <HeatmapGrid mode="spread" :dates="heatmap.dates" :hours="heatmap.hours" :matrix="heatmap.matrix"
                :daily-avg="dailyAvg" />
        </template>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import DataSourceTag from '@/components/DataSourceTag.vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import {
    fetchSpreadPlantHeatmap,
    type SpreadHeatmapData,
    fetchSpreadDailyPrices,
    type SpreadDailyPrices,
} from '@/api/modules/spread'
import { listPlantNodes } from '@/api/modules/nodes'
import type { DataSource } from '@/types'
import { useAppStore } from '@/stores/app'
import DateRangeInput from '@/components/DateRangeInput.vue'
import HeatmapGrid from '@/components/HeatmapGrid.vue'
const appStore = useAppStore()

const loading = ref(false)
const dateStart = ref('')
const dateEnd = ref('')
const nodes = ref<string[]>([])
const nodeName = ref('')
const source = ref<DataSource>('empty')
const dailyDate = ref('')
const dailyLoading = ref(false)
const dailyPrices = ref<SpreadDailyPrices>({
    date: '', hours: [], dayAhead: [], realTime: [], spread: [], source: 'empty',
})

const lineChartOption = computed<EChartsOption>(() => {
    const dp = dailyPrices.value
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (v) =>
                typeof v === 'number' ? `${v.toFixed(3)} 元/MWh` : '—',
        },
        legend: { top: 0, data: ['日前价格', '实时价格'] },
        grid: { left: 64, right: 24, top: 36, bottom: 42 },
        xAxis: {
            type: 'category',
            data: dp.hours,
            axisLabel: { interval: 3, fontSize: 11 },
        },
        yAxis: {
            type: 'value',
            name: '元/MWh',
            nameTextStyle: { color: '#606266' },
            axisLabel: { color: '#606266' },
        },
        dataZoom: [{ type: 'inside' }],
        series: [
            {
                name: '日前价格',
                type: 'line',
                smooth: true,
                showSymbol: false,
                data: dp.dayAhead,
                itemStyle: { color: '#2d6cdf' },
                lineStyle: { width: 2 },
                z: 3,
            },
            {
                name: '实时价格',
                type: 'line',
                smooth: true,
                showSymbol: false,
                data: dp.realTime,
                itemStyle: { color: '#e6a23c' },
                lineStyle: { width: 2 },
                z: 2,
            },
        ],
    }
})
const heatmap = ref<SpreadHeatmapData>({
    dates: [],
    hours: [],
    matrix: [],
    source: 'empty',
    minValue: 0,
    maxValue: 0,
})

/* ---------- 每日均价差（3 位） ---------- */
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
async function loadDailyPrices() {
    if (!dailyDate.value || !nodeName.value) {
        dailyPrices.value = {
            date: '', hours: [], dayAhead: [], realTime: [], spread: [], source: 'empty',
        }
        return
    }
    dailyLoading.value = true
    try {
        const data = await fetchSpreadDailyPrices({
            date: dailyDate.value,
            nodeType: 'plant',
            nodeName: nodeName.value,
        })
        dailyPrices.value = data
    } catch (e) {
        console.error(e)
        dailyPrices.value = {
            date: '', hours: [], dayAhead: [], realTime: [], spread: [], source: 'empty',
        }
    } finally {
        dailyLoading.value = false
    }
}
/* ---------- 加载 ---------- */
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
        const data = await fetchSpreadPlantHeatmap({
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
// 节点切换：清空日期和折线数据，等热力图重新加载后由下面的 watch 自动重新绘制
watch(nodeName, () => {
    dailyDate.value = ''
    dailyPrices.value = {
        date: '',
        hours: [],
        dayAhead: [],
        realTime: [],
        spread: [],
        source: 'empty',
    }
})

// 热力图日期更新：无论节点是否变化，都重新加载折线图
watch(
    () => heatmap.value.dates,
    (dates) => {
        if (!dates.length) {
            dailyDate.value = ''
            dailyPrices.value = {
                date: '',
                hours: [],
                dayAhead: [],
                realTime: [],
                spread: [],
                source: 'empty',
            }
            return
        }

        // 若当前选中日期不在新列表里（例如切换节点后日期集合变了），重置为最后一天
        if (!dailyDate.value || !dates.includes(dailyDate.value)) {
            dailyDate.value = dates[dates.length - 1]
        }

        // ⚠ 关键：无条件重新加载折线图
        // 因为节点切换后，即使 dailyDate 名称相同，日前/实时数据也完全不同
        loadDailyPrices()
    },
)
watch(() => appStore.dataVersion, () => refreshAll())
onMounted(refreshAll)
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

.select {
    max-width: 220px;
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
    line-height: 1.8;
}

/* ================= 表格 ================= */
.table-wrap {
    position: relative;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    overflow: auto;
    max-height: 720px;
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

/* ================= 双向色阶图例 ================= */
.legend-bar-wrap {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 10px 16px;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    flex-wrap: wrap;
}

.legend-block {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.legend-tip {
    font-size: 12px;
    color: #606266;
}

.legend-bar {
    width: 220px;
    height: 12px;
    border-radius: 6px;
    border: 1px solid #ebeef5;
}

.legend-bar.neg {
    background: linear-gradient(to right,
            hsl(120, 60%, 92%),
            hsl(120, 60%, 55%));
}

.legend-bar.pos {
    background: linear-gradient(to right,
            hsl(0, 70%, 92%),
            hsl(0, 70%, 55%));
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

/* ===== 折线图卡片 ===== */
.daily-chart-card {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.daily-chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 16px;
    border-bottom: 1px solid #f0f2f5;
    flex-wrap: wrap;
}

.daily-chart-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.daily-chart-controls {
    display: flex;
    align-items: center;
    gap: 8px;
}

.daily-lbl {
    font-size: 13px;
    color: #606266;
}

.daily-chart-controls .input {
    height: 28px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    min-width: 140px;
}

.daily-chart-controls .input:focus {
    border-color: #2d6cdf;
}

.daily-loading {
    font-size: 12px;
    color: #909399;
}

.daily-chart-body {
    padding: 8px 8px 12px;
    min-height: 340px;
}

.daily-chart {
    width: 100%;
    height: 340px;
}

.daily-chart-empty {
    padding: 80px 16px;
    text-align: center;
    color: #c0c4cc;
    font-size: 13px;
}
</style>