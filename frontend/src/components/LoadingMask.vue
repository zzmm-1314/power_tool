<template>
    <Transition name="fade">
        <div v-if="visible" class="loading-mask">
            <div class="spinner">
                <div class="bounce1"></div>
                <div class="bounce2"></div>
                <div class="bounce3"></div>
            </div>
            <p class="loading-text">{{ text }}</p>
        </div>
    </Transition>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
    visible: boolean
    text?: string
}>(), {
    text: '数据加载中...'
})
</script>

<style scoped>
.loading-mask {
    position: absolute;
    inset: 0;
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(2px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 50;
    border-radius: 8px;
}

.spinner {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
}

.spinner>div {
    width: 12px;
    height: 12px;
    background-color: #2d6cdf;
    border-radius: 100%;
    display: inline-block;
    animation: bouncedelay 1.4s infinite ease-in-out both;
}

.spinner .bounce1 {
    animation-delay: -0.32s;
}

.spinner .bounce2 {
    animation-delay: -0.16s;
}

@keyframes bouncedelay {

    0%,
    80%,
    100% {
        transform: scale(0);
    }

    40% {
        transform: scale(1);
    }
}

.loading-text {
    font-size: 13px;
    color: #606266;
    margin: 0;
    font-weight: 500;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>