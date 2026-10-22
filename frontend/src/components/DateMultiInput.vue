<template>
    <div class="date-multi">
        <textarea :value="modelValue.join(', ')" class="textarea" rows="2"
            placeholder="留空表示全部日期；多个日期用英文逗号分隔，如：2026-10-01, 2026-10-02" @input="onInput"></textarea>
        <button class="btn-clear" type="button" @click="$emit('update:modelValue', [])">
            清空
        </button>
    </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: string[] }>()
const emit = defineEmits<{
    (e: 'update:modelValue', v: string[]): void
}>()

function onInput(e: Event) {
    const text = (e.target as HTMLTextAreaElement).value
    const list = text
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter((s) => s)
    emit('update:modelValue', list)
}
</script>

<style scoped>
.date-multi {
    display: flex;
    gap: 6px;
    align-items: flex-start;
}

.textarea {
    flex: 1;
    padding: 6px 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'Consolas', 'Monaco', monospace;
    outline: none;
    resize: vertical;
}

.textarea:focus {
    border-color: #2d6cdf;
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
</style>