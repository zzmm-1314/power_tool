<template>
    <header class="app-header">
        <div class="header-left">
            <span class="logo">⚡</span>
            <h1 class="title">电力工具助手</h1>
        </div>

        <div class="header-right">
            <span class="username">未登录</span>
        </div>
    </header>
</template>

<script setup lang="ts"></script>

<style scoped>
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    background: #1f2d3d;
    color: #fff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    z-index: 10;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo {
    font-size: 20px;
}

.title {
    margin: 0;
    font-size: 17px;
    font-weight: 500;
    letter-spacing: 1px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 13px;
}

.username {
    color: #c0c4cc;
}
</style>