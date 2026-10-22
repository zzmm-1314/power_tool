<template>
    <PageContainer title="统调电厂">
        <template #extra>
            <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="file-input" @change="onFileChange" />
            <button class="btn" :disabled="!selectedFile || importing" @click="doImport">
                {{ importing ? '导入中...' : '📥 导入数据' }}
            </button>
            <button class="btn ghost" :disabled="importing || !mapData.totalUnits" @click="doClear">
                清空
            </button>
        </template>

        <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>

        <div class="layout">
            <!-- 左侧地图 -->
            <div class="map-panel">
                <div class="panel-title">浙江省电厂分布（按市）</div>

                <!-- 地图加载失败提示（覆盖 VChart 内嵌的 title 之外再加一层保险） -->
                <div v-if="mapError && !mapReady" class="map-error">
                    <p>{{ mapError }}</p>
                    <button class="btn small" @click="retryMap">重试加载地图</button>
                </div>

                <div v-else-if="!mapData.totalUnits" class="empty">
                    暂无数据，请先导入统调电厂 Excel
                </div>

                <div v-else class="map-wrap">
                    <VChart :option="mapOption" :loading="loadingMap" autoresize class="chart" />
                </div>

                <div v-if="mapData.totalUnits" class="map-summary">
                    <span>电厂总数：<strong>{{ mapData.totalPlants }}</strong></span>
                    <span>机组总数：<strong>{{ mapData.totalUnits }}</strong></span>
                    <span>覆盖城市：<strong>{{ mapData.totalCities }}</strong></span>
                    <span>
                        铭牌出力合计：<strong>{{ mapData.totalCapacity.toFixed(2) }}</strong> MW
                    </span>
                </div>
            </div>

            <!-- 右侧表格 -->
            <div class="table-panel">
                <!-- 顶部 Tab -->
                <div class="tab-bar">
                    <button class="tab-btn" :class="{ active: rightTab === 'detail' }" @click="rightTab = 'detail'">
                        机组明细
                    </button>
                    <button class="tab-btn" :class="{ active: rightTab === 'city' }" @click="rightTab = 'city'">
                        按市汇总
                    </button>
                </div>

                <!-- ① 机组明细 -->
                <template v-if="rightTab === 'detail'">
                    <div class="search-bar">
                        <input v-model.trim="keyword" type="text" placeholder="搜索调度命名 / 机组号 / 城市"
                            class="input search-input" @input="onSearchDebounced" />
                        <select v-model="city" class="input" @change="onSearch">
                            <option value="">全部城市</option>
                            <option v-for="c in cityOptions" :key="c" :value="c">{{ c }}</option>
                        </select>
                        <button class="btn small" @click="onSearch">查询</button>
                    </div>

                    <div class="table-wrap">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="width: 60px">#</th>
                                    <th>调度命名</th>
                                    <th style="width: 100px">机组序号</th>
                                    <th style="width: 130px">铭牌出力(MW)</th>
                                    <th style="width: 120px">所在城市</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(r, i) in rows" :key="i">
                                    <td class="center muted">
                                        {{ (pager.page - 1) * pager.pageSize + i + 1 }}
                                    </td>
                                    <td>{{ r.plant }}</td>
                                    <td class="center">{{ r.unit }}</td>
                                    <td class="center">
                                        {{ r.capacity != null ? r.capacity.toFixed(2) : '—' }}
                                    </td>
                                    <td class="center">{{ r.city }}</td>
                                </tr>
                                <tr v-if="!rows.length">
                                    <td colspan="5" class="empty-row">暂无数据</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="pager">
                        <span class="pager-info">
                            共 {{ pager.total }} 条 · 第 {{ pager.page }} / {{ totalPages }} 页
                        </span>
                        <div class="pager-btns">
                            <button class="pager-btn" :disabled="pager.page <= 1" @click="goto(pager.page - 1)">
                                上一页
                            </button>
                            <button v-for="p in pageNumbers" :key="p" class="pager-btn"
                                :class="{ active: p === pager.page }" @click="goto(p)">
                                {{ p }}
                            </button>
                            <button class="pager-btn" :disabled="pager.page >= totalPages"
                                @click="goto(pager.page + 1)">
                                下一页
                            </button>
                        </div>
                        <select v-model.number="pager.pageSize" class="input page-size" @change="goto(1)">
                            <option :value="10">10 条/页</option>
                            <option :value="20">20 条/页</option>
                            <option :value="50">50 条/页</option>
                            <option :value="100">100 条/页</option>
                        </select>
                    </div>
                </template>

                <!-- ② 按市汇总 -->
                <template v-else>
                    <div class="table-wrap">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="width: 60px">#</th>
                                    <th>城市</th>
                                    <th style="width: 90px">电厂数</th>
                                    <th style="width: 90px">机组数</th>
                                    <th style="width: 130px">铭牌出力(MW)</th>
                                    <th style="width: 100px">全省占比</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(c, i) in mapData.cities" :key="c.city">
                                    <td class="center muted">{{ i + 1 }}</td>
                                    <td><strong>{{ c.city }}</strong></td>
                                    <td class="center">{{ c.plantCount }}</td>
                                    <td class="center">{{ c.unitCount }}</td>
                                    <td class="center price">{{ c.totalCapacity.toFixed(2) }}</td>
                                    <td class="center">
                                        <div class="ratio-cell">
                                            <div class="ratio-bar">
                                                <div class="ratio-fill" :style="{ width: ratioWidth(c.totalCapacity) }">
                                                </div>
                                            </div>
                                            <span class="ratio-text">{{ ratioPct(c.totalCapacity) }}</span>
                                        </div>
                                    </td>
                                </tr>
                                <tr v-if="!mapData.cities.length">
                                    <td colspan="6" class="empty-row">暂无数据</td>
                                </tr>
                                <tr v-else class="total-row">
                                    <td colspan="2" class="center">全省合计</td>
                                    <td class="center">{{ mapData.totalPlants }}</td>
                                    <td class="center">{{ mapData.totalUnits }}</td>
                                    <td class="center price">
                                        {{ mapData.totalCapacity.toFixed(2) }}
                                    </td>
                                    <td class="center">100%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </template>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import VChart from 'vue-echarts'
import { registerMap } from '@/plugins/echarts'
import type { EChartsOption } from 'echarts'
import PageContainer from '@/components/PageContainer.vue'
import {
    importUnifiedPlants,
    clearUnifiedPlants,
    fetchUnifiedPlantsPaged,
    fetchUnifiedPlantsMap,
    fetchUnifiedPlantsCities,
    type UnifiedPlantRow,
    type MapData,
} from '@/api/modules/unifiedPlants'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

/* ============================================
 *  导入
 * ============================================ */
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const importing = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')
/* 右侧 Tab */
const rightTab = ref<'detail' | 'city'>('detail')
/* 按市汇总：占比 */
function ratioPct(v: number): string {
    const total = mapData.value.totalCapacity || 0
    if (!total) return '0.00%'
    return `${((v / total) * 100).toFixed(2)}%`
}

function ratioWidth(v: number): string {
    const total = mapData.value.totalCapacity || 1
    const pct = Math.max(0, Math.min(100, (v / total) * 100))
    return `${pct}%`
}
function onFileChange(e: Event) {
    const t = e.target as HTMLInputElement
    selectedFile.value = t.files?.[0] ?? null
    msg.value = ''
}

async function doImport() {
    if (!selectedFile.value) return
    importing.value = true
    msg.value = ''

    try {
        const res = await importUnifiedPlants(selectedFile.value)
        msg.value = `导入成功：${res.count} 条机组 / ${res.plants} 个电厂 / ${res.cities} 个城市`
        msgType.value = 'ok'
        selectedFile.value = null
        if (fileInputRef.value) fileInputRef.value.value = ''

        // 关键：不阻塞 importing 恢复
        refreshAll().catch((e) => {
            console.warn('[Import] 刷新数据失败', e)
        })
    } catch (e) {
        msg.value = (e as Error).message || '导入失败'
        msgType.value = 'err'
    } finally {
        importing.value = false
    }
}

async function doClear() {
    if (!confirm('确定清空已导入的统调电厂数据？')) return
    importing.value = true
    try {
        await clearUnifiedPlants()
        msg.value = '已清空'
        msgType.value = 'ok'
        refreshAll().catch(() => undefined)
    } catch (e) {
        msg.value = (e as Error).message || '清空失败'
        msgType.value = 'err'
    } finally {
        importing.value = false
    }
}

/* ============================================
 *  地图
 * ============================================ */
const mapData = ref<MapData>({
    cities: [],
    maxPlantCount: 0,
    maxCapacity: 0,          // ← 新增
    totalCapacity: 0,        // ← 新增
    totalPlants: 0,
    totalUnits: 0,
    totalCities: 0,
})

const loadingMap = ref(false)

/** 地图注册状态（响应式，让模板/computed 感知） */
const mapReady = ref(false)
const mapError = ref('')

const GEO_URLS = [
    '/geo/zhejiang.json',
    'https://geo.datav.aliyun.com/areas_v3/bound/330000_full.json',
]

async function ensureMap() {
    if (mapReady.value) return

    let lastErr = ''
    for (const url of GEO_URLS) {
        try {
            // 3 秒超时，避免 Vite 对不存在的路径长时间挂起
            const ctrl = new AbortController()
            const timer = setTimeout(() => ctrl.abort(), 3000)

            const resp = await fetch(url, { signal: ctrl.signal })
            clearTimeout(timer)

            if (!resp.ok) {
                lastErr = `${url} → HTTP ${resp.status}`
                continue
            }
            const text = await resp.text()
            if (text.trim().startsWith('<')) {
                // SPA fallback HTML
                lastErr = `${url} → 返回 HTML 而非 JSON`
                continue
            }
            const geo = JSON.parse(text)
            registerMap('zhejiang', geo)
            mapReady.value = true
            mapError.value = ''
            return
        } catch (e) {
            lastErr = `${url} → ${(e as Error).message}`
            console.warn('[Map] 加载失败:', lastErr)
        }
    }

    mapError.value = lastErr || '地图加载失败'
    throw new Error(
        `浙江省地图加载失败，请手动下载：https://geo.datav.aliyun.com/areas_v3/bound/330000_full.json ` +
        `并保存到 frontend/public/geo/zhejiang.json。错误：${lastErr}`,
    )
}

const mapOption = computed<EChartsOption>(() => {
    if (!mapReady.value) {
        return {
            title: {
                text: mapError.value ? '地图数据加载失败' : '地图加载中...',
                subtext: mapError.value
                    ? '请下载 zhejiang.json 到 frontend/public/geo/ 后刷新'
                    : '',
                left: 'center',
                top: 'center',
                textStyle: { color: '#909399', fontSize: 14, fontWeight: 'normal' },
                subtextStyle: { color: '#c0c4cc', fontSize: 12, lineHeight: 20 },
            },
        }
    }

    const max = Math.max(mapData.value.maxCapacity, 1)

    return {
        tooltip: {
            trigger: 'item',
            formatter: (p: any) => {
                const name = p.name || ''
                const item = mapData.value.cities.find((c) => c.city === name)
                if (!item) return `${name}<br/>暂无数据`
                return (
                    `<b>${name}</b><br/>` +
                    `铭牌出力：${item.totalCapacity.toFixed(2)} MW<br/>` +
                    `电厂：${item.plantCount} 个<br/>` +
                    `机组：${item.unitCount} 台`
                )
            },
        },
        visualMap: {
            min: 0,
            max,
            left: 'left',
            bottom: 'bottom',
            text: ['高', '低'],
            calculable: true,
            formatter: '{value} MW',              // ← 关键修复
            inRange: {
                color: ['#fff0f0', '#ffc9c9', '#ff8787', '#e03131', '#8b0000'],
            },
            textStyle: { fontSize: 12, color: '#606266' },
        },
        series: [
            {
                type: 'map',
                map: 'zhejiang',
                roam: true,
                zoom: 1.15,
                itemStyle: {
                    areaColor: '#fff0f0',
                    borderColor: '#c0c4cc',
                    borderWidth: 0.8,
                },
                emphasis: {
                    label: { color: '#303133', fontWeight: 600 },
                    itemStyle: { areaColor: '#ffd666', borderColor: '#d4b106' },
                },
                label: {
                    show: true,
                    fontSize: 11,
                    color: '#303133',
                    formatter: (p: any) => {
                        const item = mapData.value.cities.find((c) => c.city === p.name)
                        if (!item) return p.name
                        return `${p.name}\n${item.totalCapacity.toFixed(0)} MW`
                    },
                },
                data: mapData.value.cities.map((c) => ({
                    name: c.city,
                    value: c.totalCapacity,
                })),
            },
        ],
    }
})

async function loadMap() {
    loadingMap.value = true
    try {
        await ensureMap()
        mapData.value = await fetchUnifiedPlantsMap()
    } catch (e) {
        // 只记录错误，不抛出，避免影响 Promise.all
        console.warn('[Map] 加载地图数据失败', e)
        if (!mapError.value) {
            mapError.value = (e as Error).message || '地图加载失败'
        }
    } finally {
        loadingMap.value = false
    }
}

/* 手动重试地图 */
async function retryMap() {
    mapReady.value = false
    mapError.value = ''
    await loadMap()
}

/* ============================================
 *  表格
 * ============================================ */
const rows = ref<UnifiedPlantRow[]>([])
const pager = reactive({ page: 1, pageSize: 20, total: 0 })
const keyword = ref('')
const city = ref('')
const cityOptions = ref<string[]>([])

const totalPages = computed(() =>
    Math.max(1, Math.ceil(pager.total / pager.pageSize)),
)

const pageNumbers = computed<number[]>(() => {
    const total = totalPages.value
    const cur = pager.page
    const pages: number[] = []
    const start = Math.max(1, Math.min(cur - 2, total - 4))
    const end = Math.min(total, start + 4)
    for (let p = start; p <= end; p++) pages.push(p)
    return pages
})

async function loadTable() {
    try {
        const res = await fetchUnifiedPlantsPaged({
            page: pager.page,
            pageSize: pager.pageSize,
            keyword: keyword.value,
            city: city.value,
        })
        rows.value = res.items
        pager.total = res.total
        pager.page = res.page
        pager.pageSize = res.pageSize
    } catch (e) {
        console.warn('[Table] 查询失败', e)
    }
}

function goto(page: number) {
    if (page < 1 || page > totalPages.value) return
    pager.page = page
    loadTable()
}

let searchTimer: number | undefined
function onSearchDebounced() {
    window.clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => {
        pager.page = 1
        loadTable()
    }, 300)
}

function onSearch() {
    pager.page = 1
    loadTable()
}

/* ============================================
 *  加载 / 刷新
 * ============================================ */
async function refreshAll() {
    // 城市列表：失败也不影响流程
    try {
        cityOptions.value = await fetchUnifiedPlantsCities()
    } catch {
        cityOptions.value = []
    }

    // 表格与地图并行，各自内部处理异常
    await Promise.all([loadTable(), loadMap()])
}

watch(() => appStore.dataVersion, () => {
    refreshAll().catch(() => undefined)
})

onMounted(() => {
    refreshAll().catch(() => undefined)
})

onBeforeUnmount(() => window.clearTimeout(searchTimer))
</script>

<style scoped>
.file-input {
    font-size: 13px;
    max-width: 240px;
}

.btn {
    height: 30px;
    padding: 0 14px;
    border: none;
    border-radius: 4px;
    background: #2d6cdf;
    color: #fff;
    cursor: pointer;
    font-size: 13px;
}

.btn:hover:not(:disabled) {
    background: #2459b8;
}

.btn:disabled {
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

.btn.small {
    height: 28px;
    padding: 0 12px;
    font-size: 12px;
}

.msg {
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    margin: 0;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}

/* 布局 */
.layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 12px;
    min-height: 0;
}

.map-panel,
.table-panel {
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    min-width: 0;
}

.map-panel {
    padding: 12px;
}

.panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    padding: 0 4px 8px;
}

.map-wrap {
    flex: 1;
    min-height: 440px;
}

.chart {
    width: 100%;
    height: 100%;
    min-height: 440px;
}

.empty {
    padding: 80px 16px;
    text-align: center;
    color: #c0c4cc;
    font-size: 13px;
}

.map-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    padding: 8px 4px 0;
    font-size: 12px;
    color: #606266;
    border-top: 1px solid #f0f2f5;
    margin-top: 8px;
}

.map-summary strong {
    color: #2d6cdf;
}

/* 表格 */
.table-panel {
    padding: 12px;
    overflow: hidden;
}

.search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}

.input {
    height: 30px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.search-input {
    flex: 1;
    min-width: 180px;
}

.table-wrap {
    flex: 1;
    overflow: auto;
    border: 1px solid #f0f2f5;
    border-radius: 4px;
    min-height: 0;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.data-table th,
.data-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
}

.data-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    font-size: 12px;
}

.data-table td.center,
.data-table th.center {
    text-align: center;
}

.data-table td.muted {
    color: #909399;
}

.empty-row {
    text-align: center;
    color: #c0c4cc;
    padding: 24px 0 !important;
}

/* 分页 */
.pager {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
    justify-content: space-between;
}

.pager-info {
    font-size: 12px;
    color: #606266;
}

.pager-btns {
    display: flex;
    gap: 4px;
}

.pager-btn {
    min-width: 30px;
    height: 28px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 12px;
    cursor: pointer;
}

.pager-btn:hover:not(:disabled):not(.active) {
    border-color: #2d6cdf;
    color: #2d6cdf;
}

.pager-btn.active {
    background: #2d6cdf;
    color: #fff;
    border-color: #2d6cdf;
}

.pager-btn:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
}

.page-size {
    width: 110px;
}

@media (max-width: 1100px) {
    .layout {
        grid-template-columns: minmax(0, 1fr);
    }
}

.map-error {
    padding: 40px 20px;
    text-align: center;
    color: #f56c6c;
    font-size: 13px;
    line-height: 1.8;
    background: #fef0f0;
    border-radius: 4px;
    margin: 8px;
}

.map-error p {
    margin: 0 0 10px;
}

/* 右侧 Tab */
.tab-bar {
    display: flex;
    gap: 4px;
    padding: 2px;
    background: #f5f7fa;
    border-radius: 6px;
    margin-bottom: 10px;
    flex: 0 0 auto;
}

.tab-btn {
    height: 28px;
    padding: 0 16px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #606266;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}

.tab-btn:hover {
    color: #2d6cdf;
}

.tab-btn.active {
    background: #fff;
    color: #2d6cdf;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 汇总表 · 占比列 */
.price {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    color: #1f2d3d;
}

.ratio-cell {
    display: flex;
    align-items: center;
    gap: 6px;
}

.ratio-bar {
    flex: 1;
    height: 6px;
    background: #f0f2f5;
    border-radius: 3px;
    overflow: hidden;
    min-width: 40px;
}

.ratio-fill {
    height: 100%;
    background: linear-gradient(90deg, #ffc9c9, #e03131);
    border-radius: 3px;
    transition: width 0.3s;
}

.ratio-text {
    min-width: 46px;
    text-align: right;
    font-size: 12px;
    color: #606266;
    font-variant-numeric: tabular-nums;
}

/* 汇总表合计行 */
.total-row td {
    border-top: 2px solid #dcdfe6;
    background: #fafbfc;
    font-weight: 600;
    color: #1f2d3d;
}
</style>