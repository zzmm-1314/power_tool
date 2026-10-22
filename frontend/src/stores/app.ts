import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    const sidebarCollapsed = ref(false)
    const loading = ref(false)

    /** 上传弹窗可见性 */
    const uploadVisible = ref(false)

    /** 上传弹窗打开时预选的数据类型 key */
    const uploadInitialKey = ref<string>('')

    /** 数据版本号：上传 / 删除临时文件后 +1，各页面 watch 它自动刷新 */
    const dataVersion = ref(0)

    function toggleSidebar() {
        sidebarCollapsed.value = !sidebarCollapsed.value
    }
    function setLoading(val: boolean) {
        loading.value = val
    }
    function openUpload(datasetKey?: string) {
        uploadInitialKey.value = datasetKey || ''
        uploadVisible.value = true
    }
    function closeUpload() {
        uploadVisible.value = false
    }
    function bumpDataVersion() {
        dataVersion.value++
    }

    return {
        sidebarCollapsed,
        loading,
        uploadVisible,
        uploadInitialKey,
        dataVersion,
        toggleSidebar,
        setLoading,
        openUpload,
        closeUpload,
        bumpDataVersion,
    }
})