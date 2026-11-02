<template>
    <PageContainer title="长三角省间交易收益模拟">
        <div class="filter-bar">
            <div class="filter-item upload-item">
                <label>上传数据</label>
                <div class="upload-area" @click="triggerUpload" :class="{ 'has-file': selectedFile }">
                    <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="hidden-input"
                        @change="onFileChange" />
                    <div class="upload-content">
                        <span class="icon">📊</span>
                        <span class="text">
                            {{ selectedFile ? selectedFile.name : '点击选择文件 (含「成交数据」与「日前价格」Sheet)' }}
                        </span>
                    </div>
                </div>
            </div>

            <div class="action-btns">
                <button class="btn-primary" :disabled="!selectedFile || loading" @click="loadData">
                    {{ loading ? '处理中...' : '📤 上传解析' }}
                </button>
            </div>
        </div>

        <!-- 提取选项与收益卡片（只有数据加载后才展示） -->
        <div v-if="rawData.length" class="filter-bar" style="margin-top: 16px;">
            <div class="filter-item">
                <label>选择节点</label>
                <select v-model="selectedNode" class="input">
                    <option value="">全部节点</option>
                    <option v-for="n in nodeOptions" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>
            <div class="filter-item">
                <label>日期范围</label>
                <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                    @update:end="dateEnd = $event" />
            </div>
        </div>

        <div v-if="filteredData.length" class="stat-cards">
            <div class="stat-card total">
                <div class="stat-label">总收益 (元)</div>
                <div class="stat-value">{{ totalProfit.toFixed(2) }}</div>
            </div>
            <div class="stat-card buy">
                <div class="stat-label">买入收益 (购电)</div>
                <div class="stat-value">{{ buyProfit.toFixed(2) }}</div>
            </div>
            <div class="stat-card sell">
                <div class="stat-label">卖出收益 (售电)</div>
                <div class="stat-value">{{ sellProfit.toFixed(2) }}</div>
            </div>
        </div>

        <!-- 表格区 -->
        <div class="result-card">
            <div v-if="!filteredData.length && !rawData.length" class="empty-tip">请先上传文件解析数据。</div>
            <div v-else-if="!filteredData.length" class="empty-tip">当前筛选条件下无数据。</div>
            <div v-else class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>成交日期</th>
                            <th>交易单元</th>
                            <th>标的代码</th>
                            <th>成交类型</th>
                            <th>成交价</th>
                            <th>成交数量</th>
                            <th>日期</th>
                            <th>时间</th>
                            <th>日前价格</th>
                            <th>价差</th>
                            <th>价差金额 (元)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in filteredData" :key="idx">
                            <td>{{ row['成交日期'] || '-' }}</td>
                            <td>{{ row['交易单元'] }}</td>
                            <td>{{ row['标的代码'] }}</td>
                            <td>{{ row['成交类型'] }}</td>
                            <td>{{ row['成交价（元/MWh）']?.toFixed(3) }}</td>
                            <td>{{ row['成交数量（MW）']?.toFixed(3) }}</td>
                            <td>{{ row['日期'] }}</td>
                            <td>{{ row['时间'] }}</td>
                            <td>{{ row['日前价格（元/MWh）']?.toFixed(3) }}</td>
                            <td>{{ row['价差（元/MWh）']?.toFixed(3) }}</td>
                            <td :style="getDiffStyle(row['价差金额（元）'])">{{ row['价差金额（元）']?.toFixed(2) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import { expandDateRange } from '@/utils/dateRange'

const loading = ref(false)
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const rawData = ref<any[]>([])

// 过滤条件
const selectedNode = ref('')
const dateStart = ref('')
const dateEnd = ref('')

// 动态提取节点列表
const nodeOptions = computed(() => {
    const nodes = new Set(rawData.value.map(r => r['交易单元']))
    return Array.from(nodes).filter(Boolean)
})

function triggerUpload() {
    fileInputRef.value?.click()
}

function onFileChange(e: Event) {
    const target = e.target as HTMLInputElement
    if (target.files?.length) {
        selectedFile.value = target.files[0]
    } else {
        selectedFile.value = null
    }
}

async function loadData() {
    if (!selectedFile.value) return
    loading.value = true

    try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)

        const res = await fetch('/api/cross-province/upload', { method: 'POST', body: formData })
        const json = await res.json()

        if (json.code === 200 || json.code === 0) {
            rawData.value = json.data || []

            // 默认提取数据中的最小/最大日期作为筛选默认值
            if (rawData.value.length > 0) {
                const dates = rawData.value.map(r => r['日期']).filter(Boolean).sort()
                dateStart.value = dates[0]
                dateEnd.value = dates[dates.length - 1]
            }
        } else {
            alert('计算失败：' + (json.msg || '后端处理异常'))
        }
    } catch (err: any) {
        alert('网络请求失败，请检查后端是否崩溃')
    } finally {
        loading.value = false
    }
}

// 前端过滤数据
const filteredData = computed(() => {
    if (!rawData.value.length) return []
    const dates = expandDateRange(dateStart.value, dateEnd.value)

    return rawData.value.filter(row => {
        // 节点匹配
        const matchNode = !selectedNode.value || row['交易单元'] === selectedNode.value
        // 日期匹配（利用 expandDateRange 返回的日期数组）
        const matchDate = (!dateStart.value && !dateEnd.value) || dates.includes(row['日期'])
        return matchNode && matchDate
    })
})

// 收益计算
const totalProfit = computed(() => filteredData.value.reduce((sum, r) => sum + (r['价差金额（元）'] || 0), 0))
const buyProfit = computed(() => filteredData.value.filter(r => r['成交类型'] === '购电').reduce((sum, r) => sum + (r['价差金额（元）'] || 0), 0))
const sellProfit = computed(() => filteredData.value.filter(r => r['成交类型'] === '售电').reduce((sum, r) => sum + (r['价差金额（元）'] || 0), 0))

// 色阶
function getDiffStyle(val: number | null) {
    if (val == null || val === 0) return { backgroundColor: '#fff' }
    const maxAbs = Math.max(...filteredData.value.map(d => Math.abs(d['价差金额（元）'] || 0)), 1)
    const intensity = Math.min(Math.abs(val) / maxAbs, 1)
    if (val > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: 'bold' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: 'bold' }
    }
}
</script>

<style scoped>
/* 与滚撮页面完全一致的样式 */
.filter-bar {
    display: flex;
    align-items: flex-end;
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
    font-weight: 500;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    outline: none;
}

.upload-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    min-width: 400px;
}

.hidden-input {
    display: none;
}

.upload-area {
    border: 1px dashed #dcdfe6;
    border-radius: 6px;
    background: #fafbfc;
    padding: 8px 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    height: 38px;
    display: flex;
    align-items: center;
    width: 100%;
}

.upload-area:hover {
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
    gap: 8px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    width: 100%;
}

.upload-content .text {
    font-size: 13px;
    color: #606266;
}

.upload-area.has-file .text {
    color: #67c23a;
    font-weight: 500;
}

.action-btns {
    display: flex;
    gap: 12px;
}

.btn-primary {
    height: 38px;
    padding: 0 20px;
    background: #2d6cdf;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: 0.2s;
}

.btn-primary:hover:not(:disabled) {
    background: #2459b8;
}

.btn-primary:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.stat-cards {
    display: flex;
    gap: 16px;
    margin-top: 16px;
}

.stat-card {
    flex: 1;
    background: #fff;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    border-left: 4px solid #dcdfe6;
}

.stat-card.total {
    border-left-color: #2d6cdf;
}

.stat-card.buy {
    border-left-color: #67c23a;
}

.stat-card.sell {
    border-left-color: #e6a23c;
}

.stat-label {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #303133;
    font-variant-numeric: tabular-nums;
}

.result-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin-top: 16px;
    max-height: calc(100vh - 320px);
}

.table-wrap {
    flex: 1;
    overflow: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    text-align: center;
}

.data-table th,
.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #ebeef5;
    white-space: nowrap;
}

.data-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    position: sticky;
    top: 0;
    z-index: 2;
}

.empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    padding: 40px;
}
</style>