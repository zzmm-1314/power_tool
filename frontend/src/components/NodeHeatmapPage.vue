<template>
    <PageContainer :title="config.title">
        <template #extra>
            <div class="extra-group">
                <button class="btn-upload" @click="appStore.openUpload(config.uploadKey)">
                    {{ config.uploadText }}
                </button>
                <DataSourceTag :source="source" />
            </div>

            <div v-if="config.nodeType === 'plant'" class="extra-group">
                <label class="lbl">节点</label>
                <!-- 宽度从 200px 缩减到 160px 或 180px，防止拥挤 -->
                <SearchableSelect v-model="nodeName" :options="nodes" @change="load" style="width: 160px;" />
            </div>

            <div class="extra-group">
                <label class="lbl">日期</label>
                <DateRangeInput :start="dateStart" :end="dateEnd" @update:start="dateStart = $event"
                    @update:end="dateEnd = $event" />
                <!-- 顶部控制栏增加时段选择 -->
                <div v-if="config.mode === 'spread'" class="extra-group">
                    <label class="lbl">时段</label>
                    <select v-model.number="hourStart" class="input" style="width: 80px;">
                        <option v-for="h in 24" :key="h - 1" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:00
                        </option>
                    </select>
                    <span>至</span>
                    <select v-model.number="hourEnd" class="input" style="width: 80px;">
                        <option v-for="h in 24" :key="h" :value="h">{{ String(h).padStart(2, '0') }}:00</option>
                    </select>
                </div>
                <!-- ⭐ 新增查询按钮 -->
                <button class="btn" :disabled="loading" @click="load">
                    {{ loading ? '查询中...' : '查询' }}
                </button>
            </div>
        </template>

        <div class="content-wrapper">
            <LoadingMask :visible="loading" text="正在查询数据..." />
            <slot v-if="isEmpty" name="empty" :heatmap="heatmap" :nodes="nodes" :nodeName="nodeName" />
            <HeatmapGrid v-else :mode="config.mode" :show-positive-ratio="config.mode === 'spread'"
                :dates="filteredHeatmap.dates" :hours="filteredHeatmap.hours" :matrix="filteredHeatmap.matrix" />
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import DataSourceTag from '@/components/DataSourceTag.vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import HeatmapGrid from '@/components/HeatmapGrid.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import LoadingMask from '@/components/LoadingMask.vue'
import { useAppStore } from '@/stores/app'
import {
    fetchPlantHeatmap, fetchUnifiedHeatmap, type HeatmapData,
} from '@/api/modules/price'
import {
    fetchSpreadPlantHeatmap, fetchSpreadHeatmap, type SpreadHeatmapData,
} from '@/api/modules/spread'
import type { DataSource } from '@/types'
import type { HeatmapConfig } from './node-heatmap-types'
import { listPlantNodes, fetchPriceCompareDefaults } from '@/api/modules/nodes'
const props = defineProps<{ config: HeatmapConfig }>()
const appStore = useAppStore()

const loading = ref(false)
const dateStart = ref('')
const dateEnd = ref('')
const nodes = ref<string[]>([])
const nodeName = ref('')
const source = ref<DataSource>('empty')
const heatmap = ref<HeatmapData | SpreadHeatmapData>({
    dates: [], hours: [], matrix: [], source: 'empty', minValue: 0, maxValue: 0,
})
const hourStart = ref(0)
const hourEnd = ref(24)
const isEmpty = computed(() => {
    if (props.config.nodeType === 'plant') {
        return !nodes.value.length || !nodeName.value || !heatmap.value.dates.length
    }
    return !heatmap.value.dates.length
})
const filteredHeatmap = computed(() => {
    if (props.config.mode !== 'spread') return heatmap.value
    // 如果选 3 点，起始点应是 03:00（数组索引 5）。
    // 如果选 0 点，起始点从 00:30（数组索引 0）开始
    const startIdx = hourStart.value > 0 ? hourStart.value * 2 - 1 : 0
    const endIdx = hourEnd.value * 2
    return {
        ...heatmap.value,
        hours: heatmap.value.hours.slice(startIdx, endIdx),
        matrix: heatmap.value.matrix.slice(startIdx, endIdx)
    }
})
function initDateRange() {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 13)
    const fmt = (d: Date) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    dateEnd.value = fmt(end)
    dateStart.value = fmt(start)
}

async function loadNodes() {
    if (props.config.nodeType !== 'plant') return
    try {
        const list = await listPlantNodes()
        nodes.value = list.map(n => n.name)

        if (!nodeName.value && nodes.value.length) {
            // 1. 尝试获取全局默认节点配置
            let defaults: string[] = []
            try {
                defaults = await fetchPriceCompareDefaults()
            } catch {
                defaults = []
            }

            // 2. 如果配置了默认节点，优先选默认节点中的第一个（且必须在系统节点列表中）
            if (defaults.length > 0) {
                const firstDefault = defaults.find(d => nodes.value.includes(d))
                if (firstDefault) {
                    nodeName.value = firstDefault
                    return
                }
            }

            // 3. 如果没配置或者配置的节点都不存在，则降级选第一个
            nodeName.value = nodes.value[0]
        }
    } catch {
        nodes.value = []
    }
}

async function load() {
    if (!dateStart.value || !dateEnd.value) return
    if (props.config.nodeType === 'plant' && !nodeName.value) {
        heatmap.value = { dates: [], hours: [], matrix: [], source: 'empty', minValue: 0, maxValue: 0 }
        return
    }

    loading.value = true
    try {
        const isPlant = props.config.nodeType === 'plant'
        const params: any = { startDate: dateStart.value, endDate: dateEnd.value }
        if (isPlant) params.nodeName = nodeName.value

        let data: any
        if (props.config.kind === 'day-ahead') {
            data = isPlant
                ? await fetchPlantHeatmap(params)
                : await fetchUnifiedHeatmap(params)
        } else {
            data = isPlant
                ? await fetchSpreadPlantHeatmap(params)
                : await fetchSpreadHeatmap(params)
        }
        heatmap.value = data
        source.value = data.source
    } catch (e) {
        console.error(e)
        source.value = 'empty'
        heatmap.value = { dates: [], hours: [], matrix: [], source: 'empty', minValue: 0, maxValue: 0 }
    } finally {
        loading.value = false
    }
}

async function refreshAll() {
    await loadNodes()
    await load()
}

watch(() => appStore.dataVersion, () => refreshAll())
onMounted(() => {
    initDateRange()
    refreshAll()
})
</script>

<style scoped>
.content-wrapper {
    position: relative;
    min-height: 400px;
}

.extra-group {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
    min-width: 0;
}

.lbl {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}

.empty-tip {
    padding: 40px 16px;
    text-align: center;
    color: #909399;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    line-height: 1.8;
}

.empty-tip code {
    padding: 1px 6px;
    background: #f4f4f5;
    border-radius: 3px;
    color: #606266;
    font-size: 12px;
}

:deep(.date-range .input) {
    height: 30px;
    font-size: 13px;
}
</style>