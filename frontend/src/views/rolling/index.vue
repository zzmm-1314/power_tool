<template>
    <PageContainer title="滚撮分析（市场级）">
        <!-- 控制栏 -->
        <div class="control-bar">
            <div class="form-group">
                <label>标的日 (D日)</label>
                <input type="date" v-model="params.date" class="input" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData(true)">
                {{ loading ? '计算中...' : '🔍 查询分析' }}
            </button>
            <button class="btn-upload" :disabled="uploading" @click="triggerUpload">
                {{ uploading ? '上传中...' : '📤 上传市场滚撮' }}
            </button>
            <input ref="fileInputRef" type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                @change="handleUpload" />
            <span class="source-tag" :class="sourceCls">{{ sourceText }}</span>
        </div>

        <!-- 数据提示 -->
        <div v-if="tips.length" class="tips">
            <span v-for="(t, i) in tips" :key="i" class="tip-item">{{ t }}</span>
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
                                <template v-if="loading">加载中...</template>
                                <template v-else-if="!params.date">请选择标的日并点击查询</template>
                                <template v-else>
                                    暂无数据：该标的日既没有日前价格，也没有 D-2/D-3/D-4 的市场滚撮记录<br />
                                    可先上传日前电价与市场滚撮数据，或更换标的日后再查
                                </template>
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
const params = reactive({ date: todayStr() })
const tableData = ref<any[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

function todayStr() {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 后端返回的 D-2/D-3/D-4 日期（用于表头）
const apiDates = reactive({ d2: '', d3: '', d4: '' })

// 日前价格来源与数据缺口提示
const dayAheadSource = ref<'jiangsu' | 'zhejiang' | 'mixed' | 'none' | ''>('')
const dayAheadHours = ref(0)
const marketDates = reactive({ d2: false, d3: false, d4: false })

const dateD2 = computed(() => apiDates.d2 || 'D-2')
const dateD3 = computed(() => apiDates.d3 || 'D-3')
const dateD4 = computed(() => apiDates.d4 || 'D-4')

const sourceText = computed(() => {
    switch (dayAheadSource.value) {
        case 'jiangsu':
            return '● 日前价格：江苏库'
        case 'zhejiang':
            return '● 日前价格：浙江库（上传数据）'
        case 'mixed':
            return '● 日前价格：江苏库 + 浙江库补齐'
        case 'none':
            return '○ 日前价格：无数据'
        default:
            return '○ 尚未查询'
    }
})

const sourceCls = computed(() => ({
    js: dayAheadSource.value === 'jiangsu',
    zj: dayAheadSource.value === 'zhejiang' || dayAheadSource.value === 'mixed',
    none: !dayAheadSource.value || dayAheadSource.value === 'none',
}))

const tips = computed(() => {
    const list: string[] = []
    if (dayAheadSource.value === 'none') {
        list.push('标的前日价格缺失：江苏库与浙江库都没有该日数据，可先上传日前电价后再查询')
    } else if (dayAheadHours.value > 0 && dayAheadHours.value < 24) {
        list.push(`日前价格仅覆盖 ${dayAheadHours.value}/24 小时，缺口时段价差为空`)
    }
    const missing = [
        !marketDates.d2 ? dateD2.value : '',
        !marketDates.d3 ? dateD3.value : '',
        !marketDates.d4 ? dateD4.value : '',
    ].filter(Boolean)
    if (missing.length) {
        list.push(`市场滚撮缺少 ${missing.join('、')} 的数据，对应电量列按 0 计算`)
    }
    return list
})

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

/**
 * 查询分析
 * @param refresh true 时要求后端跳过读取缓存，确保拿到刚上传的数据
 */
async function loadData(refresh = true) {
    if (!params.date) return alert('请选择标的日')
    loading.value = true
    try {
        const res: any = await request({
            url: '/rolling/analysis',
            method: 'get',
            // _t：绕过浏览器 GET 缓存；refresh：让后端跳过服务端缓存
            params: refresh
                ? { targetDate: params.date, refresh: 1, _t: Date.now() }
                : { targetDate: params.date },
        })
        tableData.value = res.rows || []
        apiDates.d2 = res.d2Date || ''
        apiDates.d3 = res.d3Date || ''
        apiDates.d4 = res.d4Date || ''
        dayAheadSource.value = res.dayAheadSource || 'none'
        dayAheadHours.value = res.dayAheadHours || 0
        marketDates.d2 = !!res.marketDates?.d2
        marketDates.d3 = !!res.marketDates?.d3
        marketDates.d4 = !!res.marketDates?.d4
    } catch (err: any) {
        alert('查询失败：' + (err.message || '后端服务异常'))
        tableData.value = []
        dayAheadSource.value = ''
        dayAheadHours.value = 0
        marketDates.d2 = marketDates.d3 = marketDates.d4 = false
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
        // 上传成功后自动刷新一次（后端已清理缓存，此处强制重新取数）
        if (params.date) {
            await loadData(true)
        }
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

/* ===== 来源标签 ===== */
.source-tag {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1;
    white-space: nowrap;
}

.source-tag.js {
    background: #ecf5ff;
    color: #2d6cdf;
}

.source-tag.zj {
    background: #fdf6ec;
    color: #e6a23c;
}

.source-tag.none {
    background: #f4f4f5;
    color: #909399;
}

/* ===== 数据提示 ===== */
.tips {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 10px;
    padding: 10px 16px;
    background: #fdf6ec;
    border-left: 3px solid #e6a23c;
    border-radius: 4px;
    font-size: 12px;
    color: #b88230;
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