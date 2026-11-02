<template>
    <PageContainer title="滚撮分析">
        <!-- 控制栏 -->
        <div class="control-bar">
            <div class="form-group">
                <label>标的日 (D日)</label>
                <input type="date" v-model="params.date" class="input" />
            </div>
            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '计算中...' : '🔍 查询分析' }}
            </button>
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

                            <!-- D-2 -->
                            <td class="group-start">{{ format(row.d2Qty) }}</td>
                            <td>{{ format(row.d2Price) }}</td>
                            <td :style="diffStyle(row.d2Diff)">{{ format(row.d2Diff) }}</td>

                            <!-- D-3 -->
                            <td class="group-start">{{ format(row.d3Qty) }}</td>
                            <td>{{ format(row.d3Price) }}</td>
                            <td :style="diffStyle(row.d3Diff)">{{ format(row.d3Diff) }}</td>

                            <!-- D-4 -->
                            <td class="group-start">{{ format(row.d4Qty) }}</td>
                            <td>{{ format(row.d4Price) }}</td>
                            <td :style="diffStyle(row.d4Diff)">{{ format(row.d4Diff) }}</td>

                            <!-- 市场合计 -->
                            <td class="group-start">{{ format(row.marketQty) }}</td>
                            <td>{{ format(row.marketPrice) }}</td>
                            <td :style="diffStyle(row.marketDiff)">{{ format(row.marketDiff) }}</td>
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

const loading = ref(false)
const params = reactive({
    date: '2026-10-30', // 标的日
})

// 根据标的日计算具体日期
function getDateOffset(baseDate: string, offsetDays: number): string {
    if (!baseDate) return ''
    const d = new Date(baseDate)
    d.setDate(d.getDate() - offsetDays)
    return d.toISOString().slice(0, 10)
}

const dateD2 = computed(() => getDateOffset(params.date, 2))
const dateD3 = computed(() => getDateOffset(params.date, 3))
const dateD4 = computed(() => getDateOffset(params.date, 4))

// 存储表格数据
const tableData = ref<any[]>([])

// 时间标签
const SLOT_LABELS = Array.from({ length: 48 }).map((_, i) => {
    const h = Math.floor(i / 2)
    const m = (i % 2) * 30
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
})

// 格式化显示
function format(v: number | null | undefined) {
    if (v == null || isNaN(v)) return '-'
    return v.toFixed(3)
}

// 样式：日前价格（基准350）
function priceStyle(v: number) {
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

// 样式：价差（基准0）
function diffStyle(v: number | null) {
    if (v == null || v === 0) return {}
    if (v > 0) {
        const intensity = Math.min(Math.abs(v) / 100, 1)
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: '#303133' }
    } else {
        const intensity = Math.min(Math.abs(v) / 100, 1)
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: '#303133' }
    }
}

// 计算逻辑
async function loadData() {
    if (!params.date) return alert('请选择标的日')
    loading.value = true

    setTimeout(() => {
        // 模拟当日日前价格(48点)
        const dayAheadPrices = Array.from({ length: 48 }).map(() => 300 + Math.random() * 200)

        // 模拟 D-2、D-3、D-4 的成交数据（24点）
        const tradesD2 = Array.from({ length: 24 }).map(() => ({ qty: Math.random() * 100, price: 400 + Math.random() * 100 }))
        const tradesD3 = Array.from({ length: 24 }).map(() => ({ qty: Math.random() * 80, price: 410 + Math.random() * 100 }))
        const tradesD4 = Array.from({ length: 24 }).map(() => ({ qty: Math.random() * 120, price: 390 + Math.random() * 100 }))

        let rows = []

        for (let i = 0; i < 48; i++) {
            const hourIdx = Math.floor(i / 2) // 24点数据索引
            const daPrice = dayAheadPrices[i]

            // D-2
            const d2Qty = tradesD2[hourIdx].qty
            const d2Price = tradesD2[hourIdx].price
            const d2Diff = d2Price - daPrice

            // D-3
            const d3Qty = tradesD3[hourIdx].qty
            const d3Price = tradesD3[hourIdx].price
            const d3Diff = d3Price - daPrice

            // D-4
            const d4Qty = tradesD4[hourIdx].qty
            const d4Price = tradesD4[hourIdx].price
            const d4Diff = d4Price - daPrice

            // 市场合计计算
            const marketQty = d2Qty + d3Qty + d4Qty
            const marketPrice = marketQty > 0
                ? (d2Qty * d2Price + d3Qty * d3Price + d4Qty * d4Price) / marketQty
                : 0
            const marketDiff = marketQty > 0 ? marketPrice - daPrice : 0

            rows.push({
                time: SLOT_LABELS[i],
                dayAheadPrice: daPrice,

                d2Qty, d2Price, d2Diff,
                d3Qty, d3Price, d3Diff,
                d4Qty, d4Price, d4Diff,

                marketQty, marketPrice, marketDiff
            })
        }

        tableData.value = rows
        loading.value = false
    }, 500)
}
// import { ref, reactive, computed } from 'vue'
// import PageContainer from '@/components/PageContainer.vue'
// import { request } from '@/api/request' // 引入你封装的 axios

// const loading = ref(false)
// const params = reactive({
//     date: '2026-10-30',
// })

// // 接收后端返回的日期
// const dateD2 = ref('D-2')
// const dateD3 = ref('D-3')
// const dateD4 = ref('D-4')

// const tableData = ref<any[]>([])

// const SLOT_LABELS = Array.from({ length: 48 }).map((_, i) => {
//     const h = Math.floor(i / 2)
//     const m = (i % 2) * 30
//     return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
// })

// function format(v: number | null | undefined) {
//     if (v == null || isNaN(v)) return '-'
//     return v.toFixed(3)
// }

// function priceStyle(v: number | null) {
//     if (v == null) return {}
//     const base = 350
//     if (v < base) {
//         const intensity = Math.min((base - v) / 200, 1)
//         return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: '#303133' }
//     } else {
//         const intensity = Math.min((v - base) / 200, 1)
//         return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: '#303133' }
//     }
// }

// function diffStyle(v: number | null) {
//     if (v == null || v === 0) return {}
//     if (v > 0) {
//         const intensity = Math.min(Math.abs(v) / 100, 1)
//         return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: '#303133' }
//     } else {
//         const intensity = Math.min(Math.abs(v) / 100, 1)
//         return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: '#303133' }
//     }
// }

// async function loadData() {
//     if (!params.date) return alert('请选择标的日')
//     loading.value = true

//     try {
//         // 请求真实接口
//         const res = await request({
//             url: '/rolling/analysis',
//             method: 'get',
//             params: { targetDate: params.date }
//         })

//         const data = (res as any).data || res

//         if (data && data.rows) {
//             tableData.value = data.rows
//             // 更新表头日期
//             dateD2.value = data.d2Date
//             dateD3.value = data.d3Date
//             dateD4.value = data.d4Date
//         }
//     } catch (err: any) {
//         alert('查询失败：' + (err.message || '后端服务异常'))
//     } finally {
//         loading.value = false
//     }
// }
</script>

<style scoped>
/* 控制栏 */
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
    margin-left: auto;
}

.btn-primary:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

/* 图例 */
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
}

.dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid #ebeef5;
}

.dot.price-low {
    background: rgba(103, 194, 58, 0.6);
}

.dot.price-high {
    background: rgba(245, 108, 108, 0.6);
}

.dot.spread-neg {
    background: rgba(103, 194, 58, 0.6);
}

.dot.spread-pos {
    background: rgba(245, 108, 108, 0.6);
}

.gap {
    width: 16px;
}

/* 表格 */
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
    padding: 8px 10px;
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
    font-variant-numeric: tabular-nums;
}

.data-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    position: sticky;
    top: 0;
    z-index: 2;
}

/* 区分分组 */
.group-start {
    border-left: 2px solid #dcdfe6;
}

.data-table th.group-start {
    border-left: 2px solid #c0c4cc;
}

/* 固定首列 */
.sticky-col {
    position: sticky;
    background: #f5f7fa;
    z-index: 1;
    border-right: 1px solid #dcdfe6;
}

.data-table th.sticky-col {
    z-index: 3;
}

.col-time {
    left: 0;
    width: 60px;
    font-weight: 500;
}
</style>