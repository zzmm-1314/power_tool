<template>
    <SpotAnalysisPage :config="config" />
</template>

<script setup lang="ts">
import SpotAnalysisPage from '@/components/SpotAnalysisPage.vue'
import type { SpotAnalysisConfig } from '@/components/spot-analysis-types'

const config: SpotAnalysisConfig = {
    title: '滚撮收益模拟',
    nodeLabel: '电厂节点',
    apiUrl: '/rolling/spot-analysis',
    buyDirection: '买方',
    sellDirection: '卖方',
    buyLabel: '买入',
    sellLabel: '卖出',
    columns: [
        { key: 'opDate', label: '操作日期' },
        { key: 'tradeDate', label: '标的日' },
        { key: 'timeType', label: '分时段类型' },
        { key: 'direction', label: '买卖方向' },
        { key: 'qty', label: '成交电量', decimals: 3 },
        { key: 'price', label: '成交均价', decimals: 3 },
        { key: 'tradeQty', label: '交易电量', decimals: 3 },
        { key: 'clearPrice', label: '日前出清电价', decimals: 3 },
        { key: 'priceDiff', label: '电价差', decimals: 3 },
        { key: 'finalDiff', label: '差额(元)', decimals: 2, colored: true },
    ],
}
</script>