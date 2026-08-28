<template>
  <div class="itinerary-entry">
    <div class="entry-card">
      <div class="entry-icon">🗺️</div>
      <h3 class="entry-title">智能行程规划</h3>
      <p class="entry-desc">基于高德地图的AI行程规划，为您提供最优路线、景点推荐和预算明细</p>
      <a-button type="primary" size="large" @click="goToPlan">
        <template #icon><SearchOutlined /></template>
        开始规划
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { SearchOutlined } from '@ant-design/icons-vue'
const router = useRouter()
const goToPlan = () => router.push('/trip-plan')
</script>

<style scoped>
.itinerary-entry { height: 100%; display: flex; align-items: center; justify-content: center; padding: 20px; }
.entry-card { background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%); border-radius: 24px; padding: 48px; text-align: center; color: white; box-shadow: 0 20px 60px rgba(168, 181, 160, 0.4); max-width: 400px; }
.entry-icon { font-size: 80px; margin-bottom: 24px; }
.entry-title { font-size: 28px; font-weight: 700; margin-bottom: 16px; }
.entry-desc { font-size: 16px; opacity: 0.9; margin-bottom: 32px; line-height: 1.6; }
</style>
