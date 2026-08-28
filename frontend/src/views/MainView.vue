<template>
  <div class="main-view">
    <header class="page-header">
      <h1>🌍 智能出行 - 旅游个人助手</h1>
      
    </header>

    <!-- 悬浮聊天对话框 -->
    <DraggableChat ref="draggableChatRef" :ws="ws" :is-submitting="isSubmitting" />

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：交通 + 酒店 (2/5) -->
      <div class="left-section">
        <div class="section-header">
          <h2>出行服务</h2>
        </div>
        <div class="left-panels">
          <div class="panel-wrapper transport-wrapper">
            <TransportPanel
              :selected-transports="transportState.selected"
              :transport-options="transportState.options"
              @confirm="confirmTransport"
            />
          </div>
          <div class="panel-wrapper hotel-wrapper">
            <HotelPanel
              :selected-hotels="hotelState.selected"
              :hotel-options="hotelState.options"
              @confirm="confirmHotel"
            />
          </div>
        </div>
      </div>

      <!-- 右侧：行程规划 (3/5) -->
      <div class="right-section">
        <div class="section-header">
          <h2>智能行程规划</h2>
        </div>
        <div class="itinerary-panel">
          <!-- 状态1: 初始化显示入口 -->
          <div v-if="currentView === 'entry'" class="itinerary-entrance">
            <div class="entrance-card">
              <div class="entrance-icon">🗺️</div>
              <h3 class="entrance-title">智能行程规划</h3>
              <p class="entrance-desc">
                基于高德地图的AI行程规划<br/>
                自动推荐景点、酒店、餐饮
              </p>
              <a-button type="primary" size="large" @click="showForm">
                开始规划
              </a-button>
            </div>
          </div>

          <!-- 状态2: 显示表单 -->
          <div v-else-if="currentView === 'form'" class="embedded-form">
            <TripPlanFormEmbedded ref="tripPlanFormRef" :is-submitting="isSubmitting" @submit="handleFormSubmit" @cancel="showEntry" />
          </div>

          <!-- 状态3: 显示结果 -->
          <div v-else-if="currentView === 'result'" class="embedded-result">
            <TripPlanResultEmbedded 
              :response="itineraryResponse"
              :selected-transports="transportState.selected"
              :selected-hotels="hotelState.selected"
              @back="showEntry"
              @retry="showForm"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import DraggableChat from '@/components/DraggableChat.vue'
import TransportPanel from '@/components/TransportPanel.vue'
import HotelPanel from '@/components/HotelPanel.vue'
import TripPlanFormEmbedded from '@/components/TripPlanFormEmbedded.vue'
import TripPlanResultEmbedded from '@/components/TripPlanResultEmbedded.vue'
import { itineraryApi } from '@/services/api'
import type {
  SelectedTransport,
  TransportOption,
  SelectedHotel,
  HotelOption,
  ItineraryResponse,
  TripRequest,
  ItineraryState,
  TripPlan
} from '@/types'

const draggableChatRef = ref<InstanceType<typeof DraggableChat> | null>(null)
const tripPlanFormRef = ref<InstanceType<typeof TripPlanFormEmbedded> | null>(null)

// 全局提交锁 - 防止重复提交
const isSubmitting = ref(false)

// 当前视图状态: entry | form | result
const currentView = ref<'entry' | 'form' | 'result'>('entry')
const itineraryResponse = ref<ItineraryResponse | null>(null)

// WebSocket 状态 - 使用 ref 代替 reactive 确保响应式
const transportState = ref({
  selected: [] as SelectedTransport[],
  options: [] as TransportOption[]
})

const hotelState = ref({
  selected: [] as SelectedHotel[],
  options: [] as HotelOption[]
})

// 行程规划状态（用于聊天模式）
const itineraryState = ref<ItineraryState | null>(null)

// WebSocket 实例 - 使用 ref 确保响应式
const ws = ref<WebSocket | null>(null)

// 连接 WebSocket
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.host}/ws`
  ws.value = new WebSocket(url)

  ws.value.onopen = () => {
    console.log('WebSocket 已连接')
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'state_update') {
      const state = data.state
      transportState.value.selected = state.selected_transports || []
      transportState.value.options = state.transport_options || []
      hotelState.value.selected = state.selected_hotels || []
      hotelState.value.options = state.hotel_options || []
      
      // 处理行程规划数据（聊天模式）
      if (state.itinerary) {
        itineraryState.value = state.itinerary
        // 自动跳转到结果页
        const source = state.itinerary_source || 'amap'
        
        let response: ItineraryResponse
        if (source === 'amap') {
          // 高德模式：itinerary 是结构化数据
          response = {
            mode: 'chat',
            source: 'amap',
            data: state.itinerary as TripPlan,
            message: '行程规划完成'
          }
        } else {
          // 百度模式：itinerary 可能是字符串或包含 raw_text 的对象
          const itinerary = state.itinerary
          let rawText: string
          
          if (typeof itinerary === 'string') {
            rawText = itinerary
          } else if (typeof itinerary === 'object' && itinerary !== null) {
            // 如果是对象，尝试获取 raw_text 字段，否则转为 JSON 字符串
            rawText = (itinerary as any).raw_text || JSON.stringify(itinerary, null, 2)
          } else {
            rawText = String(itinerary)
          }
          
          response = {
            mode: 'chat',
            source: 'baidu',
            data: undefined,
            raw_data: { raw_text: rawText },
            message: '行程规划完成（百度搜索模式）'
          }
        }
        
        itineraryResponse.value = response
        currentView.value = 'result'
      }
    }
  }

  ws.value.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }

  ws.value.onclose = () => {
    console.log('WebSocket 已断开')
  }
}

// 视图切换
const showEntry = () => {
  currentView.value = 'entry'
  itineraryResponse.value = null
}

const showForm = () => {
  currentView.value = 'form'
}

// 表单提交处理
const handleFormSubmit = async (formData: TripRequest) => {
  // 防止重复提交
  if (isSubmitting.value) {
    message.warning('正在处理中，请稍候...')
    return
  }
  
  isSubmitting.value = true
  
  try {
    const response = await itineraryApi.formPlan(formData)
    
    if (response.source === 'error') {
      tripPlanFormRef.value?.failLoading('行程规划失败，请重试')
      return
    }
    
    itineraryResponse.value = response
    
    // 通知表单完成
    tripPlanFormRef.value?.completeLoading()
    
    // 延迟切换视图，让用户看到完成状态
    setTimeout(() => {
      currentView.value = 'result'
      
      if (response.source === 'baidu') {
        message.info('高德地图服务暂不可用，已切换至百度搜索模式')
      } else {
        message.success('行程规划成功！')
      }
    }, 800)
    
  } catch (error: any) {
    console.error('提交失败:', error)
    
    let errorMsg = '行程规划失败，请检查网络后重试'
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      errorMsg = '请求超时，请稍后重试'
    } else if (error.response?.status === 500) {
      errorMsg = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMsg = error.message
    }
    
    tripPlanFormRef.value?.failLoading(errorMsg)
  } finally {
    isSubmitting.value = false
  }
}

// 确认交通
const confirmTransport = (message: string) => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
  ws.value.send(message)
  // 在聊天框中显示确认信息
  if (draggableChatRef.value) {
    draggableChatRef.value.addMessage(message, 'user')
  }
}

const confirmHotel = (message: string) => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
  ws.value.send(message)
  // 在聊天框中显示确认信息
  if (draggableChatRef.value) {
    draggableChatRef.value.addMessage(message, 'user')
  }
}

onMounted(() => {
  connectWebSocket()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  overflow: hidden;
}

.page-header {
  text-align: center;
  padding: 12px 0;
  background: linear-gradient(135deg, #A8D8EA 0%, #87CEEB 100%);
  color: white;
  flex-shrink: 0;
}

.page-header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 300;
  letter-spacing: 2px;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

/* 左侧区域 (2/5) */
.left-section {
  width: 40%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.section-header {
  padding-bottom: 10px;
  border-bottom: 2px solid #e8e8e8;
}

.section-header h2 {
  margin: 0;
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.left-panels {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.panel-wrapper {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 12px;
  overflow: hidden;
}

/* 交通和酒店各占50% */
.transport-wrapper,
.hotel-wrapper {
  flex: 1;
}

/* 右侧区域 (3/5) */
.right-section {
  width: 60%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.itinerary-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.itinerary-entrance {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.entrance-card {
  text-align: center;
  padding: 30px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
  border-radius: 12px;
  border: 2px dashed #A8D8EA;
  max-width: 350px;
}

.entrance-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.entrance-title {
  font-size: 20px;
  color: #333;
  margin: 0 0 10px 0;
}

.entrance-desc {
  color: #666;
  margin-bottom: 20px;
  line-height: 1.5;
  font-size: 14px;
}

.embedded-form,
.embedded-result {
  flex: 1;
  overflow: auto;
}
</style>
