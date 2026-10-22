<template>
    <PageContainer title="节点编辑">
        <template #extra>
            <button class="btn ghost" @click="openBatchAdd">📋 批量新增</button>
            <button class="btn danger" :disabled="!selectedIds.length" @click="batchDelete">
                删除选中（{{ selectedIds.length }}）
            </button>
            <button class="btn" @click="openAdd">+ 新增节点</button>
        </template>

        <p v-if="errorMsg" class="error-tip">{{ errorMsg }}</p>

        <div class="table-wrap">
            <table class="node-table">
                <thead>
                    <tr>
                        <th style="width: 44px" class="center">
                            <input type="checkbox" :checked="allSelected" :indeterminate="someSelected && !allSelected"
                                @change="toggleAll" />
                        </th>
                        <th style="width: 70px" class="center">ID</th>
                        <th>节点名称</th>
                        <th>描述</th>
                        <th style="width: 170px" class="center">更新时间</th>
                        <th style="width: 130px" class="center">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="n in nodes" :key="n.id" :class="{ selected: selectedIds.includes(n.id) }">
                        <td class="center">
                            <input type="checkbox" :checked="selectedIds.includes(n.id)" @change="toggleOne(n.id)" />
                        </td>
                        <td class="center">{{ n.id }}</td>
                        <td>{{ n.name }}</td>
                        <td class="desc">{{ n.description || '—' }}</td>
                        <td class="center muted">{{ n.updatedAt }}</td>
                        <td class="center">
                            <button class="link-btn" @click="openEdit(n)">编辑</button>
                            <button class="link-btn danger" @click="remove(n)">删除</button>
                        </td>
                    </tr>
                    <tr v-if="!nodes.length">
                        <td colspan="6" class="empty">暂无节点，点击右上角「+ 新增节点」或「📋 批量新增」</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 新增 / 编辑弹窗 -->
        <Teleport to="body">
            <div v-if="modalVisible" class="mask" @click.self="closeModal">
                <div class="modal">
                    <h3 class="modal-title">
                        {{ editing ? '编辑节点' : '新增节点' }}
                    </h3>

                    <div class="form-item">
                        <label>节点名称 <span class="req">*</span></label>
                        <input v-model.trim="form.name" type="text" class="input" placeholder="例如：万华热电"
                            maxlength="64" />
                    </div>

                    <div class="form-item">
                        <label>描述（可选）</label>
                        <textarea v-model.trim="form.description" class="textarea" rows="3"
                            placeholder="用于备注该节点归属、类型等"></textarea>
                    </div>

                    <p v-if="formError" class="error-tip">{{ formError }}</p>

                    <div class="modal-footer">
                        <button class="btn ghost" @click="closeModal">取消</button>
                        <button class="btn" :disabled="saving" @click="submit">
                            {{ saving ? '保存中...' : '保存' }}
                        </button>
                    </div>
                </div>
            </div>
        </Teleport>

        <!-- 批量新增弹窗 -->
        <Teleport to="body">
            <div v-if="batchVisible" class="mask" @click.self="closeBatch">
                <div class="modal wide">
                    <h3 class="modal-title">批量新增节点</h3>

                    <div class="form-item">
                        <label>节点名称 <span class="req">*</span>（每行一个）</label>
                        <textarea v-model="batchText" class="textarea" rows="10"
                            placeholder="万华热电&#10;台州厂#7机组&#10;乌沙山#1机组&#10;..."></textarea>
                        <p class="hint">
                            共 {{ batchLines.length }} 行，其中有效 {{ batchValidCount }} 个。
                            空行、重复、非法字符会被跳过。
                        </p>
                    </div>

                    <div class="form-item">
                        <label>统一描述（可选）</label>
                        <input v-model.trim="batchDescription" type="text" class="input" placeholder="例如：2026 年统调电厂" />
                    </div>

                    <p v-if="batchError" class="error-tip">{{ batchError }}</p>

                    <!-- 结果展示 -->
                    <div v-if="batchResult" class="batch-result">
                        <p class="ok-line">
                            ✓ 成功新增 <strong>{{ batchResult.added.length }}</strong> 个
                        </p>
                        <p v-if="batchResult.skipped.length" class="skip-line">
                            ✗ 跳过 {{ batchResult.skipped.length }} 个：
                        </p>
                        <ul v-if="batchResult.skipped.length" class="skip-list">
                            <li v-for="(s, i) in batchResult.skipped" :key="i">
                                {{ s.name }} —— {{ s.reason }}
                            </li>
                        </ul>
                    </div>

                    <div class="modal-footer">
                        <button class="btn ghost" :disabled="batchSaving" @click="closeBatch">
                            {{ batchResult ? '完成' : '取消' }}
                        </button>
                        <button v-if="!batchResult" class="btn" :disabled="batchSaving || !batchValidCount"
                            @click="submitBatch">
                            {{ batchSaving ? '提交中...' : `提交 ${batchValidCount} 个` }}
                        </button>
                    </div>
                </div>
            </div>
        </Teleport>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import {
    listPlantNodes,
    addPlantNode,
    updatePlantNode,
    deletePlantNode,
    addPlantNodesBatch,
    deletePlantNodesBatch,
    type PlantNode,
    type BatchAddResult,
} from '@/api/modules/nodes'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const nodes = ref<PlantNode[]>([])
const errorMsg = ref('')

/* ==================== 选择 / 批量删除 ==================== */

const selectedIds = ref<number[]>([])

const allSelected = computed(
    () => nodes.value.length > 0 && selectedIds.value.length === nodes.value.length,
)
const someSelected = computed(
    () => selectedIds.value.length > 0 && !allSelected.value,
)

function toggleAll(e: Event) {
    const checked = (e.target as HTMLInputElement).checked
    selectedIds.value = checked ? nodes.value.map((n) => n.id) : []
}

function toggleOne(id: number) {
    const i = selectedIds.value.indexOf(id)
    if (i > -1) selectedIds.value.splice(i, 1)
    else selectedIds.value.push(id)
}

async function batchDelete() {
    if (!selectedIds.value.length) return
    if (
        !confirm(
            `确定删除选中的 ${selectedIds.value.length} 个节点？对应节点 Excel 也会被删除。`,
        )
    ) {
        return
    }
    try {
        await deletePlantNodesBatch(selectedIds.value)
        selectedIds.value = []
        await load()
        appStore.bumpDataVersion()
    } catch (e) {
        errorMsg.value = (e as Error).message
    }
}

/* ==================== 新增 / 编辑单个 ==================== */

const modalVisible = ref(false)
const editing = ref<PlantNode | null>(null)
const saving = ref(false)
const formError = ref('')
const form = reactive({ name: '', description: '' })

function openAdd() {
    editing.value = null
    form.name = ''
    form.description = ''
    formError.value = ''
    modalVisible.value = true
}

function openEdit(n: PlantNode) {
    editing.value = n
    form.name = n.name
    form.description = n.description
    formError.value = ''
    modalVisible.value = true
}

function closeModal() {
    if (saving.value) return
    modalVisible.value = false
}

const INVALID_NAME_CHARS = /[\\/:*?"<>|]/

function validateName(name: string): string {
    if (!name) return '节点名不能为空'
    if (name.length > 64) return '节点名不能超过 64 字符'
    if (INVALID_NAME_CHARS.test(name)) {
        return '节点名不能包含 \\ / : * ? " < > | 字符'
    }
    return ''
}

async function submit() {
    const err = validateName(form.name)
    if (err) {
        formError.value = err
        return
    }
    saving.value = true
    formError.value = ''
    try {
        if (editing.value) {
            await updatePlantNode(editing.value.id, {
                name: form.name,
                description: form.description,
            })
        } else {
            await addPlantNode({
                name: form.name,
                description: form.description,
            })
        }
        modalVisible.value = false
        await load()
        appStore.bumpDataVersion()
    } catch (e) {
        formError.value = (e as Error).message
    } finally {
        saving.value = false
    }
}

/* ==================== 单个删除 ==================== */

async function remove(n: PlantNode) {
    if (!confirm(`确定删除节点「${n.name}」？其节点 Excel 也会被一并删除。`)) return
    try {
        await deletePlantNode(n.id)
        selectedIds.value = selectedIds.value.filter((id) => id !== n.id)
        await load()
        appStore.bumpDataVersion()
    } catch (e) {
        errorMsg.value = (e as Error).message
    }
}

/* ==================== 批量新增 ==================== */

const batchVisible = ref(false)
const batchText = ref('')
const batchDescription = ref('')
const batchSaving = ref(false)
const batchError = ref('')
const batchResult = ref<BatchAddResult | null>(null)

const batchLines = computed(() =>
    batchText.value
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
)

const batchValidCount = computed(() => {
    const existing = new Set(nodes.value.map((n) => n.name))
    return batchLines.value.filter(
        (name) => !INVALID_NAME_CHARS.test(name) && !existing.has(name),
    ).length
})

function openBatchAdd() {
    batchText.value = ''
    batchDescription.value = ''
    batchError.value = ''
    batchResult.value = null
    batchVisible.value = true
}

function closeBatch() {
    if (batchSaving.value) return
    batchVisible.value = false
}

async function submitBatch() {
    if (!batchLines.value.length) {
        batchError.value = '请至少输入一个节点名'
        return
    }

    batchSaving.value = true
    batchError.value = ''
    batchResult.value = null

    try {
        const res = await addPlantNodesBatch({
            names: batchLines.value,
            description: batchDescription.value,
        })
        batchResult.value = res
        await load()
        appStore.bumpDataVersion()
    } catch (e) {
        batchError.value = (e as Error).message
    } finally {
        batchSaving.value = false
    }
}

/* ==================== 加载 ==================== */

async function load() {
    errorMsg.value = ''
    try {
        nodes.value = await listPlantNodes()
        // 清理已被删除的选中项
        const ids = new Set(nodes.value.map((n) => n.id))
        selectedIds.value = selectedIds.value.filter((id) => ids.has(id))
    } catch (e) {
        errorMsg.value = (e as Error).message
    }
}

watch(() => appStore.dataVersion, () => load())
onMounted(load)
</script>

<style scoped>
/* ========== 按钮 ========== */
.btn {
    height: 30px;
    padding: 0 14px;
    border: none;
    border-radius: 4px;
    background: #2d6cdf;
    color: #fff;
    cursor: pointer;
    font-size: 13px;
}

.btn:hover:not(:disabled) {
    background: #2459b8;
}

.btn:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
    color: #2d6cdf;
}

.btn.danger {
    background: #f56c6c;
}

.btn.danger:hover:not(:disabled) {
    background: #e04f4f;
}

.btn.danger:disabled {
    background: #f5b8b8;
    cursor: not-allowed;
}

.error-tip {
    padding: 8px 12px;
    background: #fef0f0;
    color: #f56c6c;
    border-radius: 4px;
    font-size: 12px;
    margin: 0;
}

/* ========== 表格 ========== */
.table-wrap {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    overflow: auto;
}

.node-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.node-table th,
.node-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
}

.node-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    font-size: 12px;
}

.node-table tr.selected td {
    background: #ecf5ff;
}

.node-table .center {
    text-align: center;
}

.node-table .muted {
    color: #909399;
    font-size: 12px;
}

.node-table .desc {
    color: #606266;
}

.node-table .empty {
    text-align: center;
    padding: 40px;
    color: #c0c4cc;
}

.node-table input[type='checkbox'] {
    width: 15px;
    height: 15px;
    cursor: pointer;
    accent-color: #2d6cdf;
}

.link-btn {
    border: none;
    background: transparent;
    color: #2d6cdf;
    font-size: 12px;
    cursor: pointer;
    padding: 2px 6px;
}

.link-btn:hover {
    text-decoration: underline;
}

.link-btn.danger {
    color: #f56c6c;
}

/* ========== 弹窗 ========== */
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
    width: 440px;
    background: #fff;
    border-radius: 8px;
    padding: 24px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

.modal.wide {
    width: 540px;
}

.modal-title {
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
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

.req {
    color: #f56c6c;
}

.hint {
    margin: 2px 0 0;
    font-size: 12px;
    color: #909399;
}

.input,
.textarea {
    padding: 8px 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    font-family: inherit;
}

.textarea {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    resize: vertical;
    min-height: 100px;
}

.input:focus,
.textarea:focus {
    border-color: #2d6cdf;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
}

/* ========== 批量新增结果 ========== */
.batch-result {
    padding: 12px;
    background: #fafbfc;
    border-radius: 6px;
    margin-top: 4px;
}

.ok-line {
    margin: 0 0 6px;
    color: #67c23a;
    font-size: 13px;
}

.skip-line {
    margin: 6px 0 4px;
    color: #e6a23c;
    font-size: 13px;
}

.skip-list {
    margin: 0;
    padding-left: 18px;
    max-height: 140px;
    overflow-y: auto;
    font-size: 12px;
    color: #909399;
}

.skip-list li {
    padding: 2px 0;
}
</style>