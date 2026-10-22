<template>
    <div class="date-range">
        <input :value="start" type="date" class="input" :max="end || undefined" @input="onStart" />
        <span class="sep">至</span>
        <input :value="end" type="date" class="input" :min="start || undefined" @input="onEnd" />
        <button type="button" class="btn-clear" @click="clear">清空</button>
        <span v-if="dayCount > 0" class="count">共 {{ dayCount }} 天</span>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { expandDateRange } from '@/utils/dateRange'

const props = defineProps<{
    start: string
    end: string
}>()

const emit = defineEmits<{
    (e: 'update:start', v: string): void
    (e: 'update:end', v: string): void
}>()

const dayCount = computed(
    () => expandDateRange(props.start, props.end).length,
)

function onStart(e: Event) {
    const v = (e.target as HTMLInputElement).value
    emit('update:start', v)
    // 结束日期为空 → 自动同步为开始日
    if (v && !props.end) {
        emit('update:end', v)
    }
    // 若结束早于开始 → 同步
    if (v && props.end && props.end < v) {
        emit('update:end', v)
    }
}

function onEnd(e: Event) {
    const v = (e.target as HTMLInputElement).value
    emit('update:end', v)
    if (v && props.start && props.start > v) {
        emit('update:start', v)
    }
}

function clear() {
    emit('update:start', '')
    emit('update:end', '')
}
</script>

<style scoped>
.date-range {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    width: 160px;
}

.input:focus {
    border-color: #2d6cdf;
}

.sep {
    font-size: 13px;
    color: #909399;
}

.btn-clear {
    height: 32px;
    padding: 0 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 12px;
    cursor: pointer;
}

.btn-clear:hover {
    color: #f56c6c;
    border-color: #fbc4c4;
}

.count {
    font-size: 12px;
    color: #909399;
}
</style>