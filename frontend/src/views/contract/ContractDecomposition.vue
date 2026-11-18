<template>
    <PageContainer title="合约分解">
        <!-- ⭐ 新增：基础配置缺失警告 -->
        <div v-if="!hasCurve || !hasHoliday" class="config-warning">
            <div class="warn-icon">⚠️</div>
            <div class="warn-content">
                <p class="warn-title">检测到您尚未完成基础数据配置，可能无法正常生成分解！</p>
                <ul class="warn-list">
                    <li v-if="!hasCurve">缺失 <strong>典型曲线</strong> （<span class="req">必填</span>，否则无法计算）</li>
                    <li v-if="!hasHoliday">缺失 <strong>年度节假日</strong> （选填，未配置时将不识别法定节假日）</li>
                </ul>
            </div>
            <div class="warn-action">
                <router-link to="/contract/config" class="btn btn-primary btn-sm">
                    去配置 →
                </router-link>
            </div>
        </div>
        <!-- 顶部查询条件 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>年月</label>
                <input type="number" v-model="query.year" class="input" style="width: 100px;" />
                <span class="separator">-</span>
                <input type="number" v-model="query.month" class="input" style="width: 70px;" />
            </div>

            <div class="filter-item qty-item">
                <label>电量 (MWh)</label>
                <input type="number" v-model="query.qty.year" class="input" placeholder="年度" />
                <input type="number" v-model="query.qty.month" class="input" placeholder="月度" />
                <input type="number" v-model="query.qty.tenday1" class="input" placeholder="上旬" />
                <input type="number" v-model="query.qty.tenday2" class="input" placeholder="中旬" />
                <input type="number" v-model="query.qty.tenday3" class="input" placeholder="下旬" />
            </div>

            <button class="btn-primary" :disabled="loading" @click="loadData">
                {{ loading ? '计算中...' : '🔍 生成分解' }}
            </button>
            <button v-if="hasData" class="btn-outline" :disabled="exporting" @click="exportData">
                📥 导出所有
            </button>
        </div>

        <!-- 结果展示区 -->
        <div class="result-card">
            <div v-if="!hasData" class="empty-tip">请输入年月和电量，点击生成获取分解结果。</div>

            <template v-else>
                <div class="tabs-header">
                    <button :class="['tab-btn', { active: activeTab === 'year' }]"
                        @click="activeTab = 'year'">年度分解</button>
                    <button :class="['tab-btn', { active: activeTab === 'month' }]"
                        @click="activeTab = 'month'">月度分解</button>
                    <button :class="['tab-btn', { active: activeTab === 'tenday1' }]"
                        @click="activeTab = 'tenday1'">上旬分解</button>
                    <button :class="['tab-btn', { active: activeTab === 'tenday2' }]"
                        @click="activeTab = 'tenday2'">中旬分解</button>
                    <button :class="['tab-btn', { active: activeTab === 'tenday3' }]"
                        @click="activeTab = 'tenday3'">下旬分解</button>
                </div>

                <div class="table-wrap">
                    <table class="result-table">
                        <thead>
                            <tr>
                                <th class="sticky-col col-date">日期</th>
                                <th class="sticky-col col-type">类型</th>
                                <th class="sticky-col col-qty">日电量</th>
                                <th v-for="t in times" :key="t">{{ t }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(day, idx) in currentData" :key="idx"
                                :style="{ '--row-bg': getRowBg(day.day_type) }">
                                <td class="sticky-col col-date">{{ day.date }}</td>
                                <td class="sticky-col col-type">{{ day.day_type }}</td>
                                <td class="sticky-col col-qty">{{ Number(day.daily_qty).toFixed(3) }}</td>
                                <td v-for="(v, i) in day.points" :key="i">{{ Number(v).toFixed(3) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </template>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { request } from '@/api/request'
import { useRouter } from 'vue-router'
import { apiUrl } from '@/utils/apiBase'
const router = useRouter()
const loading = ref(false)
const exporting = ref(false)
const activeTab = ref<'year' | 'month' | 'tenday1' | 'tenday2' | 'tenday3'>('year')

const query = reactive({
    year: 2026,
    month: 10,
    qty: { year: null, month: null, tenday1: null, tenday2: null, tenday3: null }
})

const times = ref<string[]>([])
const resultData = ref<any>(null)
const hasData = computed(() => resultData.value !== null)
// 定义配置状态
const hasCurve = ref(true)
const hasHoliday = ref(true)
const currentData = computed(() => {
    if (!resultData.value) return []
    return resultData.value[activeTab.value] || []
})

interface ApiResponse<T = any> {
    code: number
    message: string
    data: T
}

interface DayData {
    date: string
    day_type: string
    daily_qty: number
    points: number[]
}

interface DecomposeData {
    times: string[]
    year: DayData[]
    month: DayData[]
    tenday1: DayData[]
    tenday2: DayData[]
    tenday3: DayData[]
}
async function checkConfigStatus() {
    try {
        const res = await request<{ has_curve: boolean, has_holiday: boolean }>({
            url: '/contract/config/status',
            method: 'get'
        })
        hasCurve.value = res.has_curve
        hasHoliday.value = res.has_holiday
    } catch (e) {
        console.warn('检查基础配置状态失败', e)
    }
}
// 修改原先的 submit/loadData 函数
async function loadData() {
    // ⭐ 新增：生成前校验
    if (!hasCurve.value) {
        if (confirm('数据库中缺失「典型曲线」，无法生成分解。是否现在去配置？')) {
            router.push('/contract/config')
        }
        return
    }
    if (!query.year || !query.month) return
    loading.value = true

    try {
        const res = await request<ApiResponse<DecomposeData>>({
            url: '/contract/decompose',
            method: 'post',
            data: {
                year: query.year,
                month: query.month,
                qty_year: query.qty.year || 0,
                qty_month: query.qty.month || 0,
                qty_tenday1: query.qty.tenday1 || 0,
                qty_tenday2: query.qty.tenday2 || 0,
                qty_tenday3: query.qty.tenday3 || 0,
            }
        })
        // 根据你的 request 封装，可能直接返回 data，也可能返回 {code, data}
        const data = res.data || res
        times.value = data.times
        resultData.value = data
        if (data.year?.length) activeTab.value = 'year'
    } catch (err: any) {
        alert(err.message || '分解失败，请检查是否在设置中上传了典型曲线')
    } finally {
        loading.value = false
    }
}

async function exportData() {
    if (!resultData.value) return
    try {
        const res = await fetch(apiUrl('/contract/export'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resultData: resultData.value, times: times.value }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = '合约分解结果.xlsx'
        a.click()
        URL.revokeObjectURL(url)
    } catch (e) {
        alert('导出失败：' + (e as Error).message)
    }
}

function getRowBg(type: string) {
    if (type === '周六') return '#f0f7ff'
    if (type === '周日') return '#fdf6ec'
    if (type === '法定节假日') return '#fef0f0'
    return '#ffffff'
}
onMounted(() => {
    checkConfigStatus()
})
</script>

<style scoped>
/* 顶栏和卡片样式 */
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

.separator {
    color: #909399;
}

.qty-item {
    border-left: 1px solid #ebeef5;
    padding-left: 16px;
}

.qty-item .input {
    width: 90px;
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

.btn-outline {
    height: 34px;
    padding: 0 20px;
    background: #fff;
    color: #2d6cdf;
    border: 1px solid #2d6cdf;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.btn-primary:disabled,
.btn-outline:disabled {
    opacity: 0.6;
    cursor: not-allowed;
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
}

.tabs-header {
    display: flex;
    border-bottom: 1px solid #ebeef5;
    padding: 0 16px;
}

.tab-btn {
    padding: 12px 24px;
    border: none;
    background: none;
    font-size: 14px;
    color: #606266;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
}

.tab-btn.active {
    color: #2d6cdf;
    font-weight: 600;
    border-bottom-color: #2d6cdf;
}

.table-wrap {
    flex: 1;
    overflow: auto;
}

.result-table {
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
    text-align: right;
    white-space: nowrap;
    min-width: max-content;
}

.result-table th,
.result-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
}

.result-table th {
    background: #f5f7fa;
    position: sticky;
    top: 0;
    z-index: 10;
    text-align: center;
}

.sticky-col {
    position: sticky;
    background: var(--row-bg, #fff);
    z-index: 5;
    border-right: 1px solid #dcdfe6;
}

.result-table th.sticky-col {
    z-index: 20;
    background: #f5f7fa;
}

.col-date {
    left: 0;
    width: 80px;
    text-align: center;
}

.col-type {
    left: 80px;
    width: 80px;
    text-align: center;
}

.col-qty {
    left: 160px;
    width: 100px;
    text-align: right;
    font-weight: 500;
}

.empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
}

/* ===== 基础配置缺失警告横幅 ===== */
.config-warning {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    background: #fdf6ec;
    border: 1px solid #f5dab1;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
}

.warn-icon {
    font-size: 24px;
    line-height: 1.2;
}

.warn-content {
    flex: 1;
}

.warn-title {
    margin: 0 0 6px;
    font-size: 14px;
    font-weight: 600;
    color: #b88230;
}

.warn-list {
    margin: 0;
    padding-left: 20px;
    font-size: 13px;
    color: #a16d1d;
    line-height: 1.6;
}

.warn-list .req {
    color: #f56c6c;
    font-weight: 600;
}

.warn-action {
    display: flex;
    align-items: center;
    align-self: center;
}

.btn-sm {
    height: 30px;
    padding: 0 16px;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    text-decoration: none;
}
</style>