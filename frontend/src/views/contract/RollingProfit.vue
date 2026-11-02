<template>
    <PageContainer title="滚撮收益模拟">
        <!-- 顶部筛选 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>电厂节点</label>
                <select v-model="query.node" class="input">
                    <option value="" disabled>请选择电厂</option>
                    <option v-for="n in nodeOptions" :key="n.id" :value="n.name">{{ n.name }}</option>
                </select>
            </div>

            <div class="filter-item">
                <label>操作日期</label>
                <input type="date" v-model="query.dateStart" class="input" />
                <span class="separator">至</span>
                <input type="date" v-model="query.dateEnd" class="input" />
            </div>

            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '查询中...' : '🔍 查询数据' }}
            </button>
        </div>

        <!-- 收益统计卡片 -->
        <div v-if="hasSearched" class="stat-cards">
            <div class="stat-card total">
                <div class="stat-label">总收益 (元)</div>
                <div class="stat-value">{{ totalProfit.toFixed(2) }}</div>
            </div>
            <div class="stat-card buy">
                <div class="stat-label">买入收益 (元)</div>
                <div class="stat-value">{{ buyProfit.toFixed(2) }}</div>
            </div>
            <div class="stat-card sell">
                <div class="stat-label">卖出收益 (元)</div>
                <div class="stat-value">{{ sellProfit.toFixed(2) }}</div>
            </div>
        </div>

        <!-- 表格区 -->
        <div class="result-card">
            <div v-if="!hasSearched" class="empty-tip">请选择电厂节点和日期范围，点击查询。</div>
            <div v-else-if="!filteredData.length" class="empty-tip">当前条件范围内暂无数据。</div>
            <div v-else class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>操作日期</th>
                            <th>分时段类型</th>
                            <th>买卖方向</th>
                            <th>成交电量</th>
                            <th>成交均价</th>
                            <th>交易电量</th>
                            <th>负荷出清侧电价</th>
                            <th>电价差</th>
                            <th>差额 (元)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in filteredData" :key="idx">
                            <td>{{ row.opDate }}</td>
                            <td>{{ row.timeType }}</td>
                            <td>{{ row.direction }}</td>
                            <td>{{ row.qty.toFixed(3) }}</td>
                            <td>{{ row.price.toFixed(3) }}</td>
                            <td>{{ row.tradeQty.toFixed(3) }}</td>
                            <td>{{ row.clearPrice.toFixed(3) }}</td>
                            <td>{{ row.priceDiff.toFixed(3) }}</td>
                            <td :style="getDiffStyle(row.finalDiff)">{{ row.finalDiff.toFixed(2) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { listPlantNodes, type PlantNode } from '@/api/modules/nodes'
import { expandDateRange } from '@/utils/dateRange'

const nodeOptions = ref<PlantNode[]>([])
const loading = ref(false)
const hasSearched = ref(false) // 标记是否已经点击过查询
const rawData = ref<any[]>([])

const query = reactive({
    node: '',
    dateStart: '',
    dateEnd: ''
})

// 初始化日期范围（默认最近 14 天）
function initDateRange() {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 13)
    const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    query.dateEnd = fmt(end)
    query.dateStart = fmt(start)
}

onMounted(async () => {
    initDateRange()
    try {
        nodeOptions.value = await listPlantNodes()
    } catch { nodeOptions.value = [] }
})

// 前端过滤数据
const filteredData = computed(() => {
    if (!rawData.value.length) return []
    if (!query.dateStart || !query.dateEnd) return rawData.value
    const dates = expandDateRange(query.dateStart, query.dateEnd)
    return rawData.value.filter(row => dates.includes(row.opDate))
})

// 收益计算
const totalProfit = computed(() => filteredData.value.reduce((sum, r) => sum + (r.finalDiff || 0), 0))
const buyProfit = computed(() => filteredData.value.filter(r => r.direction === '买方').reduce((sum, r) => sum + (r.finalDiff || 0), 0))
const sellProfit = computed(() => filteredData.value.filter(r => r.direction === '卖方').reduce((sum, r) => sum + (r.finalDiff || 0), 0))

// 获取真实数据
async function loadData() {
    if (!query.node) return alert('请选择电厂节点')
    if (!query.dateStart || !query.dateEnd) return alert('请选择完整的日期范围')

    loading.value = true
    hasSearched.value = true

    // 此处保留模拟逻辑，后续替换为接口请求
    setTimeout(() => {
        const dates = expandDateRange(query.dateStart, query.dateEnd)
        interface MockRow {
            opDate: string
            timeType: string
            direction: string
            qty: number
            price: number
            tradeQty: number
            clearPrice: number
            priceDiff: number
            finalDiff: number
        }
        let mockRows: MockRow[] = []
        dates.forEach((d) => {
            mockRows.push(
                { opDate: d, timeType: '00:00-01:00', direction: '买方', qty: 4.0, price: 530.0, tradeQty: -4.0, clearPrice: 500.0, priceDiff: 30.0, finalDiff: -120.0 },
                { opDate: d, timeType: '01:00-02:00', direction: '卖方', qty: 2.0, price: 480.0, tradeQty: 2.0, clearPrice: 500.0, priceDiff: -20.0, finalDiff: -40.0 },
                { opDate: d, timeType: '02:00-03:00', direction: '买方', qty: 3.0, price: 460.0, tradeQty: -3.0, clearPrice: 450.0, priceDiff: 10.0, finalDiff: -30.0 },
                { opDate: d, timeType: '03:00-04:00', direction: '卖方', qty: 5.0, price: 520.0, tradeQty: 5.0, clearPrice: 450.0, priceDiff: 70.0, finalDiff: 350.0 }
            )
        })
        rawData.value = mockRows
        loading.value = false
    }, 300)
}

// 色阶
function getDiffStyle(val: number) {
    if (val === 0) return { backgroundColor: '#fff' }
    const maxAbs = Math.max(...filteredData.value.map(d => Math.abs(d.finalDiff)), 1)
    const intensity = Math.min(Math.abs(val) / maxAbs, 1)
    if (val > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: 'bold' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: 'bold' }
    }
}
</script>

<style scoped>
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
    font-size: 13px;
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

/* 统计卡片 */
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