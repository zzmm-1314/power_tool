<template>
    <PageContainer title="电厂合约仓位">
        <!-- 顶部筛选 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>电厂节点</label>
                <select v-model="query.node" class="input">
                    <option value="" disabled>请选择电厂</option>
                    <option v-for="n in nodeOptions" :key="n.id" :value="n.name">{{ n.name }}</option>
                </select>
            </div>
            <div class="filter-item">
                <label>年月</label>
                <input type="number" v-model="query.year" class="input" style="width: 100px;" />
                <span class="separator">-</span>
                <input type="number" v-model="query.month" class="input" style="width: 70px;" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '加载中...' : '🔍 查询数据' }}
            </button>
        </div>

        <!-- 图表区 -->
        <div class="chart-card">
            <div class="chart-header">
                <div class="tabs">
                    <button :class="['tab-btn', { active: activeTab === 'intraday' }]"
                        @click="activeTab = 'intraday'">分时曲线 (96点)</button>
                    <button :class="['tab-btn', { active: activeTab === 'daily' }]" @click="activeTab = 'daily'">分日曲线
                        (月度)</button>
                </div>
            </div>
            <div class="chart-body">
                <div v-if="!hasData" class="empty-tip">请选择节点和月份，点击查询。</div>
                <VChart v-else-if="activeTab === 'intraday'" :option="intradayOption" autoresize class="chart" />
                <VChart v-else-if="activeTab === 'daily'" :option="dailyOption" autoresize class="chart" />
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import { listPlantNodes, type PlantNode } from '@/api/modules/nodes'
import { request } from '@/api/request'
const nodeOptions = ref<PlantNode[]>([])
const loading = ref(false)
const activeTab = ref<'intraday' | 'daily'>('intraday')

const query = reactive({ node: '', year: 2026, month: 10 })
const hasData = ref(false)

const chartData = ref({
    yearPoints: [] as number[], monthPoints: [] as number[], tendayPoints: [] as number[], rollingPoints: [] as number[], actualPoints: [] as number[],
    yearDaily: [] as number[], monthDaily: [] as number[], tendayDaily: [] as number[], rollingDaily: [] as number[], actualDaily: [] as number[]
})


const hours96 = Array.from({ length: 96 }).map((_, i) => `${String(Math.floor(i / 4)).padStart(2, '0')}:${String((i % 4) * 15).padStart(2, '0')}`)
const days31 = Array.from({ length: 31 }).map((_, i) => `${i + 1}日`)

onMounted(async () => {
    nodeOptions.value = await listPlantNodes()
})
interface ApiResponse<T = any> {
    code: number
    message: string
    data: T
}
interface PositionData {
    yearPoints: number[]
    monthPoints: number[]
    tendayPoints: number[]
    rollingPoints: number[]
    actualPoints: number[]
    yearDaily: number[]
    monthDaily: number[]
    tendayDaily: number[]
    rollingDaily: number[]
    actualDaily: number[]
}
async function loadData() {
    if (!query.node) return alert('请选择电厂节点')
    loading.value = true

    try {
        // 假设我们有一个这样的接口
        const res = await request<ApiResponse<PositionData>>({
            url: `/contract/position-data`,
            method: 'get',
            params: { node: query.node, year: query.year, month: query.month }
        })
        const data = res.data || res

        // 后端返回 96 点数组和日数组，直接赋值
        chartData.value = data
        hasData.value = true
    } catch (err) {
        alert('获取数据失败')
    } finally {
        loading.value = false
    }
}

const commonOptions: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
}

const getSeries = (isIntraday: boolean) => [
    { name: '年度合约', type: 'line', stack: 'contract', areaStyle: { opacity: 0.3 }, smooth: true, showSymbol: false, data: isIntraday ? chartData.value.yearPoints : chartData.value.yearDaily, itemStyle: { color: '#5470c6' } } as const,
    { name: '月度合约', type: 'line', stack: 'contract', areaStyle: { opacity: 0.3 }, smooth: true, showSymbol: false, data: isIntraday ? chartData.value.monthPoints : chartData.value.monthDaily, itemStyle: { color: '#91cc75' } } as const,
    { name: '旬度合约', type: 'line', stack: 'contract', areaStyle: { opacity: 0.3 }, smooth: true, showSymbol: false, data: isIntraday ? chartData.value.tendayPoints : chartData.value.tendayDaily, itemStyle: { color: '#fac858' } } as const,
    { name: '滚撮电量', type: 'line', stack: 'contract', areaStyle: { opacity: 0.3 }, smooth: true, showSymbol: false, data: isIntraday ? chartData.value.rollingPoints : chartData.value.rollingDaily, itemStyle: { color: '#ee6666' } } as const,
    { name: '实际发电量', type: 'line', smooth: true, showSymbol: false, data: isIntraday ? chartData.value.actualPoints : chartData.value.actualDaily, itemStyle: { color: '#73c0de' }, lineStyle: { width: 2, type: 'dashed' } } as const
]


const intradayOption = computed<EChartsOption>(() => ({
    ...commonOptions, xAxis: { type: 'category', data: hours96, axisLabel: { interval: 7 } }, yAxis: { type: 'value', name: '电量 (MWh)' }, series: getSeries(true)
}))

const dailyOption = computed<EChartsOption>(() => ({
    ...commonOptions, xAxis: { type: 'category', data: days31, axisLabel: { interval: 2 } }, yAxis: { type: 'value', name: '电量 (MWh)' }, series: getSeries(false)
}))
</script>

<style scoped>
/* 样式与合约分解保持统一 */
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

.separator {
    color: #909399;
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

.chart-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    height: calc(100vh - 240px);
    margin-top: 16px;
}

.chart-header {
    padding: 12px 16px;
    border-bottom: 1px solid #ebeef5;
}

.tabs {
    display: inline-flex;
    background: #f5f7fa;
    padding: 4px;
    border-radius: 6px;
}

.tab-btn {
    padding: 6px 20px;
    border: none;
    background: transparent;
    font-size: 14px;
    color: #606266;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
}

.tab-btn.active {
    background: #fff;
    color: #2d6cdf;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-body {
    flex: 1;
    padding: 16px;
    min-height: 0;
    position: relative;
}

.chart {
    width: 100%;
    height: 100%;
}

.empty-tip {
    display: flex;
    height: 100%;
    align-items: center;
    justify-content: center;
    color: #909399;
}
</style>