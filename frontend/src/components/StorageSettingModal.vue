<template>
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="visible" class="mask" @click.self="close">
                <div class="modal">
                    <button class="close-btn" @click="close">×</button>

                    <div class="modal-header">
                        <h2 class="modal-title">⚙ 存储目录设置</h2>
                        <p class="modal-subtitle">
                            切换临时数据根目录，便于备份 / 数据迁移
                        </p>
                    </div>

                    <div class="modal-body">
                        <div class="form-item">
                            <label>当前目录</label>
                            <div class="current-path">{{ currentPath || '加载中...' }}</div>
                        </div>

                        <div class="form-item">
                            <label>新目录（服务器上的绝对路径）</label>
                            <input v-model.trim="newPath" type="text" class="input"
                                placeholder="例如：D:/power-tool/temp_data 或 /data/power-tool/temp" />
                            <p class="hint">
                                若目录不存在，后端会自动创建（要求父目录存在且可写）。
                            </p>
                        </div>

                        <div class="form-item">
                            <label class="checkbox-label">
                                <input v-model="migrate" type="checkbox" />
                                <span>切换时迁移旧目录文件（复制，不删除原文件）</span>
                            </label>
                        </div>

                        <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
                    </div>

                    <div class="modal-footer">
                        <button class="btn ghost" :disabled="saving" @click="close">
                            取消
                        </button>
                        <button class="btn" :disabled="saving || !newPath || newPath === currentPath" @click="submit">
                            {{ saving ? '切换中...' : '确认切换' }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
    getStorageConfig,
    updateStorageConfig,
} from '@/api/modules/tempData'
import { useAppStore } from '@/stores/app'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
    (e: 'update:modelValue', v: boolean): void
    (e: 'changed'): void
}>()

const appStore = useAppStore()

const visible = ref(props.modelValue)
const currentPath = ref('')
const newPath = ref('')
const migrate = ref(true)
const saving = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

watch(
    () => props.modelValue,
    async (v) => {
        visible.value = v
        if (v) await loadCurrent()
    },
)
watch(visible, (v) => emit('update:modelValue', v))

function close() {
    if (saving.value) return
    visible.value = false
}

async function loadCurrent() {
    msg.value = ''
    try {
        const res = await getStorageConfig()
        currentPath.value = res.tempDir
        newPath.value = res.tempDir
    } catch (e) {
        currentPath.value = ''
        newPath.value = ''
        msg.value = (e as Error).message || '获取当前目录失败'
        msgType.value = 'err'
    }
}

async function submit() {
    if (!newPath.value || newPath.value === currentPath.value) return

    saving.value = true
    msg.value = ''

    try {
        const res = await updateStorageConfig({
            tempDir: newPath.value,
            migrate: migrate.value,
        })

        msg.value =
            `目录已切换至：${res.newPath}` +
            (migrate.value
                ? `（迁移 ${res.migrated} 个文件，跳过 ${res.skipped} 个）`
                : '')
        msgType.value = 'ok'

        currentPath.value = res.newPath
        appStore.bumpDataVersion()
        emit('changed')
    } catch (e) {
        msg.value = (e as Error).message || '切换失败'
        msgType.value = 'err'
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
.mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.modal {
    position: relative;
    width: 540px;
    max-width: 92vw;
    max-height: 88vh;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    overflow: hidden;
}

.close-btn {
    position: absolute;
    top: 8px;
    right: 14px;
    border: none;
    background: transparent;
    font-size: 24px;
    color: #909399;
    cursor: pointer;
    line-height: 1;
    z-index: 1;
}

.close-btn:hover {
    color: #303133;
}

.modal-header {
    padding: 20px 24px 12px;
    border-bottom: 1px solid #f0f2f5;
}

.modal-title {
    margin: 0 0 4px;
    font-size: 17px;
    font-weight: 600;
    color: #1f2d3d;
}

.modal-subtitle {
    margin: 0;
    font-size: 12px;
    color: #909399;
}

.modal-body {
    flex: 1;
    padding: 16px 24px;
    overflow-y: auto;
}

.form-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;
}

.form-item label {
    font-size: 13px;
    color: #606266;
}

.current-path {
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 4px;
    font-size: 13px;
    color: #303133;
    font-family: 'Consolas', 'Monaco', monospace;
    word-break: break-all;
}

.input {
    height: 34px;
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

.hint {
    margin: 2px 0 0;
    font-size: 12px;
    color: #909399;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #606266;
    cursor: pointer;
}

.msg {
    margin: 0;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    word-break: break-all;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px 24px;
    border-top: 1px solid #f0f2f5;
    background: #fafbfc;
}

.btn {
    height: 34px;
    padding: 0 18px;
    border: none;
    border-radius: 4px;
    background: #2d6cdf;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
}

.btn:hover:not(:disabled) {
    background: #2459b8;
}

.btn:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.btn.ghost {
    background: transparent;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>