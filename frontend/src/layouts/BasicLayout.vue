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

const appStore = useAppStore()
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