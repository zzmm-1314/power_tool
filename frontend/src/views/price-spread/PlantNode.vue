<template>
    <NodeHeatmapPage :config="config">
        <template #empty="{ nodes, nodeName }">
            <p v-if="!nodes.length" class="empty-tip">
                暂无节点数据，请点击右上角「📤 上传实时节点价格」上传
            </p>
            <p v-else-if="!nodeName" class="empty-tip">请选择上方节点后查看热力图</p>
            <p v-else class="empty-tip">
                节点「{{ nodeName }}」在所选时间段内没有同时存在「日前节点」和「实时节点」的数据
            </p>
        </template>
    </NodeHeatmapPage>
</template>

<script setup lang="ts">
import NodeHeatmapPage from '@/components/NodeHeatmapPage.vue'
import type { HeatmapConfig } from '@/components/node-heatmap-types'

const config: HeatmapConfig = {
    title: '价差分析 · 电厂节点（48 点）',
    uploadKey: 'spread-plant',
    uploadText: '📤 上传实时节点价格',
    kind: 'spread',
    nodeType: 'plant',
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