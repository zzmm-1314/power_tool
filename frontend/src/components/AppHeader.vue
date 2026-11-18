<template>
    <header class="app-header">
        <div class="header-left">
            <button class="collapse-btn" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle')">
                <span class="collapse-icon" :class="{ flipped: collapsed }">⏴</span>
            </button>
            <span class="logo">⚡</span>
            <h1 class="title">电力工具助手</h1>
        </div>

        <div class="header-right">
            <button class="settings-btn" @click="showSettings = true" title="全局默认节点设置">
                ⚙️ 节点配置
            </button>
            <span class="app-tag">内部工具</span>
        </div>

        <GlobalSettingsModal v-model="showSettings" />
    </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GlobalSettingsModal from './GlobalSettingsModal.vue'
const props = defineProps<{ collapsed?: boolean }>()
const emit = defineEmits<{ (e: 'toggle'): void }>()
void props
const showSettings = ref(false)
</script>

<style scoped>
.app-header {
    flex: 0 0 var(--header-h);
    height: var(--header-h);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px;
    background: #1f2d3d;
    color: #fff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    z-index: 10;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 10px;
}

.collapse-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: #c0c4cc;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
}

.collapse-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
}

.collapse-icon {
    font-size: 13px;
    transition: transform 0.25s ease;
}

.collapse-icon.flipped {
    transform: rotate(180deg);
}

.logo {
    font-size: 19px;
}

.title {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
    letter-spacing: 1px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 13px;
}

.app-tag {
    padding: 2px 10px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.1);
    color: #c0c4cc;
    font-size: 12px;
}

.settings-btn {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: #c0c4cc;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}

.settings-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: #fff;
}
</style>
