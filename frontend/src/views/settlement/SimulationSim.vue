<template>
    <SettlementSimForm :config="config" />
</template>

<script setup lang="ts">
import SettlementSimForm from '@/components/SettlementSimForm.vue'
import type { SettlementSimConfig } from '@/components/settlement-sim-types'

const config: SettlementSimConfig = {
    title: '结算单更新 · 模拟结算单',
    taskType: 'simulate', // ⭐ 统一为 simulate
    showYearSource: true,
    showFixedFile: true, // ⭐ 保留固定申报功率
    showMonthlyPrice: true, // ⭐ 通用模拟单需要月度电价
    showDeclaration: true,
}
</script>