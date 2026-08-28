import './assets/main.css'
import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import router from './router'
import App from './App.vue'

const app = createApp(App)

app.use(router)
app.use(Antd)

app.mount('#app')    