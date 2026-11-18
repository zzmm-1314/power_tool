<template>
    <div class="searchable-select" ref="containerRef">
        <!-- 直接就是输入框 -->
        <input ref="inputRef" v-model="keyword" type="text" class="input" :placeholder="placeholder" @focus="onFocus"
            @input="onInput" @blur="onBlur" @keydown.enter="onEnter" />

        <!-- 下拉提示面板 -->
        <div v-show="isOpen" class="dropdown-panel">
            <div class="options-list">
                <div v-for="opt in filteredOptions" :key="opt" class="option-item"
                    :class="{ active: opt === modelValue }" @mousedown.prevent="select(opt)">
                    {{ opt }}
                </div>
                <div v-if="!filteredOptions.length" class="empty-option">无匹配选项</div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = withDefaults(defineProps<{
    modelValue: string
    options: string[]
    placeholder?: string
}>(), {
    placeholder: '请输入关键字搜索节点…'
})

const emit = defineEmits<{
    (e: 'update:modelValue', v: string): void
    (e: 'change', v: string): void
}>()

const isOpen = ref(false)
const keyword = ref('')
const containerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

// 过滤逻辑：根据输入词实时匹配
const filteredOptions = computed(() => {
    const kw = keyword.value.trim().toLowerCase()
    if (!kw) return props.options
    return props.options.filter(o => o.toLowerCase().includes(kw))
})

// 监听外部值的改变，同步更新输入框里的文本
watch(() => props.modelValue, (val) => {
    keyword.value = val || ''
}, { immediate: true })

// 聚焦：展开下拉框
function onFocus() {
    isOpen.value = true
}

// 输入：实时过滤
function onInput() {
    isOpen.value = true
    // 如果用户把输入框清空了，认为想取消选择，抛出空值
    if (!keyword.value.trim()) {
        emit('update:modelValue', '')
    }
}

// 失焦：如果输入的内容不包含在已有选项里，自动回退到上一次选中的值
function onBlur() {
    setTimeout(() => {
        isOpen.value = false
        if (!props.options.includes(keyword.value)) {
            keyword.value = props.modelValue || ''
        }
    }, 150)
}

// 按下回车：直接选中匹配列表的第一个
function onEnter() {
    if (filteredOptions.value.length > 0) {
        select(filteredOptions.value[0])
    }
}

// 选择某一项
function select(opt: string) {
    keyword.value = opt
    emit('update:modelValue', opt)
    emit('change', opt)
    isOpen.value = false
    inputRef.value?.blur()
}

// 点击组件外部自动收起面板
function handleClickOutside(e: MouseEvent) {
    if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
        isOpen.value = false
    }
}

onMounted(() => {
    document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.searchable-select {
    position: relative;
    width: 100%;
    min-width: 160px;
}


.input:focus {
    border-color: #2d6cdf;
    box-shadow: 0 0 0 3px rgba(45, 108, 223, 0.1);
}

.input::placeholder {
    color: #a8abb2;
}

/* 下拉面板 */
.dropdown-panel {
    position: absolute;
    top: 36px;
    left: 0;
    width: 100%;
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 100;
    overflow: hidden;
}

/* 选项列表（限制高度约为 5 个选项） */
.options-list {
    max-height: 165px;
    /* 33px * 5 = 165px */
    overflow-y: auto;
}

/* 滚动条美化 */
.options-list::-webkit-scrollbar {
    width: 6px;
}

.options-list::-webkit-scrollbar-thumb {
    background: #dcdfe6;
    border-radius: 6px;
}

.options-list::-webkit-scrollbar-thumb:hover {
    background: #c0c4cc;
}

.option-item {
    height: 33px;
    line-height: 33px;
    padding: 0 12px;
    cursor: pointer;
    color: #606266;
    transition: background 0.1s;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.option-item:hover {
    background: #f5f7fa;
}

.option-item.active {
    color: #2d6cdf;
    font-weight: 600;
    background: #ecf5ff;
}

.empty-option {
    padding: 12px;
    text-align: center;
    color: #909399;
    font-size: 12px;
}
</style>