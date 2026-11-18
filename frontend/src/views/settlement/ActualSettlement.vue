<template>
    <PageContainer title="实际结算单更新">
        <!-- 顶部筛选与上传 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>电厂节点</label>
                <SearchableSelect v-model="query.node" :options="nodeOptions" style="width: 200px;" />
            </div>

            <div class="filter-item">
                <label>月份</label>
                <el-date-picker v-model="query.month" type="month" placeholder="选择月份" format="YYYY-MM"
                    value-format="YYYY-MM" :clearable="false" style="width: 130px;" />
            </div>

            <div class="filter-item">
                <label>固定差价补偿</label>
                <input v-model.number="compensation" type="number" step="0.001" class="input" style="width: 110px;"
                    placeholder="元/MWh" />
            </div>

            <!-- 上传区域 -->
            <div class="form-group" style="flex: 1; min-width: 250px; margin-bottom: 0;">
                <label class="upload-area" :class="{ 'has-file': selectedFiles.length > 0, 'is-dragover': isDragOver }"
                    @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false"
                    @drop.prevent="handleDrop" @click="triggerFileSelect">
                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input" ref="fileInputRef"
                        @change="handleFileChange" />
                    <div class="upload-content">
                        <span class="icon">📄</span>
                        <span class="text">
                            {{ selectedFiles.length > 0 ? `已选择 ${selectedFiles.length} 个文件，点击重新上传` : '点击或拖拽上传实际结算单' }}
                        </span>
                    </div>
                </label>
            </div>

            <button class="btn primary" :disabled="!query.node || uploading" @click="submitUpload">
                {{ uploading ? '上传解析中...' : '上传并入库' }}
            </button>
            <button class="btn ghost" :disabled="!baseRecords.length" @click="exportData">导出 Excel</button>
        </div>

        <!-- 数据展示区 -->
        <div class="table-card">
            <!-- 子标签页 -->
            <div class="table-tabs">
                <button :class="['table-tab-btn', { active: activeTab === 'overview' }]"
                    @click="activeTab = 'overview'">概览</button>
                <button :class="['table-tab-btn', { active: activeTab === 'detail' }]"
                    @click="activeTab = 'detail'">详细</button>
            </div>

            <!-- 概览页 -->
            <div v-if="activeTab === 'overview'" class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>结算电量</th>
                            <th>结算均价</th>
                            <th>结算电费</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in fullMonthRows" :key="idx">
                            <td>{{ row.date }}</td>
                            <template v-if="!row.isEmpty">
                                <td>{{ format3(row.online_qty) }}</td>
                                <td>{{ format3(row.settlementPrice) }}</td>
                                <td>{{ format2(row.total_fee) }}</td>
                            </template>
                            <template v-else>
                                <td>-</td>
                                <td>-</td>
                                <td>-</td>
                            </template>
                        </tr>
                    </tbody>
                    <tfoot v-if="enrichedRecords.length">
                        <tr class="summary-row">
                            <td>合计</td>
                            <td>{{ format3(summary.online_qty) }}</td>
                            <td>{{ format3(summary.settlementPrice) }}</td>
                            <td>{{ format2(summary.total_fee) }}</td>
                        </tr>
                        <tr class="summary-row">
                            <td>固定差价补偿</td>
                            <td>{{ format3(compensationData.qty) }}</td>
                            <td>{{ format3(compensationData.price) }}</td>
                            <td>{{ format2(compensationData.fee) }}</td>
                        </tr>
                        <tr class="summary-row highlight-row">
                            <td>含补贴均价</td>
                            <td>{{ format3(withSubsidy.qty) }}</td>
                            <td>{{ format3(withSubsidy.price) }}</td>
                            <td>{{ format2(withSubsidy.fee) }}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <!-- 详细页 -->
            <div v-if="activeTab === 'detail'" class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>实际电量</th>
                            <th>日前电量</th>
                            <th>实时电量</th>
                            <th>日前结算均价</th>
                            <th>日前结算费用</th>
                            <th>实时结算均价</th>
                            <th>实时结算费用</th>
                            <th>现货收益结算费用</th>
                            <th>现货相对日前曲线盈亏</th>
                            <th>现货累计盈亏</th>
                            <th>年度集中合约电量</th>
                            <th>年度集中合约电价</th>
                            <th>年度集中合约费用</th>
                            <th>月度集中合约电量</th>
                            <th>月度集中合约电价</th>
                            <th>月度集中合约费用</th>
                            <th>日内滚撮电量</th>
                            <th>日内滚撮电价</th>
                            <th>日内滚撮费用</th>
                            <th>省间滚撮电量</th>
                            <th>省间滚撮电价</th>
                            <th>省间滚撮费用</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in fullMonthRows" :key="idx">
                            <td>{{ row.date }}</td>
                            <template v-if="!row.isEmpty">
                                <td>{{ format3(row.online_qty) }}</td>
                                <td>{{ format3(row.da_qty) }}</td>
                                <td>{{ format3(row.rt_qty) }}</td>
                                <td>{{ format3(row.da_price) }}</td>
                                <td>{{ format2(row.da_fee) }}</td>
                                <td>{{ format3(row.rt_price) }}</td>
                                <td>{{ format2(row.rt_fee) }}</td>
                                <td>{{ format2(row.spotFee) }}</td>
                                <td :style="getColorStyle(row.spotProfit, row.cumulativeProfit, 'profit')">{{
                                    format2(row.spotProfit) }}</td>
                                <td :style="getColorStyle(row.spotProfit, row.cumulativeProfit, 'cumulative')">{{
                                    format2(row.cumulativeProfit) }}</td>
                                <td>{{ format3(row.year_qty) }}</td>
                                <td>{{ format3(row.year_price) }}</td>
                                <td>{{ format2(row.year_fee) }}</td>
                                <td>{{ format3(row.month_qty) }}</td>
                                <td>{{ format3(row.month_price) }}</td>
                                <td>{{ format2(row.month_fee) }}</td>
                                <td>{{ format3(row.intraday_qty) }}</td>
                                <td>{{ format3(row.intraday_price) }}</td>
                                <td>{{ format2(row.intraday_fee) }}</td>
                                <td>{{ format3(row.cs_qty) }}</td>
                                <td>{{ format3(row.cs_price) }}</td>
                                <td>{{ format2(row.cs_fee) }}</td>
                            </template>
                            <template v-else>
                                <td v-for="i in 22" :key="i">-</td>
                            </template>
                        </tr>
                    </tbody>
                    <tfoot v-if="enrichedRecords.length">
                        <tr class="summary-row">
                            <td>汇总</td>
                            <td>{{ format3(summary.online_qty) }}</td>
                            <td>{{ format3(summary.da_qty) }}</td>
                            <td>{{ format3(summary.rt_qty) }}</td>
                            <td>{{ format3(summary.da_price) }}</td>
                            <td>{{ format2(summary.da_fee) }}</td>
                            <td>{{ format3(summary.rt_price) }}</td>
                            <td>{{ format2(summary.rt_fee) }}</td>
                            <td>{{ format2(summary.spotFee) }}</td>
                            <td>{{ format2(summary.spotProfit) }}</td>
                            <td>{{ format2(summary.cumulativeProfit) }}</td>
                            <td>{{ format3(summary.year_qty) }}</td>
                            <td>{{ format3(summary.year_price) }}</td>
                            <td>{{ format2(summary.year_fee) }}</td>
                            <td>{{ format3(summary.month_qty) }}</td>
                            <td>{{ format3(summary.month_price) }}</td>
                            <td>{{ format2(summary.month_fee) }}</td>
                            <td>{{ format3(summary.intraday_qty) }}</td>
                            <td>{{ format3(summary.intraday_price) }}</td>
                            <td>{{ format2(summary.intraday_fee) }}</td>
                            <td>{{ format3(summary.cs_qty) }}</td>
                            <td>{{ format3(summary.cs_price) }}</td>
                            <td>{{ format2(summary.cs_fee) }}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import { listPlantNodes } from '@/api/modules/nodes'
import { request } from '@/api/request'
import { apiUrl } from '@/utils/apiBase'
/* ==================== 状态 ==================== */
const nodeOptions = ref<string[]>([])
const query = reactive({
    node: '',
    month: new Date().toISOString().slice(0, 7),
})
const compensation = ref(153.515) // 默认补偿值
const baseRecords = ref<any[]>([])
const activeTab = ref<'overview' | 'detail'>('overview')

/* ==================== 文件上传 ==================== */
const selectedFiles = ref<File[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
const uploading = ref(false)

function triggerFileSelect() { fileInputRef.value?.click() }
function handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement
    if (input.files?.length) selectedFiles.value = Array.from(input.files)
    input.value = ''
}
function handleDrop(e: DragEvent) {
    isDragOver.value = false
    if (e.dataTransfer?.files?.length) selectedFiles.value = Array.from(e.dataTransfer.files)
}

async function submitUpload() {
    if (!query.node || !selectedFiles.value.length) return
    uploading.value = true
    const fd = new FormData()
    fd.append('node_name', query.node)
    for (const f of selectedFiles.value) fd.append('files', f)

    try {
        await request({
            url: '/settlement/actual/upload',
            method: 'post',
            data: fd,
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        alert('上传并入库成功')
        selectedFiles.value = []
        await loadRecords()
    } catch (e) {
        alert('上传失败：' + (e as Error).message)
    } finally {
        uploading.value = false
    }
}

/* ==================== 数据加载 ==================== */
async function loadRecords() {
    if (!query.node) {
        baseRecords.value = []
        return
    }
    try {
        const res = await request<any[]>({
            url: '/settlement/actual/records',
            method: 'get',
            params: { node_name: query.node }
        })
        baseRecords.value = res || []
    } catch {
        baseRecords.value = []
    }
}

function loadNodes() {
    listPlantNodes().then(list => {
        nodeOptions.value = list.map(n => n.name)
        if (!query.node && nodeOptions.value.length) query.node = nodeOptions.value[0]
    }).catch(() => undefined)
}

watch(() => query.node, loadRecords)
onMounted(() => {
    loadNodes()
    loadRecords()
})

/* ==================== 衍生数据计算 ==================== */
const enrichedRecords = computed(() => {
    let list = baseRecords.value
    if (query.month) {
        list = list.filter(r => r.date.startsWith(query.month))
    }
    list = [...list].sort((a, b) => a.date.localeCompare(b.date))

    let cumulative = 0
    return list.map(r => {
        const online_qty = Number(r.online_qty) || 0
        const total_fee = Number(r.total_fee) || 0
        const da_qty = Number(r.da_qty) || 0
        const da_price = Number(r.da_price) || 0
        const da_fee = Number(r.da_fee) || 0
        const rt_qty = Number(r.rt_qty) || 0
        const rt_price = Number(r.rt_price) || 0
        const rt_fee = Number(r.rt_fee) || 0

        const settlementPrice = online_qty !== 0 ? total_fee / online_qty : 0
        const spotFee = da_fee + rt_fee
        const spotProfit = rt_qty * (rt_price - da_price)
        cumulative += spotProfit

        return {
            ...r,
            online_qty, total_fee,
            da_qty, da_price, da_fee,
            rt_qty, rt_price, rt_fee,
            year_qty: Number(r.year_qty) || 0,
            year_price: Number(r.year_price) || 0,
            year_fee: Number(r.year_fee) || 0,
            month_qty: Number(r.month_qty) || 0,
            month_price: Number(r.month_price) || 0,
            month_fee: Number(r.month_fee) || 0,
            intraday_qty: Number(r.intraday_qty) || 0,
            intraday_price: Number(r.intraday_price) || 0,
            intraday_fee: Number(r.intraday_fee) || 0,
            cs_qty: Number(r.cs_qty) || 0,
            cs_price: Number(r.cs_price) || 0,
            cs_fee: Number(r.cs_fee) || 0,
            settlementPrice,
            spotFee,
            spotProfit,
            cumulativeProfit: cumulative,
        }
    })
})

/* ==================== 当月完整日期渲染 ==================== */
const fullMonthRows = computed(() => {
    const list = enrichedRecords.value
    if (!query.month) return list

    const [yearStr, monthStr] = query.month.split('-')
    const year = parseInt(yearStr)
    const month = parseInt(monthStr)
    const daysInMonth = new Date(year, month, 0).getDate()

    const map = new Map(list.map(r => [r.date, r]))
    const rows = []

    for (let d = 1; d <= daysInMonth; d++) {
        const dayStr = `${year}-${monthStr}-${String(d).padStart(2, '0')}`
        if (map.has(dayStr)) {
            rows.push(map.get(dayStr))
        } else {
            rows.push({ date: dayStr, isEmpty: true })
        }
    }
    return rows
})

/* ==================== 汇总行计算 ==================== */
const summary = computed(() => {
    const list = enrichedRecords.value
    if (!list.length) {
        return {
            online_qty: 0, total_fee: 0, settlementPrice: 0,
            da_qty: 0, da_price: 0, da_fee: 0, rt_qty: 0, rt_price: 0, rt_fee: 0,
            spotFee: 0, spotProfit: 0, cumulativeProfit: 0,
            year_qty: 0, year_price: 0, year_fee: 0,
            month_qty: 0, month_price: 0, month_fee: 0,
            intraday_qty: 0, intraday_price: 0, intraday_fee: 0,
            cs_qty: 0, cs_price: 0, cs_fee: 0,
        }
    }
    const count = list.length
    const sum = (key: string) => list.reduce((a, b) => a + (b[key] || 0), 0)
    const avg = (key: string) => count ? sum(key) / count : 0

    return {
        online_qty: sum('online_qty'),
        total_fee: sum('total_fee'),
        settlementPrice: sum('online_qty') !== 0 ? sum('total_fee') / sum('online_qty') : 0,
        da_qty: sum('da_qty'), da_price: avg('da_price'), da_fee: sum('da_fee'),
        rt_qty: sum('rt_qty'), rt_price: avg('rt_price'), rt_fee: sum('rt_fee'),
        spotFee: sum('spotFee'), spotProfit: sum('spotProfit'),
        cumulativeProfit: list[count - 1].cumulativeProfit,
        year_qty: sum('year_qty'), year_price: avg('year_price'), year_fee: sum('year_fee'),
        month_qty: sum('month_qty'), month_price: avg('month_price'), month_fee: sum('month_fee'),
        intraday_qty: sum('intraday_qty'), intraday_price: avg('intraday_price'), intraday_fee: sum('intraday_fee'),
        cs_qty: sum('cs_qty'), cs_price: avg('cs_price'), cs_fee: sum('cs_fee'),
    }
})

/* ==================== 固定差价补偿 & 含补贴均价计算 ==================== */
const compensationData = computed(() => {
    const totalQty = summary.value.online_qty
    const price = compensation.value
    const qty = totalQty * 0.45
    return {
        qty,
        price,
        fee: qty * price
    }
})

const withSubsidy = computed(() => {
    const totalQty = summary.value.online_qty
    const totalFee = summary.value.total_fee
    const compFee = compensationData.value.fee

    const finalQty = totalQty
    const finalFee = totalFee + compFee
    const finalPrice = finalQty !== 0 ? finalFee / finalQty : 0

    return {
        qty: finalQty,
        fee: finalFee,
        price: finalPrice
    }
})

/* ==================== 导出 ==================== */
function exportData() {
    if (!query.node) return
    const params = new URLSearchParams({
        node_name: query.node,
        month: query.month || '',
        compensation: String(compensation.value),
    })
    // ⭐ 替换为 apiUrl，防止生产环境或配置了 baseURL 时请求错误
    window.open(apiUrl(`/settlement/actual/export?${params.toString()}`), '_blank')
}

/* ==================== 工具函数 ==================== */
function format2(v: any) {
    if (v == null || isNaN(v)) return '-'
    return Number(v).toFixed(2)
}
function format3(v: any) {
    if (v == null || isNaN(v)) return '-'
    return Number(v).toFixed(3)
}

function getColorStyle(val: number, cumulative: number, mode: 'profit' | 'cumulative') {
    if (val == null || val === 0) return {}
    const list = enrichedRecords.value
    const maxAbs = mode === 'profit'
        ? Math.max(...list.map(r => Math.abs(r.spotProfit)), 1)
        : Math.max(...list.map(r => Math.abs(r.cumulativeProfit)), 1)
    const target = mode === 'profit' ? val : cumulative
    const intensity = Math.min(Math.abs(target) / maxAbs, 1)

    if (target > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: '500' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: '500' }
    }
}
</script>

<style scoped>
/* ===== 全局容器高度限制，防止外层滚动 ===== */
:deep(.page-body) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 0 !important;
    /* 如果外层 PageContainer 有 padding，将其压缩 */
}

/* ===== 筛选栏：大幅压缩高度 ===== */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #fff;
    padding: 8px 12px;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex-wrap: wrap;
    flex-shrink: 0;
}

.filter-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.filter-item label {
    font-size: 12px;
    color: #606266;
    white-space: nowrap;
}

.input {
    height: 28px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    outline: none;
    font-size: 12px;
}

.input:focus {
    border-color: #2d6cdf;
}

/* ===== 上传区域 ===== */
.form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.upload-area {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 28px;
    padding: 0 12px;
    border: 1px dashed #dcdfe6;
    border-radius: 4px;
    background: #fafbfc;
    cursor: pointer;
    transition: all 0.2s;
}

.upload-area:hover,
.upload-area.is-dragover {
    border-color: #2d6cdf;
    background: #f0f5ff;
}

.upload-area.has-file {
    border-color: #67c23a;
    background: #f0f9eb;
}

.upload-content {
    display: flex;
    align-items: center;
    gap: 6px;
}

.upload-content .icon {
    font-size: 14px;
}

.upload-content .text {
    font-size: 12px;
    color: #606266;
}

.hidden-input {
    display: none;
}

/* ===== 按钮 ===== */
.btn {
    height: 28px;
    padding: 0 12px;
    border-radius: 4px;
    cursor: pointer;
    border: none;
    font-size: 12px;
}

.btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.btn.primary:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

/* ===== 表格卡片 ===== */
.table-card {
    background: #fff;
    border-radius: 6px;
    padding: 8px 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 8px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

/* 标签页 */
.table-tabs {
    display: flex;
    border-bottom: 1px solid #ebeef5;
    margin-bottom: 6px;
    flex-shrink: 0;
}

.table-tab-btn {
    padding: 6px 16px;
    border: none;
    background: transparent;
    font-size: 12px;
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

/* 表格区域，自动填充剩余高度 */
.table-wrapper {
    flex: 1;
    min-height: 0;
    overflow: auto;
    /* 内容较少时自动隐藏滚动条，超出时内部滚动 */
    border: 1px solid #ebeef5;
    border-radius: 4px;
    position: relative;
}

/* ===== 大幅压缩行高和字体，确保一屏显示 ===== */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    text-align: right;
}

.data-table th,
.data-table td {
    padding: 2px 4px;
    /* 关键：极小行高 padding */
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    background: #fff;
    line-height: 1.2;
    /* 紧凑行间距 */
}

.data-table th {
    background: #f5f7fa;
    position: sticky;
    top: 0;
    z-index: 2;
    text-align: center;
    color: #303133;
    padding: 4px;
    /* 表头微缩 */
}

.data-table tbody tr:hover td {
    background-color: #f9fafc;
}

/* 汇总行固定底部 */
.summary-row td {
    background: #f0f9eb !important;
    color: #67c23a;
    font-weight: bold;
    border-top: 1px solid #dcdfe6;
    position: sticky;
    bottom: 0;
    z-index: 2;
    padding: 3px 4px;
}

.highlight-row td {
    background: #ecf5ff !important;
    color: #2d6cdf !important;
    border-bottom: 1px solid #dcdfe6;
}

/* 对齐 Element Plus 月份选择器高度 */
:deep(.el-date-editor.el-input) {
    height: 28px;
    width: 130px !important;
}

:deep(.el-date-editor .el-input__wrapper) {
    box-shadow: 0 0 0 1px #dcdfe6 inset;
    padding: 0 8px;
}

:deep(.el-date-editor .el-input__inner) {
    font-size: 12px;
    color: #303133;
}
</style>