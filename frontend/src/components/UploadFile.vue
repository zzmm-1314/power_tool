<template>
    <div class="upload-file-container">
        <!-- 拖拽模式 -->
        <div v-if="drag" class="upload-drag-area" :class="{ 'is-dragover': isDragOver, 'is-disabled': disabled }"
            @dragover.prevent="!disabled && (isDragOver = true)" @dragleave.prevent="!disabled && (isDragOver = false)"
            @drop.prevent="!disabled && handleDrop($event)" @click="!disabled && triggerSelect()">
            <input ref="fileInput" type="file" :accept="accept" :multiple="multiple" class="hidden-input"
                :disabled="disabled" @change="handleInputChange" />

            <div v-if="!hasFiles" class="drag-empty">
                <span class="icon">📤</span>
                <span class="text">{{ text }}</span>
                <span class="sub-text">支持点击或拖拽文件到此处</span>
            </div>

            <div v-else class="file-list">
                <div v-for="(file, idx) in modelValue" :key="idx" class="file-item" @click.stop>
                    <span class="file-name" :title="file.name">{{ file.name }}</span>
                    <span class="file-size">{{ formatSize(file.size) }}</span>
                    <button class="btn-remove" @click.stop="removeFile(idx)">✕</button>
                </div>
                <div class="add-more" @click.stop="triggerSelect">+ 继续添加</div>
            </div>
        </div>

        <!-- 按钮模式 -->
        <div v-else class="upload-btn-wrapper">
            <input ref="fileInput" type="file" :accept="accept" :multiple="multiple" class="hidden-input"
                :disabled="disabled" @change="handleInputChange" />
            <button class="btn-upload" :disabled="disabled" @click="triggerSelect">
                <span class="icon">📤</span>
                <span class="text">{{ text || '选择文件' }}</span>
            </button>

            <!-- 按钮旁的文件列表 -->
            <div v-if="hasFiles" class="inline-file-list">
                <div v-for="(file, idx) in modelValue" :key="idx" class="file-item">
                    <span class="file-name">{{ file.name }}</span>
                    <button class="btn-remove" @click.stop="removeFile(idx)">✕</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
    modelValue: File[]
    multiple?: boolean
    accept?: string
    drag?: boolean
    text?: string
    disabled?: boolean
}>(), {
    modelValue: () => [],
    multiple: false,
    accept: '.xlsx,.xls',
    drag: false,
    text: '选择文件',
    disabled: false,
})

const emit = defineEmits<{
    (e: 'update:modelValue', files: File[]): void
    (e: 'change', files: File[]): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

const hasFiles = computed(() => props.modelValue.length > 0)

function triggerSelect() {
    fileInput.value?.click()
}

function handleInputChange(e: Event) {
    const target = e.target as HTMLInputElement
    if (target.files && target.files.length > 0) {
        processFiles(Array.from(target.files))
    }
    target.value = '' // 允许重复选择同一文件
}

function handleDrop(e: DragEvent) {
    isDragOver.value = false
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        processFiles(Array.from(e.dataTransfer.files))
    }
}

function processFiles(newFiles: File[]) {
    let finalFiles: File[] = []
    if (props.multiple) {
        // 如果是多选，去重并合并
        const existNames = new Set(props.modelValue.map(f => f.name))
        finalFiles = [...props.modelValue]
        for (const f of newFiles) {
            if (!existNames.has(f.name)) {
                finalFiles.push(f)
            }
        }
    } else {
        finalFiles = [newFiles[0]]
    }

    emit('update:modelValue', finalFiles)
    emit('change', finalFiles)
}

function removeFile(index: number) {
    const finalFiles = [...props.modelValue]
    finalFiles.splice(index, 1)
    emit('update:modelValue', finalFiles)
    emit('change', finalFiles)
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
</script>

<style scoped>
.upload-file-container {
    width: 100%;
}

.hidden-input {
    display: none;
}

/* ===== 拖拽模式 ===== */
.upload-drag-area {
    border: 2px dashed #dcdfe6;
    padding: 20px;
    text-align: center;
    background: #fafbfc;
    cursor: pointer;
    transition: all 0.2s;
    min-height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.upload-drag-area:hover,
.upload-drag-area.is-dragover {
    border-color: #2d6cdf;
    background: #f0f5ff;
}

.upload-drag-area.is-disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background: #f5f7fa;
}

.drag-empty {
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: center;
}

.drag-empty .icon {
    font-size: 24px;
}

.drag-empty .text {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
}

.drag-empty .sub-text {
    font-size: 12px;
    color: #909399;
}

/* ===== 文件列表 ===== */
.file-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
}

.file-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    background: #fff;
    border: 1px solid #ebeef5;
    font-size: 13px;
}

.file-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #303133;
}

.file-size {
    color: #909399;
    font-size: 12px;
    margin: 0 12px;
}

.btn-remove {
    border: none;
    background: transparent;
    color: #f56c6c;
    cursor: pointer;
    font-size: 14px;
    padding: 0 4px;
}

.btn-remove:hover {
    color: #be123c;
}

.add-more {
    text-align: center;
    font-size: 13px;
    color: #2d6cdf;
    padding: 6px;
    border: 1px dashed #dcdfe6;
    margin-top: 4px;
}

.add-more:hover {
    border-color: #2d6cdf;
}

/* ===== 按钮模式 ===== */
.upload-btn-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.btn-upload {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 16px;
    background: #fff;
    border: 1px solid #2d6cdf;
    color: #2d6cdf;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}

.btn-upload:hover:not(:disabled) {
    background: #2d6cdf;
    color: #fff;
}

.btn-upload:disabled {
    border-color: #a0b4d8;
    color: #a0b4d8;
    cursor: not-allowed;
}

.inline-file-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 80px;
    overflow-y: auto;
}

.inline-file-list .file-item {
    padding: 4px 8px;
    border: none;
    background: #f5f7fa;
}
</style>