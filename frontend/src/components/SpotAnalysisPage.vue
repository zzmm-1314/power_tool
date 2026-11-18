<template>
    <PageContainer :title="config.title">
        <!-- 筛选 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>{{ config.nodeLabel }}</label>
                <SearchableSelect v-model="query.node" :options="nodeOptions" @change="loadData"
                    style="width: 200px;" />
            </div>
            <div class="filter-item">
                <label>操作日期</label>
                <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
                    end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px;" @change="onDateChange" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '查询中...' : '🔍 查询数据' }}
            </button>
        </div>

        <!-- 收益卡片 -->
        <div v-if="hasSearched" class="stat-cards">
            <div class="stat-card total">
                <div class="stat-label">总收益 (元)</div>
                <div class="stat-value" :style="{ color: totalProfit >= 0 ? '#f56c6c' : '#67c23a' }">
                    {{ totalProfit.toFixed(2) }}
                </div>
            </div>
            <div class="stat-card buy">
                <div class="stat-label">{{ config.buyLabel }}收益 (元)</div>
                <div class="stat-value">{{ buyProfit.toFixed(2) }}</div>
            </div>
            <div class="stat-card sell">
                <div class="stat-label">{{ config.sellLabel }}收益 (元)</div>
                <div class="stat-value">{{ sellProfit.toFixed(2) }}</div>
            </div>
        </div>

        <!-- 趋势图 -->
        <div v-if="hasSearched && filteredData.length > 0" class="chart-card">
            <div class="chart-title">标的日成交电量与收益趋势</div>
            <VChart :option="chartOption" autoresize class="chart" />
        </div>

        <!-- 明细表 -->
        <div class="result-card">
            <div v-if="!hasSearched" class="empty-tip">
                请选择{{ config.nodeLabel }}和日期范围，点击查询。
            </div>
            <div v-else-if="!filteredData.length" class="empty-tip">当前条件范围内暂无数据。</div>
            <div v-else class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th v-for="col in config.columns" :key="col.key">{{ col.label }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in filteredData" :key="idx">
                            <td v-for="col in config.columns" :key="col.key" :style="cellStyle(row, col)">
                                {{ formatCell(row, col) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import { listPlantNodes } from '@/api/modules/nodes'
import { expandDateRange } from '@/utils/dateRange'
import { request } from '@/api/request'
import type { SpotAnalysisConfig, SpotColumnDef } from './spot-analysis-types'
const dateRange = ref<[string, string] | null>(null)
const props = defineProps<{ config: SpotAnalysisConfig }>()

const nodeOptions = ref<string[]>([])
const loading = ref(false)
const hasSearched = ref(false)
const rawData = ref<any[]>([])

const query = reactive({ node: '', dateStart: '', dateEnd: '' })

function initDateRange() {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 13)
    const fmt = (d: Date) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    query.dateEnd = fmt(end)
    query.dateStart = fmt(start)
    dateRange.value = [query.dateStart, query.dateEnd]
}
function onDateChange(val: [string, string] | null) {
    if (val) {
        query.dateStart = val[0]
        query.dateEnd = val[1]
        loadData()
    }
}
onMounted(async () => {
    initDateRange()
    try {
        const list = await listPlantNodes()
        nodeOptions.value = list.map(n => n.name)
    } catch {
        nodeOptions.value = []
    }
})

const filteredData = computed(() => {
    if (!rawData.value.length) return []
    if (!query.dateStart || !query.dateEnd) return rawData.value
    const dates = expandDateRange(query.dateStart, query.dateEnd)
    return rawData.value.filter(row => dates.includes(row.opDate))
})

const totalProfit = computed(() =>
    filteredData.value.reduce((s, r) => s + (r.finalDiff || 0), 0),
)
const buyProfit = computed(() =>
    filteredData.value
        .filter(r => r.direction === props.config.buyDirection)
        .reduce((s, r) => s + (r.finalDiff || 0), 0),
)
const sellProfit = computed(() =>
    filteredData.value
        .filter(r => r.direction === props.config.sellDirection)
        .reduce((s, r) => s + (r.finalDiff || 0), 0),
)

async function loadData() {
    if (!query.node) return alert(`请选择${props.config.nodeLabel}`)
    if (!query.dateStart || !query.dateEnd) return alert('请选择完整的日期范围')

    loading.value = true
    hasSearched.value = true
    try {
        const res = await request<any[]>({
            url: props.config.apiUrl,
            method: 'get',
            params: { node: query.node, startDate: query.dateStart, endDate: query.dateEnd },
        })
        rawData.value = res || []
    } catch (err: any) {
        alert('查询失败：' + (err.message || '后端服务异常'))
        rawData.value = []
    } finally {
        loading.value = false
    }
}

function formatCell(row: any, col: SpotColumnDef): string {
    if (col.fixedNode) return query.node || '-'
    const v = row[col.key]
    if (v == null) return '-'
    if (typeof v === 'number') {
        return col.decimals != null ? v.toFixed(col.decimals) : String(v)
    }
    return String(v)
}

function cellStyle(row: any, col: SpotColumnDef) {
    if (!col.colored) return undefined
    return getDiffStyle(row[col.key])
}

function getDiffStyle(val: number | null | undefined) {
    const v = val ?? 0
    if (v === 0) return { backgroundColor: '#fff' }
    const maxAbs = Math.max(...filteredData.value.map(d => Math.abs(d.finalDiff || 0)), 1)
    const intensity = Math.min(Math.abs(v) / maxAbs, 1)
    if (v > 0) {
        return {
            backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.7})`,
            color: intensity > 0.6 ? '#fff' : '#303133',
            fontWeight: 'bold',
        }
    }
    return {
        backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.7})`,
        color: intensity > 0.6 ? '#fff' : '#303133',
        fontWeight: 'bold',
    }
}

const chartData = computed(() => {
    if (!filteredData.value.length) return { dates: [], qtys: [], profits: [] }
    const map = new Map<string, { qty: number; profit: number }>()
    filteredData.value.forEach(r => {
        const tradeDate = r.tradeDate || r.opDate
        if (!map.has(tradeDate)) map.set(tradeDate, { qty: 0, profit: 0 })
        const item = map.get(tradeDate)!
        item.qty += Math.abs(r.qty || 0)
        item.profit += r.finalDiff || 0
    })
    const sortedDates = Array.from(map.keys()).sort()
    return {
        dates: sortedDates,
        qtys: sortedDates.map(d => Number(map.get(d)!.qty.toFixed(2))),
        profits: sortedDates.map(d => Number(map.get(d)!.profit.toFixed(2))),
    }
})

const chartOption = computed<EChartsOption>(() => {
    const { dates, qtys, profits } = chartData.value
    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: (params: any) => {
                let html = `<div style="font-weight:bold;margin-bottom:4px;">${params[0].axisValue}</div>`
                params.forEach((p: any) => {
                    const unit = p.seriesName === '成交电量' ? ' MWh' : ' 元'
                    html += `<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">
                        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color}"></span>
                        <span>${p.seriesName}: <b>${Number(p.value).toFixed(2)}</b>${unit}</span>
                    </div>`
                })
                return html
            },
        },
        legend: { top: 0, data: ['成交电量', '总收益'] },
        grid: { left: 60, right: 60, top: 40, bottom: 40 },
        xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
        yAxis: [
            {
                type: 'value',
                name: '电量 (MWh)',
                nameTextStyle: { color: '#909399', fontSize: 11 },
                splitLine: { lineStyle: { type: 'dashed', color: '#f0f2f5' } },
            },
            {
                type: 'value',
                name: '收益 (元)',
                nameTextStyle: { color: '#909399', fontSize: 11 },
                splitLine: { show: false },
            },
        ],
        series: [
            {
                name: '成交电量', type: 'bar', yAxisIndex: 0, barMaxWidth: 32,
                itemStyle: { color: '#2d6cdf', borderRadius: [4, 4, 0, 0] },
                data: qtys,
            },
            {
                name: '总收益', type: 'line', yAxisIndex: 1, smooth: true,
                showSymbol: true, symbolSize: 6,
                itemStyle: { color: '#f56c6c' }, lineStyle: { width: 2 },
                data: profits,
            },
        ],
    }
})
</script>

<style scoped>
/* 全部从原 RollingProfit.vue 的 <style scoped> 原样搬过来 */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #fff;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex-wrap: wrap;
}

.filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.filter-item label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}

.separator {
    color: #909399;
    font-size: 13px;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.btn-primary {
    height: 34px;
    padding: 0 20px;
    background: #2d6cdf;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.stat-cards {
    display: flex;
    gap: 16px;
    margin-top: 16px;
}

.stat-card {
    flex: 1;
    background: #fff;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    border-left: 4px solid #dcdfe6;
}

.stat-card.total {
    border-left-color: #2d6cdf;
}

.stat-card.buy {
    border-left-color: #67c23a;
}

.stat-card.sell {
    border-left-color: #e6a23c;
}

.stat-label {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #303133;
    font-variant-numeric: tabular-nums;
}

.result-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin-top: 16px;
    max-height: calc(100vh - 320px);
}

.chart-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 16px;
    padding: 16px;
}

.chart-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
}

.chart {
    width: 100%;
    height: 320px;
}

.table-wrap {
    flex: 1;
    overflow: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    text-align: center;
}

.data-table th,
.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #ebeef5;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.data-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    position: sticky;
    top: 0;
    z-index: 2;
}

.empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    padding: 40px;
}
</style>