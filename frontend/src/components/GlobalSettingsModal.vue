<template>
    <Teleport to="body">
        <div v-if="visible" class="modal-mask" @click.self="close">
            <div class="modal-content">
                <div class="modal-header">
                    <span>全局节点设置</span>
                    <span class="close-btn" @click="close">✕</span>
                </div>
                <div class="modal-body">
                    <!-- ===== 全局默认节点（单节点） ===== -->
                    <div class="section">
                        <div class="section-title">
                            全局默认节点
                            <span class="section-hint">价格、合约、申报系数、结算单等页面默认展示此节点</span>
                        </div>
                        <div class="global-node-row">
                            <SearchableSelect v-model="globalNode" :options="allNodeNames" placeholder="搜索并选择默认节点..."
                                style="flex: 1;" />
                            <button class="btn ghost small" :disabled="!globalNode" @click="globalNode = ''">
                                清空
                            </button>
                        </div>
                        <div v-if="globalNode" class="global-node-current">
                            当前：<strong>{{ globalNode }}</strong>
                        </div>
                    </div>

                    <div class="section-divider"></div>

                    <!-- ===== 快捷选择节点（多选，上传用） ===== -->
                    <div class="section">
                        <div class="section-title">
                            上传时的快捷节点
                            <span class="section-hint">上传数据时可一键勾选</span>
                        </div>

                        <div class="search-box">
                            <input v-model="searchKeyword" type="text" class="search-input" placeholder="搜索所有电厂节点..." />
                        </div>

                        <div class="options-list">
                            <div v-for="node in filteredNodes" :key="node" class="option-item" @click="addNode(node)">
                                {{ node }}
                            </div>
                            <div v-if="!filteredNodes.length" class="empty-option">无匹配节点</div>
                        </div>

                        <div class="selected-area">
                            <div class="selected-title">已选快捷节点（点击右侧叉号移除）</div>
                            <div class="selected-tags">
                                <span v-for="(node, idx) in selectedNodes" :key="idx" class="tag">
                                    {{ node }} <span class="remove-btn" @click="removeNode(idx)">✕</span>
                                </span>
                                <span v-if="!selectedNodes.length" class="empty-selected">暂未选择</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn ghost" @click="close">取消</button>
                    <button class="btn primary" :disabled="saving" @click="save">
                        {{ saving ? '保存中...' : '保存设置' }}
                    </button>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import {
    listPlantNodes,
    fetchPriceCompareDefaults,
    savePriceCompareDefaults,
    fetchGlobalNode,
    saveGlobalNode,
} from '@/api/modules/nodes'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const visible = computed({
    get: () => props.modelValue,
    set: (v) => emit('update:modelValue', v)
})

const allNodes = ref<string[]>([])
const allNodeNames = computed(() => allNodes.value)
const selectedNodes = ref<string[]>([])
const globalNode = ref('')
const searchKeyword = ref('')
const saving = ref(false)

const filteredNodes = computed(() => {
    const kw = searchKeyword.value.trim().toLowerCase()
    return allNodes.value.filter(n =>
        !selectedNodes.value.includes(n) &&
        (!kw || n.toLowerCase().includes(kw))
    )
})

async function loadData() {
    try {
        const [nodes, defaults, gNode] = await Promise.all([
            listPlantNodes(),
            fetchPriceCompareDefaults(),
            fetchGlobalNode(),
        ])
        allNodes.value = nodes.map(n => n.name)
        selectedNodes.value = defaults || []
        globalNode.value = gNode || ''
    } catch (e) {
        console.warn('加载节点数据失败', e)
    }
}

function addNode(node: string) {
    if (!selectedNodes.value.includes(node)) {
        selectedNodes.value.push(node)
    }
    searchKeyword.value = ''
}

function removeNode(idx: number) {
    selectedNodes.value.splice(idx, 1)
}

async function save() {
    saving.value = true
    try {
        await Promise.all([
            savePriceCompareDefaults(selectedNodes.value),
            saveGlobalNode(globalNode.value),
        ])
        alert('节点设置已保存！')
        close()
    } catch (e) {
        alert('保存失败：' + (e as Error).message)
    } finally {
        saving.value = false
    }
}

function close() {
    visible.value = false
}

watch(visible, (v) => {
    if (v) {
        searchKeyword.value = ''
        loadData()
    }
})
</script>

<style scoped>
.modal-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.modal-content {
    width: 560px;
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    display: flex;
    flex-direction: column;
    max-height: 85vh;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #303133;
}

.close-btn {
    cursor: pointer;
    color: #909399;
    font-size: 18px;
}

.close-btn:hover {
    color: #303133;
}

.modal-body {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.section {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.section-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2d3d;
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
}

.section-hint {
    font-size: 12px;
    font-weight: 400;
    color: #909399;
}

.section-divider {
    height: 1px;
    background: #ebeef5;
    margin: 4px 0;
}

.global-node-row {
    display: flex;
    gap: 8px;
    align-items: center;
}

.global-node-current {
    font-size: 12px;
    color: #606266;
    padding: 6px 10px;
    background: #f0f9eb;
    border-radius: 4px;
}

.global-node-current strong {
    color: #67c23a;
}

.search-input {
    width: 100%;
    height: 36px;
    padding: 0 12px;
    box-sizing: border-box;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}

.search-input:focus {
    border-color: #2d6cdf;
}

.options-list {
    border: 1px solid #ebeef5;
    border-radius: 6px;
    max-height: 160px;
    overflow-y: auto;
    background: #fafbfc;
}

.option-item {
    padding: 8px 12px;
    font-size: 13px;
    cursor: pointer;
}

.option-item:hover {
    background: #ecf5ff;
    color: #2d6cdf;
}

.empty-option {
    padding: 16px;
    text-align: center;
    color: #909399;
    font-size: 12px;
}

.selected-area {
    border-top: 1px dashed #ebeef5;
    padding-top: 10px;
}

.selected-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
}

.selected-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 30px;
}

.tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #f0f5ff;
    color: #2d6cdf;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.remove-btn {
    cursor: pointer;
    font-weight: bold;
}

.remove-btn:hover {
    color: #f56c6c;
}

.empty-selected {
    font-size: 12px;
    color: #c0c4cc;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 16px;
}

.btn {
    height: 32px;
    padding: 0 16px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-size: 13px;
}

.btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.btn.primary:hover:not(:disabled) {
    background: #2459b8;
}

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost.small {
    height: 28px;
    padding: 0 12px;
    font-size: 12px;
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>