<template>
    <NodeHeatmapPage :config="config">
        <template #empty>
            <p class="empty-tip">暂无价差数据...</p>
        </template>
    </NodeHeatmapPage>
</template>

<script setup lang="ts">
import NodeHeatmapPage from '@/components/NodeHeatmapPage.vue'
import type { HeatmapConfig } from '@/components/node-heatmap-types'

const config: HeatmapConfig = {
    title: '价差分析 · 统一结算点（48 点）',
    uploadKey: 'spread-unified',
    uploadText: '📤 上传实时价格',
    kind: 'spread',
    nodeType: 'unified',
    mode: 'spread',
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
    line-height: 1.8;
}
</style>