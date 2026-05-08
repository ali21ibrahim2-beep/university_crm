// main.ts — Vue app bootstrap. Registers Pinia + Vue Router,
// imports global styles, mounts into #app from index.html.
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'

// Pinia before router: router guards read the auth store.
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
