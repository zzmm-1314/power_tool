<template>
    <div class="price-file-picker">
        <!-- 类型 + 节点 -->
        <div class="row">
            <label class="row-label">来源</label>
            <select v-model="kind" class="input select" @change="onKindChange">
                <option v-for="k in kindOptions" :key="k.value" :value="k.value">
                    {{ k.label }}
                </option>
            </select>

            <!-- 节点选择：外部控制或内部 -->
            <template v-if="kind === 'plant-pair'">
                <select v-if="!hideNodePicker" v-model="innerNodeName" class="input select" @change="onNodeChange">
                    <option value="">请选择节点</option>
                    <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
                </select>
                <span v-else-if="nodeName" class="external-node">
                    节点：<strong>{{ nodeName }}</strong>
                </span>
                <span v-else class="external-node warn">
                    （请在上方选择节点）
                </span>
            </template>
        </div>

        <!-- 日期范围 -->
        <div class="row">
            <label class="row-label">日期</label>
            <DateRangeInput :start="startDate" :end="endDate" @update:start="$emit('update:startDate', $event)"
                @update:end="$emit('update:endDate', $event)" />
        </div>

        <!-- 生成按钮 -->
        <div class="row actions">
            <button class="btn-build" :disabled="building" @click="build">
                {{ building ? '生成中...' : '🔧 从数据目录生成' }}
            </button>

            <span v-if="generatedPath" class="generated">
                ✅ {{ shortName }}
                <button class="link" @click="reset">清除</button>
            </span>
        </div>

        <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import { buildPriceFile } from '@/api/modules/settlement'
import { listPlantNodes } from '@/api/modules/nodes'

interface KindOption {
    value: 'unified' | 'plant-pair'
    label: string
}

const props = withDefaults(
    defineProps<{
        modelValue: string
        startDate: string
        endDate: string
        kindOptions?: KindOption[]
        defaultKind?: 'unified' | 'plant-pair'
        /** 外部控制的节点（如果提供则隐藏内部选择） */
        nodeName?: string
        hideNodePicker?: boolean
    }>(),
    {
        kindOptions: () => [
            { value: 'unified', label: '日前统一结算点' },
            { value: 'plant-pair', label: '节点（日前 + 实时）' },
        ],
        defaultKind: 'unified',
        nodeName: '',
        hideNodePicker: false,
    },
)

const emit = defineEmits<{
    (e: 'update:modelValue', v: string): void
    (e: 'update:nodeName', v: string): void
    (e: 'update:startDate', v: string): void
    (e: 'update:endDate', v: string): void
}>()

const kind = ref<'unified' | 'plant-pair'>(props.defaultKind)
const innerNodeName = ref('')
const nodes = ref<string[]>([])
const building = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

const generatedPath = computed(() => props.modelValue)
const shortName = computed(() => {
    const p = generatedPath.value
    if (!p) return ''
    const parts = p.split(/[/\\]/)
    return parts[parts.length - 1] || p
})

/** 实际使用的节点名 */
const effectiveNode = computed(() => {
    return props.hideNodePicker ? props.nodeName || '' : innerNodeName.value
})

watch(
    () => props.defaultKind,
    (v) => {
        kind.value = v
    },
)

async function loadNodes() {
    try {
        const list = await listPlantNodes()
        nodes.value = list.map((n) => n.name)
    } catch {
        nodes.value = []
    }
}

async function build() {
    msg.value = ''
    if (!props.startDate || !props.endDate) {
        msg.value = '请先选择日期范围'
        msgType.value = 'err'
        return
    }
    if (kind.value === 'plant-pair' && !effectiveNode.value) {
        msg.value = '请先选择节点'
        msgType.value = 'err'
        return
    }

    building.value = true
    try {
        const res = await buildPriceFile({
            kind: kind.value,
            nodeName:
                kind.value === 'plant-pair' ? effectiveNode.value : undefined,
            startDate: props.startDate,
            endDate: props.endDate,
        })
        emit('update:modelValue', res.path)
        msg.value = `已生成（共 ${res.dateCount} 天）`
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message
        msgType.value = 'err'
    } finally {
        building.value = false
    }
}

function reset() {
    emit('update:modelValue', '')
    msg.value = ''
}

function onKindChange() {
    emit('update:modelValue', '')
    msg.value = ''
}

function onNodeChange() {
    emit('update:modelValue', '')
    msg.value = ''
    emit('update:nodeName', innerNodeName.value)
}

onMounted(() => {
    if (kind.value === 'plant-pair') {
        loadNodes()
    }
})
</script>

<style scoped>
.price-file-picker {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.row-label {
    width: 40px;
    flex-shrink: 0;
    font-size: 12px;
    color: #909399;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.select {
    min-width: 160px;
}

.external-node {
    font-size: 12px;
    color: #606266;
}

.external-node strong {
    color: #2d6cdf;
}

.external-node.warn {
    color: #e6a23c;
}

.actions {
    justify-content: flex-start;
}

.btn-build {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #2d6cdf;
    border-radius: 4px;
    background: #fff;
    color: #2d6cdf;
    font-size: 13px;
    cursor: pointer;
}

.btn-build:hover:not(:disabled) {
    background: #2d6cdf;
    color: #fff;
}

.btn-build:disabled {
    border-color: #c0c4cc;
    color: #c0c4cc;
    cursor: not-allowed;
}

.generated {
    font-size: 12px;
    color: #67c23a;
    display: flex;
    align-items: center;
    gap: 8px;
}

.link {
    border: none;
    background: transparent;
    color: #f56c6c;
    font-size: 12px;
    cursor: pointer;
    text-decoration: underline;
}

.msg {
    margin: 0;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    display: inline-block;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}
</style>