<template>
    <SettlementSimForm :config="config" />
</template>

<script setup lang="ts">
import SettlementSimForm from '@/components/SettlementSimForm.vue'
import type { SettlementSimConfig } from '@/components/settlement-sim-types'

const config: SettlementSimConfig = {
    title: '结算单更新 · 模拟结算单',
    taskType: 'simulate',
    showYearSource: true,
    showMonthlyPrice: true,
    showDeclaration: true,
}
</script>