<template>
    <NodeHeatmapPage :config="config">
        <template #empty="{ nodes, nodeName }">
            <p v-if="!nodes.length" class="empty-tip">
                暂无节点数据，请点击右上角「📤 上传 Excel」上传
                <code>日前市场出清节点电价YYYYMMDD.xlsx</code>
            </p>
            <p v-else-if="!nodeName" class="empty-tip">请选择上方节点后查看热力图</p>
            <p v-else class="empty-tip">节点「{{ nodeName }}」在该时间段内无数据</p>
        </template>
    </NodeHeatmapPage>
</template>

<script setup lang="ts">
import NodeHeatmapPage from '@/components/NodeHeatmapPage.vue'
import type { HeatmapConfig } from '@/components/node-heatmap-types'

const config: HeatmapConfig = {
    title: '日前电价 · 电厂节点',
    uploadKey: 'day-ahead-plant',
    uploadText: '📤 上传 Excel',
    kind: 'day-ahead',
    nodeType: 'plant',
    mode: 'price',
    basePrice: 350,
}
</script>

<style scoped>
/* 与上一个文件相同 .empty-tip 样式 */
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
</style>