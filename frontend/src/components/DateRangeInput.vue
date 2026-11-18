<template>
    <div class="date-range-wrapper">
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
            end-placeholder="结束日期" value-format="YYYY-MM-DD" format="YYYY-MM-DD" :clearable="false"
            @change="handleChange" />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { expandDateRange } from '@/utils/dateRange'

const props = defineProps<{
    start: string
    end: string
}>()

const emit = defineEmits<{
    (e: 'update:start', v: string): void
    (e: 'update:end', v: string): void
}>()

// 将分离的 start / end 转换为 Element Plus 需要的数组
const dateRange = ref<[string, string] | null>(null)

watch(
    () => [props.start, props.end],
    ([s, e]) => {
        if (s && e) {
            dateRange.value = [s, e]
        } else {
            dateRange.value = null
        }
    },
    { immediate: true }
)

function handleChange(val: [string, string] | null) {
    if (val) {
        emit('update:start', val[0])
        emit('update:end', val[1])
    } else {
        emit('update:start', '')
        emit('update:end', '')
    }
}

const dayCount = computed(
    () => expandDateRange(props.start, props.end).length,
)

function clear() {
    emit('update:start', '')
    emit('update:end', '')
    // ⭐ 清空后自动把日期设为今天
    const today = new Date().toISOString().slice(0, 10)
    emit('update:start', today)
    emit('update:end', today)
}
</script>

<style scoped>
.date-range-wrapper {
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

/* 覆盖 Element Plus 默认样式，使其与现有 UI 融合 */
:deep(.el-date-editor) {
    --el-date-editor-width: 260px;
    height: 30px;
    background-color: #fff;
    box-shadow: none;
}

:deep(.el-range-input) {
    font-size: 13px;
    color: #303133;
}
</style>