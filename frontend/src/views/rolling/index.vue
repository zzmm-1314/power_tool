<template>
    <PageContainer title="滚撮分析">
        <template #extra>
            <button class="btn-upload" :disabled="!html || loading" @click="doExport">
                📥 导出 Excel
            </button>
        </template>

        <!-- 输入区 -->
        <div class="card">
            <div class="form-row">
                <label>均值天数</label>
                <input v-model.number="avgDays" type="number" min="1" max="60" class="input small" />
                <span class="unit">天</span>

                <label class="inline-label">参考日期（可选）</label>
                <input v-model="refDate" type="date" class="input" />
                <span class="hint">（不填则使用全部可用数据）</span>

                <button class="btn primary" :disabled="!html || loading" @click="doAnalyze">
                    {{ loading ? '分析中...' : '开始分析' }}
                </button>
            </div>

            <div class="form-row column">
                <label>HTML 片段</label>
                <textarea v-model="html" class="textarea" rows="10"
                    placeholder="粘贴滚动撮合市场盘口表格的 HTML（包含 el-table__body 或 el-table__body-wrapper）"></textarea>
            </div>

            <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
            <p v-if="result" class="dates-tip">
                已使用 {{ result.avg_days }} 天均值，日期：
                <strong>{{ result.dates_used.join('、') }}</strong>
            </p>
        </div>

        <!-- 结果区 -->
        <template v-if="result && result.rows.length">
            <!-- 图 1：价格曲线 -->
            <div class="card chart-card">
                <div class="chart-title">买1价 / 卖1价 / 日前均价</div>
                <div class="chart-body">
                    <VChart :option="priceOption" autoresize class="chart" />
                </div>
            </div>

            <!-- 图 2：价差柱 -->
            <div class="card chart-card">
                <div class="chart-title">买1价 − 日前均价 / 卖1价 − 日前均价</div>
                <div class="chart-body">
                    <VChart :option="diffOption" autoresize class="chart" />
                </div>
            </div>

            <!-- 表格 -->
            <div class="card">
                <div class="chart-title">明细（{{ result.rows.length }} 条）</div>
                <div class="table-wrap scroll-y">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>时段</th>
                                <th>最新价</th>
                                <th>买1价</th>
                                <th>卖1价</th>
                                <th>日前均价</th>
                                <th>买1-均价</th>
                                <th>卖1-均价</th>
                                <th>成交方向</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="r in result.rows" :key="r.hour">
                                <td>{{ r.hour_label }}</td>
                                <td>{{ fmt(r.latest) }}</td>
                                <td>{{ fmt(r.bid1) }}</td>
                                <td>{{ fmt(r.ask1) }}</td>
                                <td>{{ fmt(r.avg_price) }}</td>
                                <td :class="diffClass(r.bid1_diff)">{{ fmtSigned(r.bid1_diff) }}</td>
                                <td :class="diffClass(r.ask1_diff)">{{ fmtSigned(r.ask1_diff) }}</td>
                                <td>{{ r.direction || '—' }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </template>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import PageContainer from '@/components/PageContainer.vue'
import {
    analyzeRolling,
    exportRolling,
    type RollingResult,
} from '@/api/modules/rolling'

const html = ref('')
const avgDays = ref(3)
const refDate = ref('')
const loading = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')
const result = ref<RollingResult | null>(null)

function fmt(v: number | null): string {
    if (v == null) return '—'
    return Number(v).toFixed(3)
}
function fmtSigned(v: number | null): string {
    if (v == null) return '—'
    const sign = v > 0 ? '+' : ''
    return `${sign}${Number(v).toFixed(3)}`
}
function diffClass(v: number | null): string {
    if (v == null) return ''
    return v > 0 ? 'diff-pos' : v < 0 ? 'diff-neg' : ''
}

async function doAnalyze() {
    msg.value = ''
    loading.value = true
    try {
        const res = await analyzeRolling({
            html: html.value,
            avgDays: avgDays.value,
            refDate: refDate.value || undefined,
        })
        result.value = res
        msg.value = `分析完成，共 ${res.rows.length} 条时段数据`
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '分析失败'
        msgType.value = 'err'
        result.value = null
    } finally {
        loading.value = false
    }
}

async function doExport() {
    msg.value = ''
    try {
        await exportRolling({
            html: html.value,
            avgDays: avgDays.value,
            refDate: refDate.value || undefined,
        })
        msg.value = '导出成功'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '导出失败'
        msgType.value = 'err'
    }
}

/* ---------------- 图表 ---------------- */
const hours = computed(() => (result.value?.rows || []).map((r) => r.hour_label))

const priceOption = computed<EChartsOption>(() => {
    const rows = result.value?.rows || []
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (v: any) =>
                typeof v === 'number' ? v.toFixed(3) : '—',
        },
        legend: { top: 0, data: ['买1价', '卖1价', '日前均价'] },
        grid: { left: 60, right: 24, top: 36, bottom: 42 },
        xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 2 } },
        yAxis: { type: 'value', name: '元/MWh' },
        series: [
            {
                name: '买1价',
                type: 'line',
                smooth: true,
                showSymbol: false,
                data: rows.map((r) => r.bid1),
                lineStyle: { color: '#67c23a' },
            },
            {
                name: '卖1价',
                type: 'line',
                smooth: true,
                showSymbol: false,
                data: rows.map((r) => r.ask1),
                lineStyle: { color: '#f56c6c' },
            },
            {
                name: '日前均价',
                type: 'line',
                smooth: true,
                showSymbol: false,
                data: rows.map((r) => r.avg_price),
                lineStyle: { color: '#2d6cdf', type: 'dashed' },
            },
        ],
    }
})

const diffOption = computed<EChartsOption>(() => {
    const rows = result.value?.rows || []
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (v: any) =>
                typeof v === 'number' ? v.toFixed(3) : '—',
        },
        legend: { top: 0, data: ['买1价−均价', '卖1价−均价'] },
        grid: { left: 64, right: 24, top: 36, bottom: 42 },
        xAxis: { type: 'category', data: hours.value, axisLabel: { interval: 2 } },
        yAxis: { type: 'value', name: '价差(元/MWh)' },
        series: [
            {
                name: '买1价−均价',
                type: 'bar',
                data: rows.map((r) => ({
                    value: r.bid1_diff,
                    itemStyle: {
                        color:
                            r.bid1_diff == null
                                ? 'transparent'
                                : r.bid1_diff >= 0
                                    ? 'rgba(103,194,58,0.7)'
                                    : 'rgba(245,108,108,0.7)',
                    },
                })),
            },
            {
                name: '卖1价−均价',
                type: 'bar',
                data: rows.map((r) => ({
                    value: r.ask1_diff,
                    itemStyle: {
                        color:
                            r.ask1_diff == null
                                ? 'transparent'
                                : r.ask1_diff >= 0
                                    ? 'rgba(103,194,58,0.7)'
                                    : 'rgba(245,108,108,0.7)',
                    },
                })),
            },
        ],
    }
})
</script>

<style scoped>
.card {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.form-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.form-row>label:first-child {
    font-size: 13px;
    color: #606266;
    min-width: 70px;
}

.form-row.column {
    flex-direction: column;
    align-items: stretch;
}

.form-row.column>label:first-child {
    min-width: auto;
    margin-bottom: 4px;
}

.inline-label {
    font-size: 13px;
    color: #606266;
    margin-left: 8px;
}

.unit {
    font-size: 12px;
    color: #909399;
}

.hint {
    font-size: 12px;
    color: #909399;
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

.textarea {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'Consolas', 'Monaco', monospace;
    outline: none;
    resize: vertical;
}

.textarea:focus {
    border-color: #2d6cdf;
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

.btn:disabled {
    color: #fff;
    background: #a0b4d8;
    cursor: not-allowed;
}

.msg {
    margin: 0;
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

.dates-tip {
    margin: 0;
    font-size: 12px;
    color: #606266;
}

.dates-tip strong {
    color: #2d6cdf;
}

.chart-card .chart-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.chart-body {
    min-height: 360px;
}

.chart {
    width: 100%;
    height: 360px;
}

.table-wrap {
    max-height: 460px;
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
    padding: 6px 10px;
    border-bottom: 1px solid #f0f2f5;
    text-align: center;
    white-space: nowrap;
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

.diff-pos {
    color: #67c23a;
    font-weight: 600;
}

.diff-neg {
    color: #f56c6c;
    font-weight: 600;
}
</style>