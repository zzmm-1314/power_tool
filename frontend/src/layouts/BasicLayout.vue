<template>
    <div class="app-wrapper">
        <AppHeader :collapsed="isCollapsed" @toggle="appStore.toggleSidebar()" />
        <div class="main-container">
            <AppSidebar :collapsed="isCollapsed" />
            <div class="content-wrapper">
                <!-- 新增过渡动画 -->
                <router-view v-slot="{ Component }">
                    <transition name="fade-transform" mode="out-in">
                        <keep-alive :max="5">
                            <component :is="Component" :key="$route.fullPath" />
                        </keep-alive>
                    </transition>
                </router-view>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import { useAppStore } from '@/stores/app'
import { onMounted, onBeforeUnmount, computed } from 'vue'
let heartbeatTimer: number | undefined

const appStore = useAppStore()
const isCollapsed = computed(() => appStore.sidebarCollapsed)

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
.app-wrapper {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.main-container {
    flex: 1;
    display: flex;
    overflow: hidden;
    min-height: 0;
}

.content-wrapper {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    padding: 16px 20px;
    /* 给所有页面统一边距 */
}

/* 路由切换过渡：类名由 transition name 动态生成，非死样式 */
.fade-transform-enter-active,
.fade-transform-leave-active {
    transition: all 0.3s ease;
}

.fade-transform-enter-from {
    opacity: 0;
    transform: translateY(10px);
}

.fade-transform-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}
</style>