import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/global.css'
import './plugins/echarts'        // ← 新增：全局注册 ECharts 组件

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')