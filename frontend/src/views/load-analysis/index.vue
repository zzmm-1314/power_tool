<template>
    <PageContainer :title="`负荷分析 · ${tab === 'load' ? '负荷曲线' : '光伏出力'}`">
        <template #extra>
            <div class="tab-group">
                <button class="tab-btn" :class="{ active: tab === 'load' }" @click="switchTab('load')">
                    负荷曲线
                </button>
                <button class="tab-btn" :class="{ active: tab === 'pv' }" @click="switchTab('pv')">
                    光伏出力
                </button>
            </div>

            <button class="btn-upload" @click="appStore.openUpload(tab === 'load' ? 'load' : 'pv')">
                📤 上传 Excel
            </button>
            <DataSourceTag :source="source" />
            <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                @update:end="dateEnd = $event" />
            <button class="btn" @click="load">查询</button>
        </template>

        <ChartPanel :title="tab === 'load'
            ? '96 点负荷曲线（浙江电网）'
            : '96 点光伏出力曲线（浙江电网）'" :option="chartOption" :loading="loading" height="480px" />

        <!-- 差值图例：负荷 / 光伏都可能有 -->
        <div v-if="diffData" class="legend-tip">
            <span class="dot positive"></span> 预测 &gt; 实际
            <span class="dot negative"></span> 预测 &lt; 实际
            <span class="tip-text">（条形图为次坐标轴：预测 − 实际，单位 MW）</span>
        </div>

        <TempDataPanel :data-type="tab === 'load' ? 'load' : 'pv'" :date="dateStart" />
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type {
    EChartsOption,
    LineSeriesOption,
    BarSeriesOption,
} from 'echarts'
import PageContainer from '@/components/PageContainer.vue'
import ChartPanel from '@/components/ChartPanel.vue'
import DataSourceTag from '@/components/DataSourceTag.vue'
import TempDataPanel from '@/components/TempDataPanel.vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import { fetchLoadAnalysis, fetchPvAnalysis } from '@/api/modules/load'
import type { DataSource, LoadSeries } from '@/types'
import { useAppStore } from '@/stores/app'

type TabKey = 'load' | 'pv'

const appStore = useAppStore()

const tab = ref<TabKey>('load')
const dateStart = ref(new Date().toISOString().slice(0, 10))
const dateEnd = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const source = ref<DataSource>('empty')

const loadSeries = ref<LoadSeries[]>([])
const pvSeries = ref<LoadSeries[]>([])

/* ---------- 当前激活的 series ---------- */
const activeSeries = computed<LoadSeries[]>(() =>
    tab.value === 'load' ? loadSeries.value : pvSeries.value,
)

/* ---------- 日期列表（按升序去重） ---------- */
const allDates = computed<string[]>(() => {
    const dates = new Set<string>()
    activeSeries.value.forEach((s) => {
        if (s.date) dates.add(s.date)
    })
    return Array.from(dates).sort()
})

const multiDate = computed(() => allDates.value.length > 1)

/* ---------- X 轴：多日拼接 96×N 个时间标签 ---------- */
const xLabels = computed<string[]>(() => {
    // 兼容无 date 字段的单日数据
    if (!allDates.value.length) {
        const first = activeSeries.value.find((s) => s.points.length)
        return first ? first.points.map((p) => p.time) : []
    }

    const labels: string[] = []
    allDates.value.forEach((d) => {
        const daySeries = activeSeries.value.find(
            (s) => s.date === d && s.points.length,
        )
        if (!daySeries) return
        daySeries.points.forEach((p) => {
            labels.push(multiDate.value ? `${d.slice(5)} ${p.time}` : p.time)
        })
    })
    return labels
})

/* ---------- 按 kind 拼接后的数据 ----------
 *  key = kind，value = 与 xLabels 等长的数组
 *  例：actual / forecast 各自成为「3 天 × 96 = 288」长度的完整曲线
 */
const kindDataMap = computed<Record<string, (number | null)[]>>(() => {
    const map: Record<string, (number | null)[]> = {}

    const kinds = new Set<string>()
    activeSeries.value.forEach((s) => kinds.add(s.kind))

    const totalLen = xLabels.value.length
    kinds.forEach((k) => {
        map[k] = new Array(totalLen).fill(null)
    })

    let offset = 0
    allDates.value.forEach((d) => {
        const dayList = activeSeries.value.filter(
            (s) => s.date === d && s.points.length,
        )
        const dayLen = dayList[0]?.points.length || 0

        dayList.forEach((s) => {
            const arr = map[s.kind]
            s.points.forEach((p, i) => {
                if (offset + i < totalLen) {
                    arr[offset + i] = p.value
                }
            })
        })
        offset += dayLen
    })

    return map
})

/* ---------- 差值：预测 − 实际（按拼接位置对齐） ---------- */
const diffData = computed<(number | null)[] | null>(() => {
    const actualKind = tab.value === 'load' ? 'actual' : 'pv'
    const forecastKind = tab.value === 'load' ? 'forecast' : 'pv_forecast'

    const actual = kindDataMap.value[actualKind]
    const forecast = kindDataMap.value[forecastKind]
    if (!actual || !forecast) return null
    if (actual.every((v) => v == null) || forecast.every((v) => v == null)) {
        return null
    }

    const result: (number | null)[] = []
    for (let i = 0; i < actual.length; i++) {
        const a = actual[i]
        const f = forecast[i]
        if (a == null || f == null) {
            result.push(null)
        } else {
            result.push(Number((f - a).toFixed(2)))
        }
    }
    return result
})

/* ---------- 系列名称 ---------- */
function seriesNameByKind(kind: string): string {
    if (kind === 'actual') return '浙江电网（实际）'
    if (kind === 'forecast') return '浙江电网（预测）'
    if (kind === 'pv') return '光伏总出力（实际）'
    if (kind === 'pv_forecast') return '光伏总出力（预测）'
    return kind
}

/* ---------- 图表配置 ---------- */
const chartOption = computed<EChartsOption>(() => {
    const kindMap = kindDataMap.value
    const hasDiff = !!diffData.value
    const kindCount = Object.keys(kindMap).length

    /* ===== 折线（每个 kind 一条拼接后的完整曲线） ===== */
    const lineSeries: LineSeriesOption[] = []
    Object.entries(kindMap).forEach(([kind, data]) => {
        lineSeries.push({
            name: seriesNameByKind(kind),
            type: 'line',
            smooth: true,
            showSymbol: false,
            yAxisIndex: 0,
            data,
            areaStyle: kindCount === 1 ? { opacity: 0.12 } : undefined,
            z: 3,
        })
    })

    /* ===== 差值柱（多日时缩窄，便于通过 dataZoom 分段观察） ===== */
    const barSeries: BarSeriesOption[] = hasDiff
        ? [
            {
                name: '差值（预测 − 实际）',
                type: 'bar',
                yAxisIndex: 1,
                barMaxWidth: multiDate.value ? 4 : 14,
                data: diffData.value!.map((v) => ({
                    value: v,
                    itemStyle: {
                        color:
                            v == null
                                ? 'transparent'
                                : v >= 0
                                    ? 'rgba(103, 194, 58, 0.55)'
                                    : 'rgba(245, 108, 108, 0.55)',
                        borderRadius: 2,
                    },
                })),
                z: 1,
            },
        ]
        : []

    const legendData = [
        ...lineSeries.map((s) => s.name as string),
        ...(hasDiff ? ['差值（预测 − 实际）'] : []),
    ]

    const yAxis: EChartsOption['yAxis'] = hasDiff
        ? [
            {
                type: 'value',
                name: 'MW',
                position: 'left',
                nameTextStyle: { color: '#606266' },
            },
            {
                type: 'value',
                name: '差值(MW)',
                position: 'right',
                nameTextStyle: { color: '#909399' },
                axisLine: { show: false },
                splitLine: { show: false },
                axisLabel: { color: '#909399' },
            },
        ]
        : { type: 'value', name: 'MW' }
    const xAxis: EChartsOption['xAxis'] = {
        type: 'category',
        data: xLabels.value,
        axisLabel: { interval: 7 },
    }
    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            valueFormatter: (v) =>
                typeof v === 'number' ? `${v.toFixed(2)} MW` : '—',
        },
        legend: {
            top: 0,
            data: legendData,
            show: legendData.length > 1,
        },
        grid: {
            left: 70,
            right: hasDiff ? 80 : 24,
            top: legendData.length > 1 ? 40 : 32,
            bottom: 60,
        },
        xAxis: {
            type: 'category',
            data: xLabels.value,
            axisLabel: {
                // 单日每 2 小时一档；多日按 dataZoom 自动稀疏
                interval: multiDate.value ? 'auto' : 7,
                rotate: multiDate.value ? 0 : 0,
            },
        },
        yAxis,
        dataZoom: [
            { type: 'inside' },
            { type: 'slider', height: 18, bottom: 8 },
        ],
        series: [...barSeries, ...lineSeries],
    }
})

/* ---------- 加载 ---------- */
async function load() {
    loading.value = true
    try {
        const params = {
            startDate: dateStart.value || undefined,
            endDate: dateEnd.value || undefined,
        }
        if (!params.startDate || !params.endDate) {
            source.value = 'empty'
            loadSeries.value = []
            pvSeries.value = []
            return
        }

        if (tab.value === 'load') {
            const data = await fetchLoadAnalysis(params)
            source.value = data.source
            loadSeries.value = data.series
        } else {
            const data = await fetchPvAnalysis(params)
            source.value = data.source
            pvSeries.value = data.series
        }
    } catch (e) {
        console.error(e)
        source.value = 'empty'
        if (tab.value === 'load') loadSeries.value = []
        else pvSeries.value = []
    } finally {
        loading.value = false
    }
}

async function switchTab(t: TabKey) {
    if (tab.value === t) return
    tab.value = t
    await load()
}

watch(() => appStore.dataVersion, () => load())
onMounted(load)
</script>

<style scoped>
.tab-group {
    display: inline-flex;
    padding: 2px;
    background: #f5f7fa;
    border-radius: 6px;
    margin-right: 4px;
}

.tab-btn {
    height: 26px;
    padding: 0 14px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #606266;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}

.tab-btn:hover {
    color: #2d6cdf;
}

.tab-btn.active {
    background: #fff;
    color: #2d6cdf;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.input {
    height: 30px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
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

.legend-tip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    font-size: 12px;
    color: #606266;
}

.legend-tip .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
}

.legend-tip .dot.positive {
    background: rgba(103, 194, 58, 0.55);
}

.legend-tip .dot.negative {
    background: rgba(245, 108, 108, 0.55);
}

.legend-tip .tip-text {
    margin-left: 8px;
    color: #909399;
}
</style>