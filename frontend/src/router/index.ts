import { createRouter, createWebHistory } from 'vue-router'
import MainView from '@/views/MainView.vue'
import TripPlanForm from '@/views/TripPlanForm.vue'
import TripPlanResult from '@/views/TripPlanResult.vue'

const routes = [
  {
    path: '/',
    name: 'Main',
    component: MainView
  },
  {
    path: '/trip-plan',
    name: 'TripPlanForm',
    component: TripPlanForm
  },
  {
    path: '/trip-result',
    name: 'TripPlanResult',
    component: TripPlanResult
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
