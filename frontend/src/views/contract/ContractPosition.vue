<template>
    <PageContainer title="电厂合约仓位">
        <!-- 筛选栏 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>电厂节点</label>
                <SearchableSelect v-model="query.node" :options="nodeOptions" style="width: 200px;" />
            </div>
            <div class="filter-item">
                <label>月份</label>
                <el-date-picker v-model="query.monthStr" type="month" format="YYYY-MM" value-format="YYYY-MM"
                    style="width: 130px;" @change="onMonthChange" />
            </div>

            <!-- ⭐ 预测电量：上传 + 下载模板 -->
            <div class="filter-item">
                <label>预测电量</label>
                <button class="btn-outline" @click="triggerForecastUpload">
                    {{ hasForecast ? '已加载预测(点击重新上传)' : '上传预测Excel' }}
                </button>
                <button class="btn-download" @click="downloadForecastTemplate"
                    style="height: 34px; padding: 0 12px; border-radius: 4px; font-size: 13px; background: #f5f7fa; color: #606266; border: 1px solid #dcdfe6; margin-left: 8px; cursor: pointer;">
                    📥 下载模板
                </button>
                <input ref="forecastInputRef" type="file" accept=".xlsx,.xls" class="hidden-input"
                    @change="handleForecastUpload" />
            </div>

            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '加载中...' : '🔍 查询数据' }}
            </button>
            <button class="btn-outline" :disabled="!query.node || uploading" @click="triggerUpload">
                {{ uploading ? '上传中...' : '📤 上传实际发电量' }}
            </button>
            <input ref="fileInputRef" type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                @change="handleUpload" />
        </div>

        <!-- 占比重概览卡片 -->
        <div v-if="hasData" class="stat-cards">
            <div class="stat-card base-card">
                <div class="stat-label">实发总电量 (MWh)</div>
                <div class="stat-value">{{ summary.actual.toFixed(2) }}</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">年度合约占比</div>
                <div class="stat-value">{{ calcPct(summary.year) }}</div>
            </div>

            <!-- 上旬综合占比 -->
            <div class="stat-card" style="border-top-color: #e6a23c;">
                <div class="stat-label">上旬综合占比</div>
                <div class="stat-value">
                    {{ calcPct(summary.year + summary.month + summary.tenday1 + summary.rolling_tenday1) }}
                </div>
            </div>

            <!-- 中旬综合占比 -->
            <div class="stat-card" style="border-top-color: #e6a23c;">
                <div class="stat-label">中旬综合占比</div>
                <div class="stat-value">
                    {{ calcPct(summary.year + summary.month + summary.tenday2 + summary.rolling_tenday2) }}
                </div>
            </div>

            <!-- 下旬综合占比 -->
            <div class="stat-card" style="border-top-color: #e6a23c;">
                <div class="stat-label">下旬综合占比</div>
                <div class="stat-value">
                    {{ calcPct(summary.year + summary.month + summary.tenday3 + summary.rolling_tenday3) }}
                </div>
            </div>

            <div class="stat-card highlight">
                <div class="stat-label">总持仓占比(含滚撮)</div>
                <div class="stat-value">{{ calcPct(summary.totalContracts) }}</div>
            </div>
        </div>

        <!-- 图表区 -->
        <div v-if="hasData" class="chart-card">
            <div class="chart-header">
                <div class="tabs">
                    <button :class="['tab-btn', { active: activeTab === 'daily' }]"
                        @click="activeTab = 'daily'">每日总电量</button>
                    <button :class="['tab-btn', { active: activeTab === 'intraday' }]"
                        @click="activeTab = 'intraday'">单日 48 点曲线</button>
                </div>

                <div v-if="activeTab === 'intraday'" style="display: flex; align-items: center; gap: 8px;">
                    <label style="font-size: 13px; color: #606266;">选择日期</label>
                    <select v-model="selectedDay" class="input" style="width: 140px; height: 28px; padding: 0 8px;">
                        <option v-for="d in tableData" :key="d.date" :value="d.date">{{ d.date }}</option>
                    </select>
                </div>
            </div>
            <div class="chart-body">
                <VChart v-if="activeTab === 'daily'" :option="dailyOption" autoresize class="chart" />
                <VChart v-else-if="activeTab === 'intraday'" :option="intradayOption" autoresize class="chart" />
            </div>
        </div>

        <!-- 数据表格区 -->
        <div v-if="hasData" class="table-card">
            <!-- 子标签页切换 -->
            <div class="table-tabs">
                <button :class="['table-tab-btn', { active: activeTableTab === 'detail' }]"
                    @click="activeTableTab = 'detail'">每日 48 点明细</button>
                <button :class="['table-tab-btn', { active: activeTableTab === 'summary' }]"
                    @click="activeTableTab = 'summary'">每日仓位汇总</button>
                <!-- 表格区新增子标签 -->
                <button :class="['table-tab-btn', { active: activeTableTab === 'ratio' }]"
                    @click="activeTableTab = 'ratio'">分时电量占比</button>
            </div>

            <!-- 48 点明细表 -->
            <div v-if="activeTableTab === 'detail'" class="table-wrapper scroll-y" style="margin-top: 12px;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col" style="min-width: 90px;">日期</th>
                            <th style="min-width: 80px; background: #ecf5ff; color: #2d6cdf;">总计</th>
                            <th v-for="(label, idx) in hours48" :key="idx">{{ label }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- ⭐ 第一行：汇总行 -->
                        <tr class="summary-row">
                            <td class="sticky-col" style="background: #f0f9eb; color: #67c23a;">每日总计</td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">
                                {{colSums48.reduce((a, b) => a + b, 0).toFixed(2)}}
                            </td>
                            <td v-for="(val, idx) in colSums48" :key="'sum-' + idx"
                                style="background: #f0f9eb; color: #67c23a; font-weight: bold;">
                                {{ val === 0 ? '-' : val.toFixed(2) }}
                            </td>
                        </tr>

                        <!-- 数据行 -->
                        <tr v-for="row in tableData" :key="row.date">
                            <td class="sticky-col">{{ row.date }}</td>
                            <!-- ⭐ 每行的总计 -->
                            <td style="background: #f5f7fa; font-weight: 600;">
                                {{ calcRowSum(row.points).toFixed(2) }}
                            </td>
                            <td v-for="(val, idx) in row.points" :key="idx">
                                {{ val === 0 ? '-' : val.toFixed(2) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- 每日仓位汇总表 -->
            <div v-if="activeTableTab === 'summary'" class="table-wrapper scroll-y" style="margin-top: 12px;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col">日期</th>
                            <th>实发电量</th>
                            <th>年度合约</th>
                            <th>月度合约</th>
                            <th>旬度合约</th>
                            <th>滚撮买入</th>
                            <th>滚撮卖出</th>
                            <th>总合约量</th>
                            <th>总占比</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="row in tableData" :key="row.date">
                            <td class="sticky-col">{{ row.date }}</td>
                            <td>{{ calcRowSum(row.actualPoints).toFixed(2) }}</td>
                            <td>{{ calcRowSum(row.yearPoints).toFixed(2) }}</td>
                            <td>{{ calcRowSum(row.monthPoints).toFixed(2) }}</td>
                            <td>{{ calcRowSum(row.tendayPoints).toFixed(2) }}</td>
                            <td style="color: #f56c6c;">{{ (row.rollingBuy || 0).toFixed(2) }}</td>
                            <td style="color: #67c23a;">{{ (row.rollingSell || 0).toFixed(2) }}</td>
                            <td style="font-weight: 600;">{{ calcRowTotal(row).toFixed(2) }}</td>
                            <td :style="{ color: calcRowRatio(row) > 100 ? '#f56c6c' : '#2d6cdf' }">
                                {{ calcRowRatio(row).toFixed(2) }}%
                            </td>
                        </tr>
                    </tbody>
                    <!-- ⭐ 新增：底部汇总行 -->
                    <tfoot>
                        <tr class="summary-row">
                            <td class="sticky-col" style="background: #f0f9eb; color: #67c23a; font-weight: bold;">合计
                            </td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">{{
                                portfolioTotals.actual }}</td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">{{ portfolioTotals.year
                                }}</td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">{{ portfolioTotals.month
                                }}</td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">{{
                                portfolioTotals.tenday }}</td>
                            <td style="background: #f0f9eb; color: #f56c6c; font-weight: bold;">{{
                                portfolioTotals.rollingBuy }}</td>
                            <td style="background: #f0f9eb; color: #67c23a; font-weight: bold;">{{
                                portfolioTotals.rollingSell }}</td>
                            <td style="background: #f0f9eb; color: #2d6cdf; font-weight: bold;">{{ portfolioTotals.total
                                }}</td>
                            <td style="background: #f0f9eb; color: #2d6cdf; font-weight: bold;">{{ portfolioTotals.ratio
                                }}%</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <!-- 新增占比表格 -->
            <div v-if="activeTableTab === 'ratio'" class="table-wrapper scroll-y" style="margin-top: 12px;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col" style="min-width: 90px;">日期</th>
                            <th v-for="(label, idx) in hours48" :key="idx">{{ label }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="row in tableData" :key="row.date">
                            <td class="sticky-col">{{ row.date }}</td>
                            <td v-for="(val, idx) in row.points" :key="idx"
                                :style="getRatioStyle(row.points[idx], row.actualPoints[idx])">
                                {{ formatRatio(row.points[idx], row.actualPoints[idx]) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import { listPlantNodes, fetchGlobalNode } from '@/api/modules/nodes'
import { request } from '@/api/request'
import { apiUrl } from '@/utils/apiBase'
const nodeOptions = ref<string[]>([])
const loading = ref(false)
const uploading = ref(false)
const hasData = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const forecastInputRef = ref<HTMLInputElement | null>(null)
const forecastData = ref<Record<string, number>>({})
const hasForecast = computed(() => Object.keys(forecastData.value).length > 0)
const query = reactive({
    node: '',
    monthStr: new Date().toISOString().slice(0, 7), // '2026-11'
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1
})

const chartData = ref({
    dates: [] as string[],
    year: [] as number[],
    month: [] as number[],
    tenday: [] as number[],
    actual: [] as number[],
    rollingBuy: [] as number[],
    rollingSell: [] as number[]
})

const activeTab = ref<'daily' | 'intraday'>('daily')
const activeTableTab = ref<'detail' | 'summary' | 'ratio'>('detail') // 新增：表格标签页
const selectedDay = ref<string>('')

const summary = ref({
    actual: 0, year: 0, month: 0,
    tenday1: 0, tenday2: 0, tenday3: 0,
    rolling_tenday1: 0, rolling_tenday2: 0, rolling_tenday3: 0,
    totalContracts: 0
})

const tableData = ref<{
    date: string,
    points: number[],
    yearPoints: number[],
    monthPoints: number[],
    tendayPoints: number[],
    rollingPoints: number[],
    actualPoints: number[],
    rollingBuy: number,
    rollingSell: number
}[]>([])

// ⭐ 修改 hours48 生成逻辑，变为 00:30 ~ 24:00
const hours48 = Array.from({ length: 48 }).map((_, i) => {
    if (i === 47) return '24:00'
    const h = Math.floor(i / 2)
    const m = (i % 2) * 30 + 30
    if (m === 60) return `${String(h + 1).padStart(2, '0')}:00`
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
})

onMounted(async () => {
    try {
        const list = await listPlantNodes()
        nodeOptions.value = list.map(n => n.name)
        // ⭐ 默认选中全局节点
        if (!query.node && nodeOptions.value.length) {
            try {
                const g = await fetchGlobalNode()
                if (g && nodeOptions.value.includes(g)) {
                    query.node = g
                }
            } catch {
                // ignore
            }
        }
    } catch { nodeOptions.value = [] }
})
function triggerForecastUpload() {
    forecastInputRef.value?.click()
}
async function handleForecastUpload(e: Event) {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (!file) return

    const fd = new FormData()
    fd.append('file', file)

    try {
        const res: any = await request({
            url: '/contract/parse-forecast',
            method: 'post',
            data: fd,
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        forecastData.value = res || {}
        alert(`成功解析 ${Object.keys(forecastData.value).length} 天的预测电量`)
    } catch (err: any) {
        alert('预测电量解析失败：' + (err.message || '未知错误'))
    } finally {
        target.value = ''
    }
}
function calcPct(val: number) {
    if (summary.value.actual === 0) return '0.00%'
    return ((val / summary.value.actual) * 100).toFixed(2) + '%'
}
function downloadForecastTemplate() {
    // 直接打开新窗口请求后端接口，触发浏览器下载，绕开 Axios 和 Vue Router
    window.open(apiUrl('/contract/forecast-template'), '_blank')
}
// ⭐ 修改 loadData 的请求方式为 POST 并携带 forecastData
async function loadData() {
    if (!query.node) return alert('请选择电厂节点')
    loading.value = true

    try {
        const res: any = await request({
            url: '/contract/position-data',
            method: 'post', // 改用 POST 以避开 GET 参数长度限制
            data: {
                node: query.node,
                year: query.year,
                month: query.month,
                forecastData: forecastData.value
            }
        })
        const data = res || {}
        summary.value = data.summary || { actual: 0, year: 0, month: 0, tenday1: 0, tenday2: 0, tenday3: 0, totalContracts: 0 }
        tableData.value = data.tableData || []

        const cd = data.chartData || {}
        chartData.value = {
            dates: cd.dates || [],
            year: cd.year || [],
            month: cd.month || [],
            tenday: cd.tenday || [],
            rollingSell: cd.rollingSell || (cd.rolling ? cd.rolling.map((v: number) => v > 0 ? v : 0) : []),
            rollingBuy: cd.rollingBuy || (cd.rolling ? cd.rolling.map((v: number) => v < 0 ? Math.abs(v) : 0) : []),
            actual: cd.actual || []
        }

        hasData.value = true
        if (tableData.value.length > 0) {
            selectedDay.value = tableData.value[0].date
        }

        await nextTick()
    } catch (err: any) {
        alert('获取数据失败：' + err.message)
    } finally {
        loading.value = false
    }
}
// ⭐ 新增：计算 48 点表格每一列（每个时间点）的总和
const colSums48 = computed(() => {
    const sums = new Array(48).fill(0)
    tableData.value.forEach(row => {
        if (row.points) {
            row.points.forEach((v, i) => {
                sums[i] += (v || 0)
            })
        }
    })
    return sums.map(v => Number(v.toFixed(2)))
})

// ⭐ 新增：计算仓位汇总表的底部总计行
const portfolioTotals = computed(() => {
    const totals = {
        actual: 0, year: 0, month: 0, tenday: 0,
        rollingBuy: 0, rollingSell: 0, total: 0
    }
    tableData.value.forEach(row => {
        totals.actual += calcRowSum(row.actualPoints)
        totals.year += calcRowSum(row.yearPoints)
        totals.month += calcRowSum(row.monthPoints)
        totals.tenday += calcRowSum(row.tendayPoints)
        totals.rollingBuy += (row.rollingBuy || 0)
        totals.rollingSell += (row.rollingSell || 0)
        totals.total += calcRowTotal(row)
    })

    // 格式化
    Object.keys(totals).forEach(k => {
        // @ts-ignore
        totals[k] = Number(totals[k].toFixed(2))
    })

    const actual = totals.actual
    const ratio = actual > 0 ? (totals.total / actual) * 100 : 0

    return { ...totals, ratio: Number(ratio.toFixed(2)) }
})
function triggerUpload() {
    if (!query.node) return alert('请先选择电厂节点')
    fileInputRef.value?.click()
}
function onMonthChange(val: string) {
    if (val) {
        const [y, m] = val.split('-')
        query.year = parseInt(y)
        query.month = parseInt(m)
        loadData()
    }
}

function formatRatio(total: number, actual: number): string {
    if (!actual || actual === 0) return '-'
    return ((total / actual) * 100).toFixed(2) + '%'
}
function getRatioStyle(total: number, actual: number) {
    if (!actual || actual === 0) return {}
    const ratio = total / actual
    if (ratio < 0.9) return { color: '#67c23a' } // 标绿
    if (ratio > 1.1) return { color: '#f56c6c', fontWeight: 'bold' } // 标红
    return {}
}
async function handleUpload(e: Event) {
    const target = e.target as HTMLInputElement
    const files = target.files
    if (!files || files.length === 0 || !query.node) return

    uploading.value = true
    const formData = new FormData()
    formData.append('node_name', query.node)
    formData.append('data_type', 'actual')

    // ⭐ 遍历所有文件，塞入同一个 FormData
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i])
    }

    try {
        await request({
            url: '/contract/config/node-data',
            method: 'post',
            data: formData,
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        // 修改提示文字
        alert(`成功上传 ${files.length} 个实际发电量文件`)
        await loadData()
    } catch (err: any) {
        alert('上传失败：\n' + (err.message || '未知错误'))
    } finally {
        uploading.value = false
        // 清空 input，允许重复上传同名文件
        target.value = ''
    }
}

// 汇总表计算辅助函数
function calcRowSum(points: number[]): number {
    if (!points || !points.length) return 0
    return points.reduce((a, b) => a + b, 0)
}

function calcRowTotal(row: any): number {
    const y = calcRowSum(row.yearPoints)
    const m = calcRowSum(row.monthPoints)
    const t = calcRowSum(row.tendayPoints)
    return y + m + t + (row.rollingSell || 0) - (row.rollingBuy || 0)
}

function calcRowRatio(row: any): number {
    const actual = calcRowSum(row.actualPoints)
    if (actual === 0) return 0
    return (calcRowTotal(row) / actual) * 100
}

// 图表 Tooltip
const getTooltipHtml = (axisValue: string, d: any) => {
    const { year, month, tenday, sell, buy, actual } = d
    const totalContract = year + month + tenday + sell - buy
    const safeTotal = totalContract > 0 ? totalContract : 1
    const pct = (v: number) => ((v / safeTotal) * 100).toFixed(1)

    let detailRows = `
        <div style="display:flex; justify-content:space-between; gap:20px; font-size:12px; line-height:1.6; color:#606266;">
            <span>■ 年度合约</span><span><b>${year.toFixed(2)}</b> (${pct(year)}%)</span>
        </div>
        <div style="display:flex; justify-content:space-between; gap:20px; font-size:12px; line-height:1.6; color:#606266;">
            <span>■ 月度合约</span><span><b>${month.toFixed(2)}</b> (${pct(month)}%)</span>
        </div>
        <div style="display:flex; justify-content:space-between; gap:20px; font-size:12px; line-height:1.6; color:#606266;">
            <span>■ 旬度合约</span><span><b>${tenday.toFixed(2)}</b> (${pct(tenday)}%)</span>
        </div>
    `
    if (sell > 0 || buy > 0) {
        detailRows += `
            <div style="display:flex; flex-direction:column; font-size:12px; line-height:1.6; margin-top:4px; padding-top:4px; border-top:1px dashed #ebeef5;">
                ${sell > 0 ? `<div style="display:flex; justify-content:space-between;"><span><span style="color:#67c23a;">■</span> 滚撮卖出</span><span style="color:#67c23a;"><b>+${sell.toFixed(2)}</b></span></div>` : ''}
                ${buy > 0 ? `<div style="display:flex; justify-content:space-between;"><span><span style="color:#f56c6c;">■</span> 滚撮买入</span><span style="color:#f56c6c;"><b>-${buy.toFixed(2)}</b></span></div>` : ''}
            </div>`
    }
    const ratio = actual > 0 ? ((totalContract / actual) * 100).toFixed(1) : '0.0'
    return `
        <div style="font-weight:bold; margin-bottom:6px; border-bottom:1px solid #ebeef5; padding-bottom:4px;">${axisValue}</div>
        <div style="color:#303133; font-weight:bold; margin-bottom:4px; font-size:13px;">总合约量: ${totalContract.toFixed(2)} MWh</div>
        ${detailRows}
        <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #ebeef5; font-size:13px;">
            <div style="display:flex; justify-content:space-between; color:#10b981; font-weight:bold;">
                <span>实发电量</span><span>${actual.toFixed(2)} MWh</span>
            </div>
            <div style="display:flex; justify-content:space-between; color:#909399; font-size:12px; margin-top:2px;">
                <span>持仓覆盖率</span><span>${ratio}%</span>
            </div>
        </div>
    `
}

const dailyOption = computed<EChartsOption>(() => {
    const cd = chartData.value
    if (!cd.dates.length) return { tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: [] }, yAxis: { type: 'value' }, series: [] }

    const totalContracts = cd.dates.map((_, i) => (cd.year[i] || 0) + (cd.month[i] || 0) + (cd.tenday[i] || 0))

    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
                const p = Array.isArray(params) ? params[0] : params
                const idx = p.dataIndex
                const d = {
                    year: cd.year[idx] || 0, month: cd.month[idx] || 0, tenday: cd.tenday[idx] || 0,
                    sell: cd.rollingSell[idx] || 0, buy: cd.rollingBuy[idx] || 0, actual: cd.actual[idx] || 0
                }
                return getTooltipHtml(p.axisValue, d)
            }
        },
        legend: { top: 0, data: ['总合约', '实发电量'] },
        grid: { left: 60, right: 30, top: 40, bottom: 60 },
        dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 10, height: 20 }],
        xAxis: { type: 'category', data: cd.dates, axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', name: '电量 (MWh)' },
        series: [
            {
                name: '总合约', type: 'bar', data: totalContracts, barWidth: 24,
                itemStyle: { color: 'rgba(84, 112, 198, 0.6)', borderRadius: [4, 4, 0, 0] }, z: 1
            },
            {
                name: '实发电量', type: 'bar', data: cd.actual, barWidth: 12, barGap: '-100%',
                itemStyle: { color: '#10b981', borderRadius: [2, 2, 0, 0] }, z: 2
            }
        ]
    }
})

const intradayOption = computed<EChartsOption>(() => {
    const row = tableData.value.find(r => r.date === selectedDay.value)
    if (!row) return { tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: hours48 }, yAxis: { type: 'value' }, series: [] }

    const yTotal = row.yearPoints.map((v, i) => v + row.monthPoints[i] + row.tendayPoints[i])

    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
                const p = Array.isArray(params) ? params[0] : params
                const idx = p.dataIndex
                const net = row.rollingPoints[idx] || 0
                const d = {
                    year: row.yearPoints[idx] || 0, month: row.monthPoints[idx] || 0, tenday: row.tendayPoints[idx] || 0,
                    sell: net > 0 ? net : 0, buy: net < 0 ? Math.abs(net) : 0, actual: row.actualPoints[idx] || 0
                }
                return getTooltipHtml(p.axisValue, d)
            }
        },
        legend: { top: 0, data: ['总合约', '实发电量'] },
        grid: { left: 60, right: 30, top: 40, bottom: 40 },
        xAxis: { type: 'category', data: hours48, axisLabel: { interval: 3, fontSize: 11 } },
        yAxis: { type: 'value', name: '电量 (MWh)' },
        series: [
            {
                name: '总合约', type: 'bar', data: yTotal, barWidth: 14,
                itemStyle: { color: 'rgba(84, 112, 198, 0.6)' }, z: 1
            },
            {
                name: '实发电量', type: 'bar', data: row.actualPoints, barWidth: 6, barGap: '-100%',
                itemStyle: { color: '#10b981' }, z: 2
            }
        ]
    }
})
</script>

<style scoped>
/* 原有筛选、卡片等样式不变 */
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

.btn-primary:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.btn-outline {
    height: 34px;
    padding: 0 20px;
    background: #fff;
    color: #2d6cdf;
    border: 1px solid #2d6cdf;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.btn-outline:hover:not(:disabled) {
    background: #ecf5ff;
}

.btn-outline:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.hidden-input {
    display: none;
}

.stat-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin-top: 16px;
}

.stat-card {
    background: #fff;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    border-top: 3px solid #e4e7ed;
}

.stat-card.base-card {
    border-top-color: #2d6cdf;
}

.stat-card.highlight {
    border-top-color: #f56c6c;
    background: #fef0f0;
}

.stat-label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 20px;
    font-weight: 700;
    color: #303133;
}

.chart-card {
    background: #fff;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 16px;
}

.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 10px;
}

.tabs {
    display: inline-flex;
    background: #f5f7fa;
    padding: 4px;
    border-radius: 6px;
}

.tab-btn {
    padding: 6px 16px;
    border: none;
    background: transparent;
    font-size: 13px;
    color: #606266;
    border-radius: 4px;
    cursor: pointer;
}

.tab-btn.active {
    background: #fff;
    color: #2d6cdf;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-body {
    height: 360px;
}

.chart {
    width: 100%;
    height: 100%;
}

/* 表格卡片 */
.table-card {
    background: #fff;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 16px;
}

/* ⭐ 表格子标签页样式 */
.table-tabs {
    display: flex;
    border-bottom: 1px solid #ebeef5;
    margin-bottom: 12px;
}

.table-tab-btn {
    padding: 10px 20px;
    border: none;
    background: transparent;
    font-size: 14px;
    color: #606266;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
}

.table-tab-btn.active {
    color: #2d6cdf;
    font-weight: 600;
    border-bottom-color: #2d6cdf;
}

.table-wrapper {
    overflow-x: auto;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    max-height: 500px;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: right;
}

.data-table th,
.data-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
    white-space: nowrap;
}

.data-table th {
    background: #f5f7fa;
    position: sticky;
    top: 0;
    z-index: 2;
    text-align: center;
    color: #303133;
}

.sticky-col {
    position: sticky;
    left: 0;
    background: #fff;
    z-index: 1;
    text-align: center;
    font-weight: 500;
}

th.sticky-col {
    background: #f5f7fa;
    z-index: 3;
}

/* 表格汇总行通用样式 */
.summary-row td {
    border-top: 2px solid #dcdfe6;
    border-bottom: 2px solid #dcdfe6;
}

tfoot td {
    position: sticky;
    bottom: 0;
    z-index: 2;
}

tfoot .sticky-col {
    z-index: 3;
}
</style>