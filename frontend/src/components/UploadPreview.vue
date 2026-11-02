<template>
    <div class="upload-preview">
        <div class="preview-header">
            <span class="preview-title">📈 即时预览</span>
            <span class="preview-meta">{{ metaText }}</span>
            <span v-if="saved === true" class="tag ok">已写入数据库</span>
            <span v-else-if="saved === false" class="tag warn" :title="saveTip">
                仅内存预览（重启后需重新上传）
            </span>
        </div>

        <div class="preview-body">
            <div v-if="loading" class="preview-empty">加载中…</div>
            <div v-else-if="error" class="preview-empty err">{{ error }}</div>
            <div v-else-if="!option" class="preview-empty">暂无可预览的数据</div>
            <VChart v-else :option="option" autoresize class="preview-chart" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'
import { fetchLoadAnalysis, fetchPvAnalysis } from '@/api/modules/load'
import { fetchDayAheadUnified, fetchDayAheadPlant } from '@/api/modules/price'
import { fetchSpreadDailyPrices } from '@/api/modules/spread'

const props = defineProps<{
    datasetKey: string
    date: string
    nodeName?: string
    saved?: boolean
    saveTip?: string
}>()

const loading = ref(false)
const error = ref('')
const option = ref<EChartsOption | null>(null)

const metaText = computed(() => {
    const parts: string[] = []
    if (props.date) parts.push(`日期 ${props.date}`)
    if (props.nodeName) parts.push(`节点 ${props.nodeName}`)
    return parts.join(' · ')
})

async function load() {
    option.value = null
    error.value = ''
    if (!props.date) { error.value = '缺少日期'; return }
    if (props.datasetKey.includes('plant') && !props.nodeName) {
        error.value = '缺少节点'; return
    }

    loading.value = true
    try {
        switch (props.datasetKey) {
            case 'load': await renderLoadOrPv(true); break
            case 'pv': await renderLoadOrPv(false); break
            case 'day-ahead-unified': await renderDayAheadUnified(); break
            case 'day-ahead-plant': await renderDayAheadPlant(); break
            case 'spread-unified':
            case 'spread-plant': await renderSpread(); break
            default: error.value = '未知的数据类型'
        }
    } catch (e) {
        error.value = (e as Error).message || '预览加载失败'
    } finally {
        loading.value = false
    }
}

async function renderLoadOrPv(isLoad: boolean) {
    const fn = isLoad ? fetchLoadAnalysis : fetchPvAnalysis
    const data: any = await fn({ startDate: props.date, endDate: props.date })
    const series: any[] = data?.series || []
    if (!series.length) { error.value = '暂无数据'; return }

    const xLabels = (series[0].points || []).map((p: any) => p.time)
    option.value = lineOption(
        xLabels,
        series.map((s: any) => ({
            name: formatKind(s.kind),
            type: 'line' as const,
            smooth: true,
            showSymbol: false,
            data: (s.points || []).map((p: any) => p.value),
        })),
        'MW',
    )
}

async function renderDayAheadUnified() {
    const data: any = await fetchDayAheadUnified({ date: props.date })
    const points: any[] = data?.points || []
    if (!points.length) { error.value = '暂无数据'; return }
    option.value = lineOption(
        points.map((p) => p.hour),
        [{
            name: '日前电价', type: 'line', smooth: true, showSymbol: false,
            data: points.map((p) => p.value), itemStyle: { color: '#2d6cdf' }
        }],
        '元/MWh',
    )
}

async function renderDayAheadPlant() {
    const data: any = await fetchDayAheadPlant({ date: props.date, nodeName: props.nodeName! })
    const points: any[] = data?.points || []
    if (!points.length) { error.value = '暂无数据'; return }
    option.value = lineOption(
        points.map((p) => p.time),
        [{
            name: '日前电价', type: 'line', smooth: true, showSymbol: false,
            data: points.map((p) => p.value), itemStyle: { color: '#2d6cdf' }
        }],
        '元/MWh',
    )
}

async function renderSpread() {
    const isPlant = props.datasetKey === 'spread-plant'
    const data: any = await fetchSpreadDailyPrices({
        date: props.date,
        nodeType: isPlant ? 'plant' : 'unified',
        nodeName: isPlant ? props.nodeName : undefined,
    })
    if (!data?.hours?.length) { error.value = '暂无数据'; return }
    option.value = lineOption(
        data.hours,
        [
            {
                name: '日前', type: 'line', smooth: true, showSymbol: false,
                data: data.dayAhead, itemStyle: { color: '#2d6cdf' }
            },
            {
                name: '实时', type: 'line', smooth: true, showSymbol: false,
                data: data.realTime, itemStyle: { color: '#e6a23c' }
            },
        ],
        '元/MWh',
    )
}

function lineOption(xLabels: string[], series: any[], yName: string): EChartsOption {
    return {
        tooltip: { trigger: 'axis', valueFormatter: (v: any) => (typeof v === 'number' ? v.toFixed(3) : '—') },
        legend: { top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 20, top: 32, bottom: 30 },
        xAxis: { type: 'category', data: xLabels, axisLabel: { interval: 'auto', fontSize: 10 } },
        yAxis: { type: 'value', name: yName, nameTextStyle: { fontSize: 11 } },
        series,
    }
}

function formatKind(kind: string): string {
    const map: Record<string, string> = { actual: '实际', forecast: '预测', pv: '光伏实际', pv_forecast: '光伏预测' }
    return map[kind] || kind
}

watch([() => props.datasetKey, () => props.date, () => props.nodeName], () => { if (props.date) load() }, { immediate: true })
</script>

<style scoped>
.upload-preview {
    margin-top: 12px;
    background: #fafbfc;
    border: 1px solid #f0f2f5;
    border-radius: 6px;
    padding: 10px 12px;
}

.preview-header {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 6px;
}

.preview-title {
    font-size: 13px;
    font-weight: 600;
    color: #1f2d3d;
}

.preview-meta {
    font-size: 12px;
    color: #909399;
    flex: 1;
}

.tag {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    line-height: 1.4;
}

.tag.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.tag.warn {
    background: #fdf6ec;
    color: #e6a23c;
    cursor: help;
}

.preview-body {
    min-height: 240px;
}

.preview-chart {
    width: 100%;
    height: 240px;
}

.preview-empty {
    height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    font-size: 13px;
}

.preview-empty.err {
    color: #f56c6c;
}
</style>