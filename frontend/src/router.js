import { createRouter, createWebHistory } from 'vue-router'
import ConsoleView from './views/ConsoleView.vue'
import RespondView from './views/RespondView.vue'
import ReportView from './views/ReportView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ConsoleView },
    { path: '/r/:path', component: RespondView },
    { path: '/report/:sid', component: ReportView },
  ],
})
