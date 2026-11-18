<template>
    <PageContainer title="电价对比">
        <!-- 顶部筛选 -->
        <div class="filter-bar">
            <div class="filter-item">
                <label>电厂节点</label>
                <div class="node-display" @click="openNodeModal">
                    <span class="node-text">{{ query.nodes || '点击选择节点...' }}</span>
                    <span class="arrow">▾</span>
                </div>
            </div>
            <div class="filter-item">
                <label>月份</label>
                <input v-model="query.month" type="month" class="input" style="width: 130px;" />
            </div>
            <button class="btn primary" :disabled="loading || !query.nodes || !query.month" @click="loadData">
                {{ loading ? '计算中...' : '🔍 查询并计算' }}
            </button>
        </div>

        <!-- ===== 节点选择模态窗 ===== -->
        <Teleport to="body">
            <div v-if="modalVisible" class="modal-mask" @click.self="modalVisible = false">
                <div class="modal-content">
                    <div class="modal-header">
                        <span>选择节点</span>
                        <div class="header-actions">
                            <button class="btn-save-default" @click="saveCurrentAsDefault">保存当前为默认</button>
                            <span class="close-btn" @click="modalVisible = false">✕</span>
                        </div>
                    </div>
                    <div class="modal-body">
                        <!-- 默认节点快捷区 -->
                        <div class="default-section" v-if="defaultNodes.length">
                            <div class="section-header">
                                <div class="section-title">默认节点（点击快速添加/移除）</div>
                                <div class="section-actions">
                                    <button class="text-btn" @click="selectAllDefaults">全选</button>
                                    <span class="divider">|</span>
                                    <button class="text-btn" @click="deselectAllDefaults">取消全选</button>
                                </div>
                            </div>
                            <div class="tags-wrap">
                                <span v-for="node in defaultNodes" :key="node" class="tag-btn"
                                    :class="{ active: tempSelectedNodes.includes(node) }" @click="toggleNode(node)">
                                    {{ node }}
                                </span>
                            </div>
                        </div>

                        <!-- 搜索框 -->
                        <div class="search-box">
                            <input v-model="searchKeyword" type="text" class="search-input" placeholder="搜索所有电厂节点..." />
                        </div>

                        <!-- 所有节点候选列表 -->
                        <div class="options-list">
                            <div v-for="node in filteredNodes" :key="node" class="option-item" @click="addNode(node)">
                                {{ node }}
                            </div>
                            <div v-if="!filteredNodes.length" class="empty-option">无匹配节点</div>
                        </div>

                        <!-- 已选区域 -->
                        <div class="selected-area">
                            <div class="selected-title">已选节点（点击右侧叉号移除）</div>
                            <div class="selected-tags">
                                <span v-for="(node, idx) in tempSelectedNodes" :key="idx" class="tag">
                                    {{ node }} <span class="remove-btn" @click="removeNode(idx)">✕</span>
                                </span>
                                <span v-if="!tempSelectedNodes.length" class="empty-selected">暂未选择</span>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn ghost" @click="modalVisible = false">取消</button>
                        <button class="btn primary" @click="confirmNodes">确定</button>
                    </div>
                </div>
            </div>
        </Teleport>

        <!-- 结果表格卡片 -->
        <div class="table-card">
            <!-- 子标签页切换 -->
            <div class="tabs-header">
                <button :class="['tab-btn', { active: activeTab === 'base' }]" @click="activeTab = 'base'">
                    电价与收益
                </button>
                <button :class="['tab-btn', { active: activeTab === 'simulate' }]" @click="activeTab = 'simulate'">
                    模拟结算
                </button>
            </div>

            <!-- 标签页 1：电价与收益 -->
            <div v-show="activeTab === 'base'" class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col">电厂</th>
                            <th>最新日期</th>
                            <th>裸电价</th>
                            <th>结算均价</th>
                            <th class="col-wrap" style="width: 130px;">官方均价<br>(仅供参考)</th>
                            <th>年度合约收益</th>
                            <th>月度合约收益</th>
                            <th class="col-wrap">省内滚撮<br>收益</th>
                            <th class="col-wrap">省内滚撮<br>买入电量</th>
                            <th class="col-wrap">省内滚撮<br>买入均价</th>
                            <th class="col-wrap">省内滚撮<br>卖出电量</th>
                            <th class="col-wrap">省内滚撮<br>卖出均价</th>
                            <th>现货收益</th>
                            <th class="col-wrap">省间滚撮<br>收益</th>
                            <th class="col-wrap">省间滚撮<br>买入电量</th>
                            <th class="col-wrap">省间滚撮<br>买入均价</th>
                            <th class="col-wrap">省间滚撮<br>卖出电量</th>
                            <th class="col-wrap">省间滚撮<br>卖出均价</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in results" :key="idx">
                            <td class="sticky-col">{{ row.node }}</td>
                            <td style="color: #909399;">{{ row.latestDate || '-' }}</td>
                            <td>{{ format3(row.barePrice) }}</td>
                            <td>{{ format3(row.settlementPrice) }}</td>
                            <!-- 官方均价输入保存 -->
                            <td>
                                <div style="display: flex; gap: 4px; justify-content: center;">
                                    <input v-model.number="row.officialPrice" type="number" class="inline-input"
                                        step="0.001" />
                                    <button class="btn-save" @click="saveOfficialPrice(row)">保存</button>
                                </div>
                            </td>
                            <td>{{ format2(row.yearFee) }}</td>
                            <td>{{ format2(row.monthFee) }}</td>
                            <td>{{ format2(row.intradayFee) }}</td>
                            <td>{{ format3(row.intradayBuyQty) }}</td>
                            <td>{{ format3(row.intradayBuyPrice) }}</td>
                            <td>{{ format3(row.intradaySellQty) }}</td>
                            <td>{{ format3(row.intradaySellPrice) }}</td>
                            <td :style="getColorStyle(row.spotProfit)">{{ format2(row.spotProfit) }}</td>
                            <td>{{ format2(row.csFee) }}</td>
                            <td>{{ format3(row.csBuyQty) }}</td>
                            <td>{{ format3(row.csBuyPrice) }}</td>
                            <td>{{ format3(row.csSellQty) }}</td>
                            <td>{{ format3(row.csSellPrice) }}</td>
                        </tr>
                        <tr v-if="!results.length">
                            <td colspan="18" class="empty-tip">暂无数据，请输入节点和月份后查询</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- 标签页 2：模拟结算 -->
            <div v-show="activeTab === 'simulate'" class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sticky-col">电厂</th>
                            <th>最新日期</th>
                            <th>实际电费(元)</th>
                            <th class="col-wrap" style="width: 150px;">模拟电费(元)</th>
                            <th class="col-wrap">模拟结算差额<br>(模拟-实际)</th>
                            <th class="col-wrap">反向差额<br>(实际-模拟)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, idx) in results" :key="idx">
                            <td class="sticky-col">{{ row.node }}</td>
                            <td style="color: #909399;">{{ row.latestDate || '-' }}</td>
                            <td>{{ format2(row.totalFee) }}</td>
                            <!-- 模拟电费输入保存 -->
                            <td>
                                <div style="display: flex; gap: 4px; justify-content: center;">
                                    <input v-model.number="row.simulatedFee" type="number" class="inline-input"
                                        step="0.01" />
                                    <button class="btn-save" @click="saveSimulatedFee(row)">保存</button>
                                </div>
                            </td>
                            <td :style="getDiffColorStyle(row.simulatedFee - row.totalFee)">
                                {{ (row.simulatedFee != null && row.totalFee != null) ? format2(row.simulatedFee -
                                    row.totalFee) : '-' }}
                            </td>
                            <td :style="getDiffColorStyle(row.totalFee - row.simulatedFee)">
                                {{ (row.simulatedFee != null && row.totalFee != null) ? format2(row.totalFee -
                                    row.simulatedFee) : '-' }}
                            </td>
                        </tr>
                        <tr v-if="!results.length">
                            <td colspan="6" class="empty-tip">暂无数据，请输入节点和月份后查询</td>
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
import { request } from '@/api/request'
import {
    listPlantNodes,
    fetchPriceCompareDefaults,
    savePriceCompareDefaults
} from '@/api/modules/nodes'

/* ==================== 状态 ==================== */
const query = reactive({
    nodes: '',
    month: new Date().toISOString().slice(0, 7)
})

const loading = ref(false)
const results = ref<any[]>([])
const activeTab = ref<'base' | 'simulate'>('base')

const allNodes = ref<string[]>([])
const defaultNodes = ref<string[]>([])
const modalVisible = ref(false)
const searchKeyword = ref('')
const tempSelectedNodes = ref<string[]>([])

onMounted(async () => {
    try {
        const list = await listPlantNodes()
        allNodes.value = list.map(n => n.name)
    } catch (e) {
        console.error('加载节点列表失败', e)
    }
    loadDefaults()
})

async function loadDefaults() {
    try {
        defaultNodes.value = await fetchPriceCompareDefaults()
    } catch {
        defaultNodes.value = []
    }
}

/* ==================== 节点选择逻辑 ==================== */
function openNodeModal() {
    tempSelectedNodes.value = query.nodes ? query.nodes.split(',').filter(Boolean) : []
    searchKeyword.value = ''
    modalVisible.value = true
}
function addNode(node: string) {
    if (!tempSelectedNodes.value.includes(node)) {
        tempSelectedNodes.value.push(node)
    }
    searchKeyword.value = ''
}
function toggleNode(node: string) {
    const idx = tempSelectedNodes.value.indexOf(node)
    if (idx > -1) {
        tempSelectedNodes.value.splice(idx, 1)
    } else {
        tempSelectedNodes.value.push(node)
    }
}
function removeNode(idx: number) {
    tempSelectedNodes.value.splice(idx, 1)
}
function confirmNodes() {
    query.nodes = tempSelectedNodes.value.join(',')
    modalVisible.value = false
}
const filteredNodes = computed(() => {
    const kw = searchKeyword.value.trim().toLowerCase()
    return allNodes.value.filter(n =>
        !tempSelectedNodes.value.includes(n) &&
        (!kw || n.toLowerCase().includes(kw))
    )
})

function selectAllDefaults() {
    const set = new Set(tempSelectedNodes.value)
    defaultNodes.value.forEach(node => set.add(node))
    tempSelectedNodes.value = Array.from(set)
}

function deselectAllDefaults() {
    tempSelectedNodes.value = tempSelectedNodes.value.filter(
        node => !defaultNodes.value.includes(node)
    )
}

async function saveCurrentAsDefault() {
    if (!tempSelectedNodes.value.length) {
        alert('当前没有选中任何节点，无法保存为默认')
        return
    }
    try {
        await savePriceCompareDefaults(tempSelectedNodes.value)
        await loadDefaults()
        alert('已成功保存为默认节点')
    } catch (e) {
        alert('保存失败：' + (e as Error).message)
    }
}

/* ==================== 数据查询 ==================== */
async function loadData() {
    if (!query.nodes || !query.month) return
    loading.value = true
    try {
        const res = await request<any[]>({
            url: '/settlement/actual/query',
            method: 'get',
            params: {
                nodes: query.nodes,
                month: query.month,
                compensation: 153.515
            }
        })
        results.value = res || []
    } catch (e) {
        alert('查询失败：' + (e as Error).message)
    } finally {
        loading.value = false
    }
}

/* ==================== 保存逻辑 ==================== */
async function saveOfficialPrice(row: any) {
    if (row.officialPrice == null || isNaN(row.officialPrice)) {
        alert('请输入有效的官方均价')
        return
    }
    try {
        await request({
            url: '/settlement/actual/save-official',
            method: 'post',
            data: {
                node: row.node,
                month: query.month,
                officialPrice: row.officialPrice
            }
        })
        alert('官方均价保存成功')
    } catch (e) {
        alert('保存失败：' + (e as Error).message)
    }
}

async function saveSimulatedFee(row: any) {
    if (row.simulatedFee == null || isNaN(row.simulatedFee)) {
        alert('请输入有效的模拟电费')
        return
    }
    try {
        await request({
            url: '/settlement/actual/save-official',
            method: 'post',
            data: {
                node: row.node,
                month: query.month,
                simulatedFee: row.simulatedFee
            }
        })
        alert('模拟电费保存成功')
    } catch (e) {
        alert('保存失败：' + (e as Error).message)
    }
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
function getColorStyle(val: number) {
    if (val == null || val === 0) return {}
    const maxAbs = Math.max(...results.value.map(r => Math.abs(r.spotProfit)), 1)
    const intensity = Math.min(Math.abs(val) / maxAbs, 1)
    if (val > 0) {
        return { backgroundColor: `rgba(245, 108, 108, ${0.1 + intensity * 0.6})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: '500' }
    } else {
        return { backgroundColor: `rgba(103, 194, 58, ${0.1 + intensity * 0.6})`, color: intensity > 0.6 ? '#fff' : '#303133', fontWeight: '500' }
    }
}
function getDiffColorStyle(val: number | null) {
    if (val == null || isNaN(val) || val === 0) return { color: '#303133' }
    if (val > 0) return { color: '#f56c6c', fontWeight: 'bold' }
    return { color: '#67c23a', fontWeight: 'bold' }
}
</script>

<style scoped>
/* ===== 顶部筛选 ===== */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #fff;
    padding: 12px 16px;
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
    border-radius: 6px;
    outline: none;
    font-size: 13px;
}

.node-display {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 300px;
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    font-size: 13px;
    transition: border-color 0.2s;
}

.node-display:hover {
    border-color: #2d6cdf;
}

.node-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #606266;
    flex: 1;
}

.arrow {
    color: #909399;
    font-size: 12px;
    margin-left: 8px;
}

.btn {
    height: 32px;
    padding: 0 16px;
    border-radius: 6px;
    cursor: pointer;
    border: none;
    font-size: 13px;
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

.btn.ghost:hover {
    background: #f5f7fa;
}

/* ===== 模态窗 ===== */
.modal-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.modal-content {
    width: 500px;
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    display: flex;
    flex-direction: column;
    max-height: 80vh;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #303133;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
}

.btn-save-default {
    background: #fdf6ec;
    color: #e6a23c;
    border: 1px solid #f5dab1;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
}

.btn-save-default:hover {
    background: #e6a23c;
    color: #fff;
}

.close-btn {
    cursor: pointer;
    color: #909399;
    font-size: 18px;
}

.close-btn:hover {
    color: #303133;
}

.modal-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    gap: 12px;
}

.search-box {
    flex-shrink: 0;
}

.search-input {
    width: 100%;
    height: 36px;
    padding: 0 12px;
    box-sizing: border-box;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}

.search-input:focus {
    border-color: #2d6cdf;
}

.options-list {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    max-height: 200px;
    background: #fafbfc;
}

.option-item {
    padding: 8px 12px;
    font-size: 13px;
    color: #303133;
    cursor: pointer;
    transition: background 0.15s;
}

.option-item:hover {
    background: #ecf5ff;
    color: #2d6cdf;
}

.empty-option {
    padding: 16px;
    text-align: center;
    color: #909399;
    font-size: 12px;
}

.selected-area {
    flex-shrink: 0;
    border-top: 1px dashed #ebeef5;
    padding-top: 12px;
}

.selected-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
}

.selected-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 30px;
}

.tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #f0f5ff;
    color: #2d6cdf;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.remove-btn {
    cursor: pointer;
    font-weight: bold;
}

.remove-btn:hover {
    color: #f56c6c;
}

.empty-selected {
    font-size: 12px;
    color: #c0c4cc;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 16px;
}

/* 默认节点快捷区 */
.default-section {
    background: #f8f9fb;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 4px;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.section-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 0;
}

.section-actions {
    display: flex;
    align-items: center;
    gap: 6px;
}

.text-btn {
    background: none;
    border: none;
    color: #2d6cdf;
    font-size: 12px;
    cursor: pointer;
    padding: 0;
}

.text-btn:hover {
    text-decoration: underline;
}

.divider {
    color: #dcdfe6;
    font-size: 10px;
}

.tags-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.tag-btn {
    padding: 4px 10px;
    background: #fff;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    color: #606266;
}

.tag-btn:hover {
    border-color: #2d6cdf;
    color: #2d6cdf;
}

.tag-btn.active {
    background: #2d6cdf;
    color: #fff;
    border-color: #2d6cdf;
}

/* ===== 表格卡片 & Tabs ===== */
.table-card {
    background: #fff;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    margin-top: 12px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.tabs-header {
    display: flex;
    border-bottom: 1px solid #ebeef5;
    margin-bottom: 12px;
    flex-shrink: 0;
}

.tab-btn {
    padding: 8px 24px;
    border: none;
    background: transparent;
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

.table-wrapper {
    flex: 1;
    overflow: auto;
    border: 1px solid #ebeef5;
    border-radius: 6px;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: right;
}

.data-table th,
.data-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #ebeef5;
    border-right: 1px solid #ebeef5;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.data-table th {
    background: #f5f7fa;
    position: sticky;
    top: 0;
    z-index: 2;
    text-align: center;
    color: #303133;
}

.data-table th.col-wrap {
    white-space: normal;
    line-height: 1.2;
    padding: 4px 6px;
    min-width: 65px;
    max-width: 80px;
    text-align: center;
}

.sticky-col {
    position: sticky;
    left: 0;
    background: #fff;
    z-index: 1;
    text-align: center;
    font-weight: 500;
}

th.sticky-col {
    background: #f5f7fa;
    z-index: 3;
}

.empty-tip {
    text-align: center;
    color: #909399;
    padding: 40px;
}

.inline-input {
    width: 80px;
    height: 24px;
    padding: 0 4px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 12px;
    text-align: right;
}

.btn-save {
    height: 24px;
    padding: 0 6px;
    border: none;
    background: #e6a23c;
    color: #fff;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
}
</style>