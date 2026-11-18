<template>
    <div class="app-wrapper">
        <div class="main-container">
            <AppSidebar />
            <div class="content-wrapper">
                <router-view v-slot="{ Component }">
                    <transition name="fade-transform" mode="out-in">
                        <keep-alive :max="5">
                            <component :is="Component" :key="$route.fullPath" />
                        </keep-alive>
                    </transition>
                </router-view>
            </div>
        </div>
        <FloatingSettings />
    </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
import FloatingSettings from '@/components/FloatingSettings.vue'
import { onMounted, onBeforeUnmount } from 'vue'
import { apiUrl } from '@/utils/apiBase'

let heartbeatTimer: number | undefined

// 发送心跳（仅正式环境）
function sendHeartbeat() {
    if (import.meta.env.DEV) return
    fetch(apiUrl('/heartbeat'), { method: 'GET' }).catch(() => { })
}

onMounted(() => {
    sendHeartbeat()
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
}

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