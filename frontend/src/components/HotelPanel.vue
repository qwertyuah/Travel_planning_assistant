<template>
  <div class="hotel-panel">
    <h3 class="panel-title">🏨 酒店住宿-Agent</h3>
    <div class="panel-content">
      <template v-if="cards.length">
        <div v-for="card in cards" :key="card.id" class="item-card" :class="{ confirmed: card.confirmed }">
          <template v-if="card.confirmed">
            <div class="card-header"><span class="badge confirmed">✅ 已确认预订</span></div>
            <div class="card-body">
              <div class="info-row"><span class="label">酒店:</span><span class="value highlight">{{ card.name }}</span></div>
              <div class="info-row"><span class="label">入住:</span><span class="value">{{ card.check_in }} - {{ card.check_out }}</span></div>
              <div class="info-row"><span class="label">价格:</span><span class="value price">{{ card.price }}元</span></div>
            </div>
          </template>
          <template v-else>
            <div class="card-header"><span class="badge option">🏨 {{ card.star || '未评级' }}</span><span class="name">{{ card.name }}</span></div>
            <div class="card-body">
              <div class="info-row"><span class="label">📍 地址:</span><span class="value">{{ card.address }} ({{ card.business_circle || '未知商圈' }})</span></div>
              <div class="info-row"><span class="label">🏠 房型:</span><span class="value">{{ card.room_type }} | 🪟 窗户: {{ card.window_type || '未知' }}</span></div>
              <div class="info-row"><span class="label">⭐ 评分:</span><span class="value">{{ card.score }}</span></div>
              <div class="action-area"><span class="price">{{ card.price }}元起</span><button class="confirm-btn" @click="confirmHotel(card)">确认选择</button></div>
            </div>
          </template>
        </div>
      </template>
      <div v-else class="empty-state"><div class="empty-icon">🏨</div><div class="empty-text">等待规划...</div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HotelOption, SelectedHotel } from '@/types'
interface HotelCard { id: string; confirmed: boolean; name?: string; check_in?: string; check_out?: string; price?: number; type?: string; star?: string; address?: string; business_circle?: string; room_type?: string; window_type?: string; score?: string }
const props = defineProps<{
  selectedHotels?: SelectedHotel[]
  hotelOptions?: HotelOption[]
  selected?: SelectedHotel[]
  options?: HotelOption[]
}>()
const emit = defineEmits<{ confirm: [message: string] }>()
const cards = computed<HotelCard[]>(() => {
  const list: HotelCard[] = []
  const selectedList = props.selected || props.selectedHotels || []
  const optionsList = props.options || props.hotelOptions || []
  
  selectedList.forEach((h, idx) => { list.push({ id: 'sel-' + h.name + idx, confirmed: true, name: h.name, check_in: h.check_in, check_out: h.check_out, price: h.price, type: h.type }) })
  optionsList.forEach(item => { list.push({ id: item.id, confirmed: false, name: item.name, star: item.star, address: item.address, business_circle: item.business_circle, room_type: item.room_type, window_type: item.window_type, score: item.score, price: item.price }) })
  return list
})
const confirmHotel = (card: HotelCard) => { emit('confirm', `确认酒店 ID ${card.id}，名称 ${card.name}，价格 ${card.price}`) }
</script>

<style scoped>
.hotel-panel { height: 100%; display: flex; flex-direction: column; background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }
.panel-title { margin: 0; padding: 16px; font-size: 16px; font-weight: 600; color: #7B6B9C; border-bottom: 2px solid #87CEEB; background: linear-gradient(135deg, #F3F1F9 0%, #F9F7FC 100%); }
.panel-content { flex: 1; overflow-y: auto; padding: 12px; }
.item-card { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 12px; margin-bottom: 12px; transition: all 0.3s ease; }
.item-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.item-card.confirmed { background: #f6ffed; border-color: #b7eb8f; }
.card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.badge.confirmed { background: #87CEEB; color: white; }
.badge.option { background: #A8A4FF; color: white; }
.name { font-weight: 600; color: #262626; }
.info-row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; }
.label { color: #8c8c8c; }
.value { color: #262626; }
.value.highlight { font-weight: 600; color: #7B6B9C; }
.value.price { font-weight: 600; color: #f5222d; }
.action-area { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #d9d9d9; }
.price { font-size: 16px; font-weight: 600; color: #f5222d; }
.confirm-btn { background: #87CEEB; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.confirm-btn:hover { background: #A8A4FF; transform: translateY(-1px); box-shadow: 0 2px 6px rgba(199, 206, 234, 0.4); }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #bfbfbf; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; }
</style>
