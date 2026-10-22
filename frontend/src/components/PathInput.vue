<template>
    <div class="path-input">
        <input :value="modelValue" type="text" class="input" :placeholder="placeholder"
            @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)" />
        <button class="btn-browse" :disabled="browsing" @click="browse">
            {{ browsing ? '...' : '浏览' }}
        </button>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { browseFile, browseFolder } from '@/api/modules/settlement'

const props = withDefaults(
    defineProps<{
        modelValue: string
        type?: 'file' | 'folder'
        placeholder?: string
    }>(),
    { type: 'file', placeholder: '' },
)

const emit = defineEmits<{
    (e: 'update:modelValue', v: string): void
}>()

const browsing = ref(false)

async function browse() {
    browsing.value = true
    try {
        const res = props.type === 'folder' ? await browseFolder() : await browseFile()
        if (res?.path) emit('update:modelValue', res.path)
    } catch (e) {
        alert((e as Error).message)
    } finally {
        browsing.value = false
    }
}
</script>

<style scoped>
.path-input {
    display: flex;
    gap: 6px;
}

.input {
    flex: 1;
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    font-family: 'Consolas', 'Monaco', monospace;
}

.input:focus {
    border-color: #2d6cdf;
}

.btn-browse {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
}

.btn-browse:hover:not(:disabled) {
    border-color: #2d6cdf;
    color: #2d6cdf;
}

.btn-browse:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
}
</style>