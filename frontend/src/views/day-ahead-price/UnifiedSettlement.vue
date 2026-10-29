<template>
    <PageContainer title="日前电价 · 统一结算点">
        <template #extra>
            <button class="btn-upload" @click="appStore.openUpload('day-ahead-unified')">
                📤 上传 Excel
            </button>

            <DataSourceTag :source="source" />
            <label class="lbl">日期</label>
            <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                @update:end="dateEnd = $event" />
            <button class="btn" @click="load">刷新</button>
        </template>

        <p v-if="!heatmap.dates.length" class="empty-tip">
            暂无数据，请点击右上角「📤 上传 Excel」上传
            <code>日前市场出清负荷侧电价YYYYMMDD.xlsx</code>
        </p>

        <!-- ===== 新热力图 ===== -->
        <HeatmapGrid v-else mode="price" :base-price="350" :dates="heatmap.dates" :hours="heatmap.hours"
            :matrix="heatmap.matrix" :daily-avg="dailyAvg" />
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import DataSourceTag from '@/components/DataSourceTag.vue'
import { fetchUnifiedHeatmap, type HeatmapData } from '@/api/modules/price'
import type { DataSource } from '@/types'
import { useAppStore } from '@/stores/app'
import DateRangeInput from '@/components/DateRangeInput.vue'
import HeatmapGrid from '@/components/HeatmapGrid.vue'
const appStore = useAppStore()

const loading = ref(false)
const dateStart = ref('')
const dateEnd = ref('')
const source = ref<DataSource>('empty')
const heatmap = ref<HeatmapData>({
    dates: [],
    hours: [],
    matrix: [],
    source: 'empty',
    minValue: 0,
    maxValue: 0,
})

/* ---------- 每日均值（按列计算，3 位小数） ---------- */
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

/* ---------- 加载 ---------- */
async function load() {
    if (!dateStart.value || !dateEnd.value) {
        heatmap.value = {
            dates: [], hours: [], matrix: [],
            source: 'empty', minValue: 0, maxValue: 0,
        }
        return
    }
    loading.value = true
    try {
        const data = await fetchUnifiedHeatmap({
            startDate: dateStart.value,
            endDate: dateEnd.value,
        })
        heatmap.value = data
        source.value = data.source
    } catch (e) {
        console.error(e)
        source.value = 'empty'
        heatmap.value = {
            dates: [], hours: [], matrix: [],
            source: 'empty', minValue: 0, maxValue: 0,
        }
    } finally {
        loading.value = false
    }
}

/* 上传/删除后自动刷新 */
watch(() => appStore.dataVersion, () => load())

onMounted(() => {
    initDateRange()
    load()
})
</script>

<style scoped>
.lbl {
    font-size: 13px;
    color: #606266;
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
    min-width: 88px;
    /* 从 76px → 88px */
}

.price-table th,
.price-table td {
    padding: 6px 10px;
    text-align: center;
    white-space: nowrap;
    border-right: 1px solid #eef0f3;
    border-bottom: 1px solid #eef0f3;
    min-width: 88px;
    /* 从 76px → 88px */
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
    min-width: 76px;
}

.sticky-col {
    position: sticky;
    left: 0;
    z-index: 3;
    background: #f5f7fa !important;
    color: #303133;
    font-weight: 500;
    text-align: center;
}

.corner {
    z-index: 4;
    top: 0;
    left: 0;
    min-width: 100px;
}

.value-td {
    min-width: 76px;
    font-variant-numeric: tabular-nums;
    transition: transform 0.1s, box-shadow 0.1s;
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

/* ===== 日均值行 ===== */
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

/* ===== 总体均值条 ===== */
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

/* ================= 色阶图例 ================= */
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