<template>
    <div class="chart-panel">
        <div v-if="title" class="chart-title">{{ title }}</div>
        <div class="chart-wrap" :style="{ height }">
            <VChart class="chart" :option="option" :loading="loading" autoresize />
        </div>
    </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'


withDefaults(
    defineProps<{
        option: EChartsOption
        title?: string
        height?: string
        loading?: boolean
    }>(),
    {
        height: '360px',
        loading: false,
    },
)
</script>

<style scoped>
.chart-panel {
    padding: 12px 16px;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.chart-title {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.chart-wrap {
    width: 100%;
}

.chart {
    width: 100%;
    height: 100%;
}
</style>