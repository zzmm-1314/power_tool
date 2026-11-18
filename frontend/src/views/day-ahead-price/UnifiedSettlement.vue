<template>
    <NodeHeatmapPage :config="config">
        <template #empty>
            <p class="empty-tip">
                暂无数据，请点击右上角「📤 上传 Excel」上传
                <code>日前市场出清负荷侧电价YYYYMMDD.xlsx</code>
            </p>
        </template>
    </NodeHeatmapPage>
</template>

<script setup lang="ts">
import NodeHeatmapPage from '@/components/NodeHeatmapPage.vue'
import type { HeatmapConfig } from '@/components/node-heatmap-types'

const config: HeatmapConfig = {
    title: '日前电价 · 统一结算点',
    uploadKey: 'day-ahead-unified',
    uploadText: '📤 上传 Excel',
    kind: 'day-ahead',
    nodeType: 'unified',
    mode: 'price',
    basePrice: 350,
}
</script>

<style scoped>
.empty-tip {
    padding: 40px 16px;
    text-align: center;
    color: #909399;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.empty-tip code {
    padding: 1px 6px;
    background: #f4f4f5;
    border-radius: 3px;
    color: #606266;
    font-size: 12px;
}
</style>