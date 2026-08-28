<template>
  <div class="transport-panel">
    <h3 class="panel-title">🚄 交通出行-Agent</h3>
    <div class="panel-content">
      <template v-if="cards.length">
        <div v-for="card in cards" :key="card.id" class="item-card" :class="{ confirmed: card.confirmed }">
          <template v-if="card.confirmed">
            <div class="card-header">
              <span class="badge confirmed">✅ {{ card.directionLabel }} 已选定</span>
            </div>
            <div class="card-body">
              <div class="info-row"><span class="label">类型:</span><span class="value">{{ card.type }}</span></div>
              <div class="info-row"><span class="label">名称:</span><span class="value highlight">{{ card.name }}</span></div>
              <div class="info-row"><span class="label">座位:</span><span class="value">{{ card.seat || '默认' }}</span></div>
              <div class="info-row"><span class="label">价格:</span><span class="value price">{{ card.price }}元</span></div>
              <div class="info-row"><span class="label">时间:</span><span class="value">{{ card.time }}</span></div>
              <div class="route-info"><span class="from">{{ card.from }}</span><span class="arrow">→</span><span class="to">{{ card.to }}</span></div>
            </div>
          </template>
          <template v-else-if="card.isOption">
            <div class="card-header"><span class="badge option">{{ card.icon }} {{ card.type }}</span><span class="name">{{ card.name }}</span></div>
            <div class="card-body">
              <div class="info-row"><span class="label">时间:</span><span class="value">{{ card.time }}</span></div>
              <div class="route-info"><span class="from">{{ card.from }}</span><span class="arrow">→</span><span class="to">{{ card.to }}</span></div>
              <div v-if="card.isTrain" class="seat-selection">
                <label>座位:</label>
                <select v-model="card.selectedSeat" @change="onSeatChange(card)">
                  <option v-for="seat in card.seats" :key="seat.type" :value="seat.type">{{ seat.type }} - {{ seat.price }}元 (余{{ seat.available }}张)</option>
                </select>
                <button class="confirm-btn" @click="confirmTrain(card)">确认选择</button>
              </div>
              <div v-else class="action-area"><span class="price">{{ card.price }}元</span><button class="confirm-btn" @click="confirmFlight(card)">确认选择</button></div>
            </div>
          </template>
        </div>
      </template>
      <div v-else class="empty-state"><div class="empty-icon">🚄</div><div class="empty-text">等待规划...</div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TransportOption, SelectedTransport } from '@/types'
interface TransportCard { id: string; confirmed: boolean; directionLabel?: string; type?: string; name?: string; seat?: string; price?: number; time?: string; from?: string; to?: string; isOption?: boolean; isTrain?: boolean; icon?: string; seats?: Array<{ type: string; price: number; available: number }>; selectedSeat?: string }
const props = defineProps<{ 
  selectedTransports?: SelectedTransport[]
  transportOptions?: TransportOption[]
  selected?: SelectedTransport[]
  options?: TransportOption[]
}>()
const emit = defineEmits<{ confirm: [message: string] }>()
const cards = computed<TransportCard[]>(() => {
  const list: TransportCard[] = []
  const selectedList = props.selected || props.selectedTransports || []
  const optionsList = props.options || props.transportOptions || []
  
  selectedList.forEach(t => { list.push({ id: 'sel-' + t.name + t.time, confirmed: true, directionLabel: t.direction === 'outbound' ? '去程' : '返程', type: t.type, name: t.name, seat: t.seat_type || '默认', price: t.price, time: t.time, from: t.from, to: t.to }) })
  optionsList.forEach(item => {
    const isTrain = (item.seats && item.seats.length > 0) || (item.type && (item.type.includes('高铁') || item.type.includes('动车')))
    const icon = isTrain ? item.type === '动车' ? '🚅' : item.type === '普快' ? '🚂' : '🚄' : '✈️'
    const card: TransportCard = { id: item.id, confirmed: false, isOption: true, isTrain: !!isTrain, icon, type: item.type, name: item.name, time: item.time, from: item.from, to: item.to, price: item.price, seats: item.seats || [], selectedSeat: undefined }
    if (card.isTrain && card.seats && card.seats.length > 0) { card.selectedSeat = card.seats[0]!.type }
    list.push(card)
  })
  return list
})
const onSeatChange = (card: TransportCard) => {}
const confirmTrain = (card: TransportCard) => { const seatType = card.selectedSeat; const seat = card.seats?.find(s => s.type === seatType); const price = seat ? seat.price : card.price; emit('confirm', `确认交通 ID ${card.id}，名称 ${card.name}，座位 ${seatType}，价格 ${price} 元，时间 ${card.time}，从 ${card.from} 到 ${card.to}`) }
const confirmFlight = (card: TransportCard) => { emit('confirm', `确认交通 ID ${card.id}，名称 ${card.name}，价格 ${card.price} 元，时间 ${card.time}，从 ${card.from} 到 ${card.to}`) }
</script>

<style scoped>
.transport-panel { height: 100%; display: flex; flex-direction: column; background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }
.panel-title { margin: 0; padding: 16px; font-size: 16px; font-weight: 600; color: #2C9E9A; border-bottom: 2px solid #7FDBDA; background: linear-gradient(135deg, #E8F8F7 0%, #F0FCFA 100%); }
.panel-content { flex: 1; overflow-y: auto; padding: 12px; }
.item-card { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 12px; margin-bottom: 12px; transition: all 0.3s ease; }
.item-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.item-card.confirmed { background: #f6ffed; border-color: #b7eb8f; }
.card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.badge.confirmed { background: #7FDBDA; color: white; }
.badge.option { background: #2C9E9A; color: white; }
.name { font-weight: 600; color: #262626; }
.info-row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; }
.label { color: #8c8c8c; }
.value { color: #262626; }
.value.highlight { font-weight: 600; color: #2C9E9A; }
.value.price { font-weight: 600; color: #f5222d; }
.route-info { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 8px; padding: 8px; background: #f0f0f0; border-radius: 4px; font-size: 13px; }
.arrow { color: #2C9E9A; font-weight: 600; }
.seat-selection { margin-top: 12px; padding-top: 12px; border-top: 1px dashed #d9d9d9; }
.seat-selection label { display: block; margin-bottom: 6px; font-size: 13px; color: #595959; }
.seat-selection select { width: 100%; padding: 6px; border: 1px solid #d9d9d9; border-radius: 4px; margin-bottom: 8px; font-size: 13px; }
.action-area { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #d9d9d9; }
.price { font-size: 16px; font-weight: 600; color: #f5222d; }
.confirm-btn { background: #7FDBDA; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.confirm-btn:hover { background: #2C9E9A; transform: translateY(-1px); box-shadow: 0 2px 6px rgba(127, 219, 218, 0.4); }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #bfbfbf; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; }
</style>
