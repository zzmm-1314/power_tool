<template>
    <PageContainer title="滚撮分析（市场级）">
        <!-- 控制栏 -->
        <div class="control-bar">
            <div class="form-group">
                <label>标的日 (D日)</label>
                <input type="date" v-model="params.date" class="input" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '计算中...' : '🔍 查询分析' }}
            </button>
            <button class="btn-upload" :disabled="uploading" @click="triggerUpload">
                {{ uploading ? '上传中...' : '📤 上传市场滚撮' }}
            </button>
            <input ref="fileInputRef" type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                @change="handleUpload" />
        </div>

        <!-- 图例说明 -->
        <div class="legend-tip">
            <span>日前价格：</span>
            <span class="dot price-low"></span> &lt; 350
            <span class="dot price-high"></span> &gt; 350
            <span class="gap"></span>
            <span>价差：</span>
            <span class="dot spread-neg"></span> &lt; 0
            <span class="dot spread-pos"></span> &gt; 0
            <span class="gap"></span>
            <span class="hint">日前价格为 24 个整点时段均值；鼠标悬浮单元格可放大查看</span>
        </div>

        <!-- 表格区 -->
        <div class="result-card">
            <div class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col col-time">时段</th>
                            <th>当日日前价格</th>

                            <th class="group-start">{{ dateD2 }} 电量</th>
                            <th>{{ dateD2 }} 电价</th>
                            <th>{{ dateD2 }} 价差</th>

                            <th class="group-start">{{ dateD3 }} 电量</th>
                            <th>{{ dateD3 }} 电价</th>
                            <th>{{ dateD3 }} 价差</th>

                            <th class="group-start">{{ dateD4 }} 电量</th>
                            <th>{{ dateD4 }} 电价</th>
                            <th>{{ dateD4 }} 价差</th>

                            <th class="group-start">市场合计 电量</th>
                            <th>市场合计 电价</th>
                            <th>市场合计 价差</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in tableData" :key="idx">
                            <td class="sticky-col col-time">{{ row.time }}</td>
                            <td :style="priceStyle(row.dayAheadPrice)">{{ format(row.dayAheadPrice) }}</td>

                            <td class="group-start">{{ format(row.d2Qty) }}</td>
                            <td>{{ format(row.d2Price) }}</td>
                            <td :style="diffStyle(row.d2Diff)">{{ format(row.d2Diff) }}</td>

                            <td class="group-start">{{ format(row.d3Qty) }}</td>
                            <td>{{ format(row.d3Price) }}</td>
                            <td :style="diffStyle(row.d3Diff)">{{ format(row.d3Diff) }}</td>

                            <td class="group-start">{{ format(row.d4Qty) }}</td>
                            <td>{{ format(row.d4Price) }}</td>
                            <td :style="diffStyle(row.d4Diff)">{{ format(row.d4Diff) }}</td>

                            <td class="group-start">{{ format(row.marketQty) }}</td>
                            <td>{{ format(row.marketPrice) }}</td>
                            <td :style="diffStyle(row.marketDiff)">{{ format(row.marketDiff) }}</td>
                        </tr>
                        <tr v-if="!tableData.length">
                            <td colspan="14" class="empty-row">
                                {{ loading ? '加载中...' : '请选择标的日并点击查询' }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { request } from '@/api/request'

const loading = ref(false)
const uploading = ref(false)
const params = reactive({ date: '' })
const tableData = ref<any[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

// 后端返回的 D-2/D-3/D-4 日期（用于表头）
const apiDates = reactive({ d2: '', d3: '', d4: '' })

const dateD2 = computed(() => apiDates.d2 || 'D-2')
const dateD3 = computed(() => apiDates.d3 || 'D-3')
const dateD4 = computed(() => apiDates.d4 || 'D-4')

function format(v: number | null | undefined) {
    if (v == null || isNaN(v)) return '-'
    return v.toFixed(3)
}

function priceStyle(v: number | null) {
    if (v == null) return {}
    const base = 350
    if (v < base) {
        const intensity = Math.min((base - v) / 200, 1)
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: '#303133' }
    } else {
        const intensity = Math.min((v - base) / 200, 1)
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: '#303133' }
    }
}

function diffStyle(v: number | null) {
    if (v == null || v === 0) return {}
    const intensity = Math.min(Math.abs(v) / 100, 1)
    if (v > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: '#303133' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: '#303133' }
    }
}

async function loadData() {
    if (!params.date) return alert('请选择标的日')
    loading.value = true
    try {
        const res: any = await request({
            url: '/rolling/analysis',
            method: 'get',
            params: { targetDate: params.date },
        })
        tableData.value = res.rows || []
        apiDates.d2 = res.d2Date || ''
        apiDates.d3 = res.d3Date || ''
        apiDates.d4 = res.d4Date || ''
    } catch (err: any) {
        alert('查询失败：' + (err.message || '后端服务异常'))
        tableData.value = []
    } finally {
        loading.value = false
    }
}

function triggerUpload() {
    fileInputRef.value?.click()
}

async function handleUpload(e: Event) {
    const target = e.target as HTMLInputElement
    const files = target.files
    if (!files || !files.length) return

    uploading.value = true
    const fd = new FormData()
    for (let i = 0; i < files.length; i++) {
        fd.append('files', files[i])
    }

    try {
        const res: any = await request({
            url: '/rolling/market-upload',
            method: 'post',
            data: fd,
        })
        alert(`上传成功，共 ${res.count || 0} 条`)
        await loadData()
    } catch (err: any) {
        alert('上传失败：' + (err.message || '未知错误'))
    } finally {
        uploading.value = false
        target.value = ''
    }
}
</script>

<style scoped>
/* ===== 控制栏 ===== */
.control-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #fff;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex-wrap: wrap;
}

.form-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.form-group label {
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
    width: 140px;
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

.btn-upload {
    height: 34px;
    padding: 0 16px;
    background: #fff;
    color: #2d6cdf;
    border: 1px solid #2d6cdf;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
}

.btn-upload:hover:not(:disabled) {
    background: #ecf5ff;
}

.btn-upload:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.hidden-input {
    display: none;
}

/* ===== 图例 ===== */
.legend-tip {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    padding: 10px 16px;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    font-size: 12px;
    color: #606266;
    margin-top: 12px;
    flex-wrap: wrap;
}

.dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid #ebeef5;
}

.dot.price-low,
.dot.spread-neg {
    background: rgba(103, 194, 58, 0.6);
}

.dot.price-high,
.dot.spread-pos {
    background: rgba(245, 108, 108, 0.6);
}

.gap {
    width: 16px;
}

.hint {
    color: #909399;
    margin-left: auto;
}

/* ===== 表格卡片 ===== */
.result-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 16px;
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    max-height: calc(100vh - 240px);
}

.table-wrap {
    flex: 1;
    overflow: auto;
}

/* ===== 表格 ===== */
.data-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
    text-align: center;
    white-space: nowrap;
}

.data-table th,
.data-table td {
    padding: 4px 10px;
    /* 保持行高紧凑（上次已缩半） */
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
    font-variant-numeric: tabular-nums;
    position: relative;
    /* ← hover 伪元素需要 */
    background: #fff;
    /* 让 inherit 拿到白底 */
}

.data-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    position: sticky;
    top: 0;
    z-index: 2;
}

/* 分组左边框 */
.group-start {
    border-left: 2px solid #dcdfe6;
}

.data-table th.group-start {
    border-left: 2px solid #c0c4cc;
}

/* ===== 单元格悬浮突出 ===== */
.data-table tbody td {
    cursor: crosshair;
    transition: box-shadow 0.12s ease;
}

/* 非 sticky 单元格：伪元素外扩 3px，继承原背景色（保留色阶），描边 + 阴影浮起 */
.data-table tbody td:not(.sticky-col):hover {
    z-index: 20;
}

.data-table tbody td:not(.sticky-col):hover::before {
    content: '';
    position: absolute;
    inset: -3px;
    border-radius: 4px;
    background: inherit;
    box-shadow: 0 0 0 2px #1f2d3d, 0 8px 24px rgba(0, 0, 0, 0.35);
    z-index: -1;
    pointer-events: none;
}

/* 时段列（sticky）悬浮改为浅蓝背景，不用伪元素避免 sticky 错位 */
.sticky-col {
    position: sticky;
    background: #f5f7fa;
    z-index: 1;
    border-right: 1px solid #dcdfe6;
    left: 0;
    width: 96px;
    font-weight: 500;
}

.data-table th.sticky-col {
    z-index: 3;
}

.data-table tbody td.sticky-col:hover {
    background: #ecf5ff;
    color: #2d6cdf;
    font-weight: 700;
}

/* 空数据行 */
.empty-row {
    text-align: center;
    color: #909399;
    padding: 40px 0 !important;
}
</style>