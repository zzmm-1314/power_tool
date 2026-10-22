<template>
    <PageContainer title="申报系数预测">
        <template #extra>
            <button class="btn-upload" @click="weatherModalVisible = true">
                ⚙ 天气参数配置
            </button>
        </template>

        <!-- 表单卡片 -->
        <div class="form-card">
            <div class="form-row">
                <label>数据来源</label>
                <select v-model="form.nodeType" class="input" @change="onTypeChange">
                    <option value="unified">统一结算点</option>
                    <option value="plant">电厂节点</option>
                </select>

                <template v-if="form.nodeType === 'plant'">
                    <label class="inline-label">节点</label>
                    <select v-model="form.nodeName" class="input" style="min-width: 200px">
                        <option value="">请选择节点</option>
                        <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
                    </select>
                </template>

                <label class="inline-label">预测日期</label>
                <input v-model="form.targetDate" type="date" class="input" />

                <label class="inline-label">回看窗口</label>
                <input v-model.number="form.windowDays" type="number" min="15" max="120" class="input small" />
                <span class="unit">天</span>

                <label class="inline-label">检测偏移</label>
                <input v-model.number="form.detectionOffset" type="number" min="0" max="10" class="input small" />
                <span class="unit">天</span>
            </div>

            <div class="form-row">
                <label>系数范围</label>
                <input v-model.number="form.coeffMin" type="number" step="0.01" class="input small" placeholder="下限" />
                <span class="unit">~</span>
                <input v-model.number="form.coeffMax" type="number" step="0.01" class="input small" placeholder="上限" />

                <label class="inline-label">天气文件（可选）</label>
                <input type="file" accept=".xlsx,.xls" class="file-input" @change="onWeatherFile" />

                <button class="btn primary" :disabled="starting" @click="startPredict">
                    {{ starting ? '启动中...' : '开始预测' }}
                </button>
            </div>

            <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
            <p v-if="taskProgress" class="progress-tip">
                {{ taskProgress.stage }}：{{ taskProgress.current }}/{{ taskProgress.total }}
                {{ taskProgress.message }}
            </p>
        </div>

        <!-- ===== 结果区：左右分栏 ===== -->
        <div v-if="result" class="result-layout">
            <!-- 左侧目录 -->
            <aside class="result-aside">
                <div v-for="item in TOC_ITEMS" :key="item.key" class="toc-item"
                    :class="{ active: activeKey === item.key, disabled: !item.enabled }"
                    @click="item.enabled && (activeKey = item.key)">
                    {{ item.label }}
                </div>
            </aside>

            <!-- 右侧图表 -->
            <section class="result-main">
                <!-- 摘要 -->
                <div class="summary-bar">
                    <span>策略：<strong>{{ result.strategy }}</strong></span>
                    <span>半衰期：<strong>{{ result.half_life }} 天</strong></span>
                    <span>预测日期：<strong>{{ result.target_date }}</strong></span>
                    <span>系数范围：{{ result.coeff_min }} ~ {{ result.coeff_max }}</span>
                </div>

                <!-- 1. 修正前多策略曲线 -->
                <!-- 1. 修正前多策略曲线 -->
                <div v-if="activeKey === 'base'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">修正前系数曲线（所有策略 × 半衰期）</span>
                        <button class="btn ghost small" @click="exportMultiStrategyCsv">
                            导出多策略 CSV
                        </button>
                    </div>
                    <div class="chart-body">
                        <VChart :option="multiStrategyOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 2. 修正后系数 -->
                <div v-if="activeKey === 'final'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">修正后系数曲线（本次选中策略）</span>
                        <button class="btn ghost small" @click="exportCsv">导出 CSV</button>
                    </div>
                    <div class="chart-body">
                        <VChart :option="finalCurveOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 3. 修正前后对比 -->
                <div v-if="activeKey === 'compare'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">修正前后对比</span>
                    </div>
                    <div class="chart-body">
                        <VChart :option="beforeAfterOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 4. 天气-气温云量 -->
                <div v-if="activeKey === 'weather-temp'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">气温与云量（面积图）</span>
                    </div>
                    <div class="chart-body">
                        <VChart :option="tempCloudOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 5. 天气-风速湿度 -->
                <div v-if="activeKey === 'weather-wind'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">风速与湿度（面积图）</span>
                    </div>
                    <div class="chart-body">
                        <VChart :option="windHumidityOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 6. 天气-辐射 -->
                <div v-if="activeKey === 'weather-rad'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">直接辐射与散射辐射（面积图）</span>
                    </div>
                    <div class="chart-body">
                        <VChart :option="radiationOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 7. 修正明细 -->
                <div v-if="activeKey === 'detail'" class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">修正明细（各偏移分量堆叠）</span>
                    </div>
                    <div class="chart-body">
                        <VChart :option="correctionDetailOption" autoresize class="chart" />
                    </div>
                </div>

                <!-- 8. 系数表格 -->
                <div v-if="activeKey === 'table'" class="table-card">
                    <div class="chart-header">
                        <span class="chart-title">48 点系数明细</span>
                        <button class="btn ghost small" @click="exportCsv">导出 CSV</button>
                    </div>
                    <div class="table-wrap scroll-y">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>时段</th>
                                    <th>修正前</th>
                                    <th>修正后</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(h, i) in result.hours" :key="i">
                                    <td>{{ h }}</td>
                                    <td>{{ result.base_coefficients[i]?.toFixed(4) }}</td>
                                    <td>{{ result.coefficients[i]?.toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </div>

        <!-- 天气参数配置弹窗 -->
        <WeatherConfigModal v-model="weatherModalVisible" :initial="weatherConfig" @confirm="onWeatherConfigConfirm" />
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import PageContainer from '@/components/PageContainer.vue'
import WeatherConfigModal from '@/components/WeatherConfigModal.vue'
import {
    startCoefficientTask,
    fetchCoefficientProgress,
    type PredictResult,
    type ProgressData,
} from '@/api/modules/coefficient'
import { listPlantNodes } from '@/api/modules/nodes'

/* ---------------- 表单 ---------------- */
const form = reactive({
    nodeType: 'unified',
    nodeName: '',
    targetDate: new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10),
    windowDays: 45,
    detectionOffset: 3,
    coeffMin: 0.1,
    coeffMax: 1.9,
})

const nodes = ref<string[]>([])
const weatherFile = ref<File | null>(null)
const starting = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')
const taskId = ref<string | null>(null)
const taskProgress = ref<ProgressData['progress'] | null>(null)
const result = ref<PredictResult | null>(null)
let timer: number | undefined

/* ---------------- 天气配置 ---------------- */
const weatherModalVisible = ref(false)
const weatherConfig = ref<Record<string, any>>({})

function onWeatherConfigConfirm(cfg: Record<string, any>) {
    weatherConfig.value = cfg
}

/* ---------------- 左侧目录 ---------------- */
const hasWeather = computed(() => !!result.value?.weather_data)

const TOC_ITEMS = computed(() => [
    { key: 'base', label: '① 修正前（多策略）', enabled: true },
    { key: 'final', label: '② 修正后系数', enabled: true },
    { key: 'compare', label: '③ 修正前后对比', enabled: true },
    { key: 'weather-temp', label: '④ 气温与云量', enabled: hasWeather.value },
    { key: 'weather-wind', label: '⑤ 风速与湿度', enabled: hasWeather.value },
    { key: 'weather-rad', label: '⑥ 辐射对比', enabled: hasWeather.value },
    { key: 'detail', label: '⑦ 修正明细', enabled: true },
    { key: 'table', label: '⑧ 系数表格', enabled: true },
])

const activeKey = ref<string>('base')
watch(hasWeather, (v) => {
    if (!v && activeKey.value.startsWith('weather')) activeKey.value = 'base'
})

/* ---------------- 加载节点 ---------------- */
async function loadNodes() {
    try {
        const list = await listPlantNodes()
        nodes.value = list.map((n) => n.name)
    } catch {
        nodes.value = []
    }
}

function onTypeChange() {
    if (form.nodeType === 'unified') form.nodeName = ''
}

function onWeatherFile(e: Event) {
    const input = e.target as HTMLInputElement
    weatherFile.value = input.files?.[0] ?? null
}
/** 导出第一张图：所有策略 × 半衰期 的 48 点系数表 */
function exportMultiStrategyCsv() {
    if (!result.value) return

    const curves = result.value.all_coeffs_curves || []
    if (!curves.length) {
        msg.value = '没有可导出的多策略系数'
        msgType.value = 'err'
        return
    }

    const hours = result.value.hours || []
    const selectedStrategy = result.value.strategy
    const selectedHalfLife = result.value.half_life

    // 列头：时段 + 每个策略组合
    const header: string[] = ['时段']
    curves.forEach((c) => {
        // 用 * 标记当前选中的策略，方便在 Excel 中直观识别
        const isSelected =
            c.strategy_family === selectedStrategy &&
            Math.abs((c.half_life ?? 0) - (selectedHalfLife ?? 0)) < 1e-6
        header.push(isSelected ? `*${c.name}` : c.name)
    })

    const rows: string[][] = [header]
    hours.forEach((h, i) => {
        const row: string[] = [h]
        curves.forEach((c) => {
            const v = c.data[i]
            row.push(v == null ? '' : Number(v).toFixed(4))
        })
        rows.push(row)
    })

    // UTF-8 BOM，避免 Excel 打开中文乱码
    const csv =
        '\uFEFF' + rows.map((r) => r.map(escapeCsvCell).join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `申报系数_多策略_${result.value.target_date}.csv`
    a.click()
    URL.revokeObjectURL(url)

    msg.value = `已导出 ${curves.length} 条策略组合 × ${hours.length} 个时段`
    msgType.value = 'ok'
}

/** CSV 单元格转义：含逗号/引号/换行时用双引号包裹 */
function escapeCsvCell(v: string): string {
    if (v == null) return ''
    const s = String(v)
    if (/[",\n\r]/.test(s)) {
        return `"${s.replace(/"/g, '""')}"`
    }
    return s
}
/* ---------------- 启动预测 ---------------- */
async function startPredict() {
    msg.value = ''
    if (!form.targetDate) {
        msg.value = '请选择预测日期'
        msgType.value = 'err'
        return
    }
    if (form.nodeType === 'plant' && !form.nodeName) {
        msg.value = '请选择电厂节点'
        msgType.value = 'err'
        return
    }

    const fd = new FormData()
    fd.append('nodeType', form.nodeType)
    fd.append('nodeName', form.nodeName)
    fd.append('targetDate', form.targetDate)
    fd.append('windowDays', String(form.windowDays))
    fd.append('detectionOffset', String(form.detectionOffset))
    fd.append('coeffMin', String(form.coeffMin))
    fd.append('coeffMax', String(form.coeffMax))
    if (weatherFile.value) fd.append('weather_file', weatherFile.value)
    if (Object.keys(weatherConfig.value).length) {
        fd.append('weatherConfig', JSON.stringify(weatherConfig.value))
    }

    starting.value = true
    result.value = null
    taskProgress.value = null
    try {
        const res = await startCoefficientTask(fd)
        taskId.value = res.taskId
        msg.value = '任务已启动，正在计算…'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '启动失败'
        msgType.value = 'err'
    } finally {
        starting.value = false
    }
}

async function poll() {
    if (!taskId.value) return
    try {
        const data = await fetchCoefficientProgress(taskId.value)
        taskProgress.value = data.progress
        if (data.status === 'done') {
            clearInterval(timer)
            result.value = data.result || null
            activeKey.value = 'base'
            msg.value = '预测完成'
            msgType.value = 'ok'
        } else if (data.status === 'error') {
            clearInterval(timer)
            msg.value = data.error || '预测失败'
            msgType.value = 'err'
        }
    } catch (e) {
        console.warn('轮询失败', e)
    }
}

watch(taskId, (v) => {
    clearInterval(timer)
    if (!v) return
    poll()
    timer = window.setInterval(poll, 1000)
})

onMounted(() => {
    loadNodes()
})
onBeforeUnmount(() => clearInterval(timer))

/* ---------------- 图表 option ---------------- */
const hours = computed(() => result.value?.hours || [])

/** ① 修正前：所有策略 × 半衰期的曲线 */
const multiStrategyOption = computed<EChartsOption>(() => {
    const curves = result.value?.all_coeffs_curves || []
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (v: any) => (typeof v === 'number' ? v.toFixed(4) : '—'),
        },
        legend: {
            top: 0,
            type: 'scroll',
            data: curves.map((c) => c.name),
            textStyle: { fontSize: 11 },
        },
        grid: { left: 60, right: 24, top: 48, bottom: 42 },
        xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 } },
        yAxis: { type: 'value', name: '系数' },
        series: curves.map((c) => ({
            name: c.name,
            type: 'line' as const,
            smooth: true,
            showSymbol: false,
            data: c.data,
        })),
    }
})

/** ② 修正后系数 */
const finalCurveOption = computed<EChartsOption>(() => ({
    tooltip: {
        trigger: 'axis',
        valueFormatter: (v: any) => (typeof v === 'number' ? v.toFixed(4) : '—'),
    },
    grid: { left: 60, right: 24, top: 28, bottom: 42 },
    xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 } },
    yAxis: { type: 'value', name: '系数' },
    series: [
        {
            name: '修正后系数',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: result.value?.coefficients || [],
            lineStyle: { color: '#2d6cdf', width: 2 },
            areaStyle: { opacity: 0.12 },
        },
    ],
}))

/** ③ 修正前后对比 */
const beforeAfterOption = computed<EChartsOption>(() => ({
    tooltip: {
        trigger: 'axis',
        valueFormatter: (v: any) => (typeof v === 'number' ? v.toFixed(4) : '—'),
    },
    legend: { top: 0, data: ['修正前', '修正后'] },
    grid: { left: 60, right: 24, top: 36, bottom: 42 },
    xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 } },
    yAxis: { type: 'value', name: '系数' },
    series: [
        {
            name: '修正前',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: result.value?.base_coefficients || [],
            lineStyle: { color: '#909399' },
        },
        {
            name: '修正后',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: result.value?.coefficients || [],
            lineStyle: { color: '#2d6cdf' },
        },
    ],
}))

/* ============ 天气图（面积图） ============ */
const weatherRows = computed(() => result.value?.weather_data || [])

function wcol(key: string): (number | null)[] {
    return weatherRows.value.map((r) => {
        const v = r[key]
        return typeof v === 'number' ? v : null
    })
}

const tempCloudOption = computed<EChartsOption>(() => ({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['体感温度', '云量'] },
    grid: { left: 60, right: 60, top: 36, bottom: 42 },
    xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 }, boundaryGap: false },
    yAxis: [
        { type: 'value', name: '℃' },
        { type: 'value', name: '%', max: 100 },
    ],
    series: [
        {
            name: '体感温度',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: wcol('apparent_temperature (°C)'),
            areaStyle: { opacity: 0.25 },
            lineStyle: { color: '#e6a23c' },
            itemStyle: { color: '#e6a23c' },
        },
        {
            name: '云量',
            type: 'line',
            smooth: true,
            showSymbol: false,
            yAxisIndex: 1,
            data: wcol('cloud_cover_low (%)'),
            areaStyle: { opacity: 0.18 },
            lineStyle: { color: '#2d6cdf' },
            itemStyle: { color: '#2d6cdf' },
        },
    ],
}))

const windHumidityOption = computed<EChartsOption>(() => ({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['风速', '湿度'] },
    grid: { left: 60, right: 60, top: 36, bottom: 42 },
    xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 }, boundaryGap: false },
    yAxis: [
        { type: 'value', name: 'km/h' },
        { type: 'value', name: '%', max: 100 },
    ],
    series: [
        {
            name: '风速',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: wcol('wind_speed_80m (km/h)'),
            areaStyle: { opacity: 0.25 },
            lineStyle: { color: '#67c23a' },
            itemStyle: { color: '#67c23a' },
        },
        {
            name: '湿度',
            type: 'line',
            smooth: true,
            showSymbol: false,
            yAxisIndex: 1,
            data: wcol('relative_humidity_2m (%)'),
            areaStyle: { opacity: 0.18 },
            lineStyle: { color: '#7f7f7f' },
            itemStyle: { color: '#7f7f7f' },
        },
    ],
}))

const radiationOption = computed<EChartsOption>(() => ({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['直接辐射', '散射辐射'] },
    grid: { left: 64, right: 24, top: 36, bottom: 42 },
    xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 }, boundaryGap: false },
    yAxis: { type: 'value', name: 'W/m²' },
    series: [
        {
            name: '直接辐射',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: wcol('direct_radiation (W/m²)'),
            areaStyle: { opacity: 0.3 },
            lineStyle: { color: '#e6a23c' },
            itemStyle: { color: '#e6a23c' },
        },
        {
            name: '散射辐射',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: wcol('diffuse_radiation (W/m²)'),
            areaStyle: { opacity: 0.25 },
            lineStyle: { color: '#2d6cdf' },
            itemStyle: { color: '#2d6cdf' },
        },
    ],
}))

/** ⑦ 修正明细 */
const correctionDetailOption = computed<EChartsOption>(() => {
    const details = result.value?.correction_details || []
    const keys = [
        ['pv_offset', '光伏'],
        ['temp_offset', '温度'],
        ['humidity_offset', '湿度'],
        ['wind_offset', '风速'],
        ['extreme_offset', '极端天气'],
        ['gen_risk_offset', '发电风险'],
        ['ml_offset', 'ML偏移'],
    ] as const
    return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { top: 0, data: keys.map((k) => k[1]) },
        grid: { left: 60, right: 24, top: 36, bottom: 42 },
        xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 3 } },
        yAxis: { type: 'value', name: '偏移量' },
        series: keys.map(([key, name]) => ({
            name,
            type: 'bar',
            stack: 'total',
            data: details.map((d: any) => d[key] ?? 0),
        })),
    }
})

/* ---------------- 导出 CSV ---------------- */
function exportCsv() {
    if (!result.value) return
    const rows = [['时段', '修正前系数', '修正后系数']]
    result.value.hours.forEach((h, i) => {
        rows.push([
            h,
            String(result.value!.base_coefficients[i] ?? ''),
            String(result.value!.coefficients[i] ?? ''),
        ])
    })
    const csv = '\uFEFF' + rows.map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `申报系数_${result.value.target_date}.csv`
    a.click()
    URL.revokeObjectURL(url)
}
</script>

<style scoped>
.form-card,
.chart-card,
.table-card {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 14px 18px;
}

.form-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 10px;
}

.form-row:last-child {
    margin-bottom: 0;
}

.form-row>label:first-child {
    font-size: 13px;
    color: #606266;
    min-width: 70px;
}

.inline-label {
    font-size: 13px;
    color: #606266;
    margin-left: 8px;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.input.small {
    width: 90px;
}

.unit {
    font-size: 12px;
    color: #909399;
}

.file-input {
    font-size: 13px;
}

.btn {
    height: 32px;
    padding: 0 16px;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
}

.btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.btn.primary:hover:not(:disabled) {
    background: #2459b8;
}

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

.btn.small {
    height: 26px;
    padding: 0 12px;
    font-size: 12px;
}

.btn:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
}

.msg {
    margin: 10px 0 0;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    display: inline-block;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}

.progress-tip {
    margin: 8px 0 0;
    font-size: 12px;
    color: #909399;
}

/* ===== 结果区左右分栏 ===== */
.result-layout {
    display: flex;
    gap: 12px;
    min-height: 480px;
}

.result-aside {
    width: 190px;
    flex-shrink: 0;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 8px 0;
    height: fit-content;
}

.toc-item {
    padding: 10px 16px;
    font-size: 13px;
    color: #606266;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    border-left: 3px solid transparent;
}

.toc-item:hover {
    background: #f5f7fa;
}

.toc-item.active {
    background: #ecf5ff;
    color: #2d6cdf;
    border-left-color: #2d6cdf;
    font-weight: 600;
}

.toc-item.disabled {
    color: #c0c4cc;
    cursor: not-allowed;
    background: transparent;
}

.result-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.summary-bar {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 10px 16px;
    font-size: 13px;
    color: #606266;
}

.summary-bar strong {
    color: #2d6cdf;
}

.chart-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.chart-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.chart-body {
    min-height: 420px;
}

.chart {
    width: 100%;
    height: 420px;
}

.table-wrap {
    max-height: 540px;
    overflow-y: auto;
    border: 1px solid #f0f2f5;
    border-radius: 4px;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.data-table th,
.data-table td {
    padding: 6px 12px;
    border-bottom: 1px solid #f0f2f5;
    text-align: center;
}

.data-table th {
    position: sticky;
    top: 0;
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    font-size: 12px;
    z-index: 1;
}
</style>