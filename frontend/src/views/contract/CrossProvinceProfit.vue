<template>
    <SpotAnalysisPage :config="config" />
</template>

<script setup lang="ts">
import SpotAnalysisPage from '@/components/SpotAnalysisPage.vue'
import type { SpotAnalysisConfig } from '@/components/spot-analysis-types'

const config: SpotAnalysisConfig = {
    title: '长三角省间交易收益模拟',
    nodeLabel: '交易单元',
    apiUrl: '/cross-province/spot-analysis',
    buyDirection: '购电',
    sellDirection: '售电',
    buyLabel: '购电',
    sellLabel: '售电',
    columns: [
        { key: 'opDate', label: '操作日期' },
        { key: 'tradeDate', label: '标的日' },
        { key: 'timeType', label: '时段' },
        { key: 'fixedNode', label: '交易单元', fixedNode: true },  // 显示 query.node
        { key: 'direction', label: '方向' },
        { key: 'tradePath', label: '交易路径' },
        { key: 'price', label: '成交价', decimals: 3 },
        { key: 'qty', label: '成交数量', decimals: 3 },
        { key: 'clearPrice', label: '日前出清价', decimals: 3 },
        { key: 'priceDiff', label: '价差', decimals: 3 },
        { key: 'finalDiff', label: '收益(元)', decimals: 2, colored: true },
    ],
}
</script>