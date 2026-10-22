<template>
    <span class="source-tag" :class="cls">{{ text }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DataSource } from '@/types'

const props = defineProps<{ source?: DataSource }>()

const text = computed(() => {
    if (props.source === 'database') return '● 数据来源：数据库'
    if (props.source === 'excel') return '● 数据来源：Excel 临时'
    return '○ 暂无数据'
})

const cls = computed(() => ({
    db: props.source === 'database',
    excel: props.source === 'excel',
    empty: !props.source || props.source === 'empty',
}))
</script>

<style scoped>
.source-tag {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1;
}

.source-tag.db {
    background: #ecf5ff;
    color: #2d6cdf;
}

.source-tag.excel {
    background: #fdf6ec;
    color: #e6a23c;
}

.source-tag.empty {
    background: #f4f4f5;
    color: #909399;
}
</style>