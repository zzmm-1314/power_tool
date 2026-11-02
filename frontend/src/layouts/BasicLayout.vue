<template>
    <div class="basic-layout">
        <AppHeader class="layout-header" />

        <div class="layout-body">
            <AppSidebar class="layout-sidebar" :collapsed="appStore.sidebarCollapsed" />

            <main class="layout-content scroll-y">
                <router-view v-slot="{ Component }">
                    <keep-alive>
                        <component :is="Component" />
                    </keep-alive>
                </router-view>
            </main>
        </div>
    </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import { useAppStore } from '@/stores/app'
import { onMounted, onBeforeUnmount } from 'vue'
let heartbeatTimer: number | undefined

const appStore = useAppStore()
// 发送心跳（仅在正式环境生效）
function sendHeartbeat() {
    if (import.meta.env.DEV) return // 开发模式下不发送，避免开发时后端自动退出

    // 使用原生 fetch 避免被 axios 拦截器或超时限制影响
    fetch('/api/heartbeat', { method: 'GET' }).catch(() => {
        // 忽略网络异常，比如后端正在退出
    })
}
onMounted(() => {
    // 立即发一次
    sendHeartbeat()
    // 每 5 秒发一次心跳
    heartbeatTimer = window.setInterval(sendHeartbeat, 5000)
})

onBeforeUnmount(() => {
    if (heartbeatTimer) window.clearInterval(heartbeatTimer)
})
</script>

<style scoped>
.basic-layout {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.layout-header {
    flex: 0 0 56px;
}

.layout-body {
    flex: 1;
    display: flex;
    min-height: 0;
    overflow: hidden;
}

.layout-sidebar {
    flex: 0 0 auto;
}

.layout-content {
    flex: 1;
    min-width: 0;
    padding: 16px;
    background: #f5f7fa;
}
</style>