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
                <input type="date" v-model="query.date" class="input" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '查询中...' : '🔍 查询数据' }}
            </button>
        </div>

        <!-- 表格区 -->
        <div class="result-card">
            <div v-if="!tableData.length" class="empty-tip">请选择电厂和日期，点击查询。</div>
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
                        <tr v-for="(row, idx) in tableData" :key="idx">
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
import { ref, reactive, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { listPlantNodes, type PlantNode } from '@/api/modules/nodes'

const nodeOptions = ref<PlantNode[]>([])
const loading = ref(false)
const tableData = ref<any[]>([])

const query = reactive({ node: '', date: '' })

onMounted(async () => {
    nodeOptions.value = await listPlantNodes()
})

// 后续替换为真实接口
function loadData() {
    if (!query.node || !query.date) return alert('请选择电厂和日期')
    loading.value = true
    setTimeout(() => {
        // 模拟后台计算好的差额
        tableData.value = [
            { opDate: query.date, timeType: '00:00-01:00', direction: '买方', qty: 4.0, price: 530.0, tradeQty: -4.0, clearPrice: 500.0, priceDiff: 30.0, finalDiff: -120.0 },
            { opDate: query.date, timeType: '01:00-02:00', direction: '卖方', qty: 2.0, price: 480.0, tradeQty: 2.0, clearPrice: 500.0, priceDiff: -20.0, finalDiff: -40.0 },
            { opDate: query.date, timeType: '02:00-03:00', direction: '买方', qty: 3.0, price: 460.0, tradeQty: -3.0, clearPrice: 450.0, priceDiff: 10.0, finalDiff: -30.0 },
            { opDate: query.date, timeType: '03:00-04:00', direction: '卖方', qty: 5.0, price: 520.0, tradeQty: 5.0, clearPrice: 450.0, priceDiff: 70.0, finalDiff: 350.0 },
        ]
        loading.value = false
    }, 500)
}

function getDiffStyle(val: number) {
    if (val === 0) return { backgroundColor: '#fff' }
    const maxAbs = Math.max(...tableData.value.map(d => Math.abs(d.finalDiff)), 1)
    const intensity = Math.min(Math.abs(val) / maxAbs, 1)

    if (val > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.7})`, color: intensity > 0.6 ? '#fff' : '#303133' }
    }
}
</script>

<style scoped>
/* 样式保持统一 */
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

.result-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin-top: 16px;
    max-height: calc(100vh - 220px);
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

.data-table td {
    font-variant-numeric: tabular-nums;
}

.empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
}
</style>