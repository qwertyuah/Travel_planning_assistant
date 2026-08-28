<template>
  <div
    ref="chatContainer"
    class="draggable-chat"
    :class="{ 
      minimized: isMinimized, 
      expanded: isExpanded,
      'resizing-x': isResizingX,
      'resizing-y': isResizingY 
    }"
    :style="containerStyle"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <!-- 调整大小手柄 - 右边缘 -->
    <div 
      class="resize-handle resize-handle-right"
      @mousedown="startResizeX($event, 'right')"
    ></div>
    
    <!-- 调整大小手柄 - 下边缘 -->
    <div 
      class="resize-handle resize-handle-bottom"
      @mousedown="startResizeY($event, 'bottom')"
    ></div>
    
    <!-- 调整大小手柄 - 右下角 -->
    <div 
      class="resize-handle resize-handle-corner"
      @mousedown="startResizeXY($event)"
    ></div>

    <!-- 标题栏 - 可拖拽 -->
    <div
      class="chat-header"
      @mousedown="startDrag"
      @touchstart="startDrag"
    >
      <span class="header-title">💬 智能助手</span>
      <div class="header-actions">
        <button class="action-btn" @click.stop="toggleMinimize">
          {{ isMinimized ? '□' : '−' }}
        </button>
        <button class="action-btn" @click.stop="toggleExpand">
          {{ isExpanded ? '⤓' : '⤢' }}
        </button>
      </div>
    </div>

    <!-- 聊天内容区 -->
    <div v-show="!isMinimized" class="chat-body">
      <div ref="chatLog" class="chat-messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['msg', msg.sender]"
        >
          {{ msg.text }}
        </div>
      </div>
      <div class="input-area">
        <input
          v-model="userInput"
          placeholder="请输入您的需求..."
          @keypress.enter="sendMessage"
          :disabled="isSubmitting"
        />
        <button @click="sendMessage" :disabled="isSubmitting">
          {{ isSubmitting ? '发送中...' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'

// Props
const props = defineProps<{
  ws?: WebSocket | null
  isSubmitting?: boolean
}>()

// 聊天消息
const messages = ref<Array<{ text: string; sender: 'user' | 'ai' }>>([])
const userInput = ref('')
const chatLog = ref<HTMLElement | null>(null)

// 拖拽相关
const chatContainer = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const position = reactive({ x: 0, y: 0 })
const dragOffset = reactive({ x: 0, y: 0 })

// 调整大小相关
const containerSize = reactive({ width: 350, height: 500 })
const isResizingX = ref(false)
const isResizingY = ref(false)
const resizeStartX = ref(0)
const resizeStartY = ref(0)
const resizeStartWidth = ref(0)
const resizeStartHeight = ref(0)

// 窗口状态
const isMinimized = ref(false)
const isExpanded = ref(false)

// 计算容器样式
const containerStyle = computed(() => ({
  left: position.x === 0 ? 'auto' : `${position.x}px`,
  right: position.x === 0 ? '20px' : 'auto',
  top: position.y === 0 ? 'auto' : `${position.y}px`,
  bottom: position.y === 0 ? '20px' : 'auto',
  width: `${containerSize.width}px`,
  height: isMinimized.value ? '50px' : isExpanded.value ? '70vh' : `${containerSize.height}px`
}))

// 监听 WebSocket 消息
watch(() => props.ws, (newWs) => {
  if (newWs) {
    // 监听消息
    const originalOnMessage = newWs.onmessage
    newWs.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'chat') {
        addMessage(data.content, 'ai')
      }
      // 调用原始处理函数
      if (originalOnMessage) {
        originalOnMessage.call(newWs, event)
      }
    }
  }
}, { immediate: true })

// 拖拽开始
const startDrag = (e: MouseEvent | TouchEvent) => {
  if (isMinimized.value) return
  
  isDragging.value = true
  const touchE = e as TouchEvent
  const mouseE = e as MouseEvent
  const clientX = 'touches' in e && touchE.touches.length > 0 ? touchE.touches[0]!.clientX : mouseE.clientX
  const clientY = 'touches' in e && touchE.touches.length > 0 ? touchE.touches[0]!.clientY : mouseE.clientY
  
  const rect = chatContainer.value?.getBoundingClientRect()
  if (rect) {
    dragOffset.x = clientX - rect.left
    dragOffset.y = clientY - rect.top
  }

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

// 拖拽中
const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return
  
  const touchE = e as TouchEvent
  const mouseE = e as MouseEvent
  const clientX = 'touches' in e && touchE.touches.length > 0 ? touchE.touches[0]!.clientX : mouseE.clientX
  const clientY = 'touches' in e && touchE.touches.length > 0 ? touchE.touches[0]!.clientY : mouseE.clientY
  
  position.x = clientX - dragOffset.x
  position.y = clientY - dragOffset.y
  
  // 边界限制
  const maxX = window.innerWidth - (chatContainer.value?.offsetWidth || 350)
  const maxY = window.innerHeight - (chatContainer.value?.offsetHeight || 500)
  
  position.x = Math.max(0, Math.min(position.x, maxX))
  position.y = Math.max(0, Math.min(position.y, maxY))
}

// 拖拽结束
const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// 水平调整大小开始
const startResizeX = (e: MouseEvent, direction: 'left' | 'right') => {
  e.stopPropagation()
  isResizingX.value = true
  resizeStartX.value = e.clientX
  resizeStartWidth.value = containerSize.width
  
  document.addEventListener('mousemove', onResizeX)
  document.addEventListener('mouseup', stopResizeX)
}

// 水平调整中
const onResizeX = (e: MouseEvent) => {
  if (!isResizingX.value) return
  const delta = e.clientX - resizeStartX.value
  const newWidth = Math.max(250, Math.min(800, resizeStartWidth.value + delta))
  containerSize.width = newWidth
}

// 水平调整结束
const stopResizeX = () => {
  isResizingX.value = false
  document.removeEventListener('mousemove', onResizeX)
  document.removeEventListener('mouseup', stopResizeX)
}

// 垂直调整大小开始
const startResizeY = (e: MouseEvent, direction: 'top' | 'bottom') => {
  e.stopPropagation()
  isResizingY.value = true
  resizeStartY.value = e.clientY
  resizeStartHeight.value = containerSize.height
  
  document.addEventListener('mousemove', onResizeY)
  document.addEventListener('mouseup', stopResizeY)
}

// 垂直调整中
const onResizeY = (e: MouseEvent) => {
  if (!isResizingY.value) return
  const delta = e.clientY - resizeStartY.value
  const newHeight = Math.max(300, Math.min(900, resizeStartHeight.value + delta))
  containerSize.height = newHeight
}

// 垂直调整结束
const stopResizeY = () => {
  isResizingY.value = false
  document.removeEventListener('mousemove', onResizeY)
  document.removeEventListener('mouseup', stopResizeY)
}

// 同时调整大小开始
const startResizeXY = (e: MouseEvent) => {
  e.stopPropagation()
  isResizingX.value = true
  isResizingY.value = true
  resizeStartX.value = e.clientX
  resizeStartY.value = e.clientY
  resizeStartWidth.value = containerSize.width
  resizeStartHeight.value = containerSize.height
  
  document.addEventListener('mousemove', onResizeXY)
  document.addEventListener('mouseup', stopResizeXY)
}

// 同时调整中
const onResizeXY = (e: MouseEvent) => {
  if (isResizingX.value) {
    const deltaX = e.clientX - resizeStartX.value
    containerSize.width = Math.max(250, Math.min(800, resizeStartWidth.value + deltaX))
  }
  if (isResizingY.value) {
    const deltaY = e.clientY - resizeStartY.value
    containerSize.height = Math.max(300, Math.min(900, resizeStartHeight.value + deltaY))
  }
}

// 同时调整结束
const stopResizeXY = () => {
  isResizingX.value = false
  isResizingY.value = false
  document.removeEventListener('mousemove', onResizeXY)
  document.removeEventListener('mouseup', stopResizeXY)
}

// 鼠标移动处理（用于改变光标样式）
const handleMouseMove = (e: MouseEvent) => {
  if (isResizingX.value || isResizingY.value || isDragging.value) return
  
  const rect = chatContainer.value?.getBoundingClientRect()
  if (!rect) return
  
  const isRightEdge = e.clientX >= rect.right - 10
  const isBottomEdge = e.clientY >= rect.bottom - 10
  
  if (isRightEdge && isBottomEdge) {
    chatContainer.value!.style.cursor = 'nwse-resize'
  } else if (isRightEdge) {
    chatContainer.value!.style.cursor = 'ew-resize'
  } else if (isBottomEdge) {
    chatContainer.value!.style.cursor = 'ns-resize'
  } else {
    chatContainer.value!.style.cursor = 'default'
  }
}

// 鼠标离开
const handleMouseLeave = () => {
  if (!isResizingX.value && !isResizingY.value && chatContainer.value) {
    chatContainer.value.style.cursor = 'default'
  }
}

// 最小化/恢复
const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
}

// 放大/缩小
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 添加消息
const addMessage = (text: string, sender: 'user' | 'ai') => {
  messages.value.push({ text, sender })
  nextTick(() => {
    if (chatLog.value) {
      chatLog.value.scrollTop = chatLog.value.scrollHeight
    }
  })
}

// 发送消息
const sendMessage = () => {
  // 防止重复提交
  if (props.isSubmitting) {
    return
  }
  
  const text = userInput.value.trim()
  if (!text) return
  if (!props.ws || props.ws.readyState !== WebSocket.OPEN) {
    addMessage('未连接或输入为空...', 'ai')
    return
  }
  addMessage(text, 'user')
  addMessage('⏳ 正在查询中，请稍候...', 'ai')
  props.ws.send(text)
  userInput.value = ''
}

onMounted(() => {
  addMessage('嗨！我是你的出行百宝箱。🎩查交通、定酒店，动动嘴皮子就能搞定。至于行程规划，咱们可以闲聊细说，或者你直接点击“定制”，我立马为你安排得明明白白。告诉我你的下一个目的地，咱们出发吧！🚗', 'ai')
})

// 暴露方法给父组件
defineExpose({
  addMessage
})
</script>

<style scoped>
.draggable-chat {
  position: fixed;
  min-width: 250px;
  min-height: 300px;
  max-width: 800px;
  max-height: 900px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 9999;
  transition: box-shadow 0.3s ease;
}

.draggable-chat:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
}

.draggable-chat.minimized {
  height: 50px !important;
  min-height: 50px !important;
}

.draggable-chat.expanded {
  width: 500px !important;
}

/* 调整大小手柄 */
.resize-handle {
  position: absolute;
  z-index: 10;
  opacity: 0;
  transition: opacity 0.2s;
}

.draggable-chat:hover .resize-handle {
  opacity: 1;
}

.resize-handle-right {
  right: 0;
  top: 50px;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
  background: linear-gradient(to right, transparent, rgba(168, 181, 160, 0.3));
}

.resize-handle-bottom {
  bottom: 0;
  left: 0;
  right: 0;
  height: 8px;
  cursor: ns-resize;
  background: linear-gradient(to bottom, transparent, rgba(168, 181, 160, 0.3));
}

.resize-handle-corner {
  right: 0;
  bottom: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, rgba(168, 181, 160, 0.5) 50%);
  border-radius: 0 0 12px 0;
}

.resize-handle:hover {
  opacity: 1;
}

/* 调整大小时的状态 */
.draggable-chat.resizing-x,
.draggable-chat.resizing-y {
  user-select: none;
}

.chat-header {
  background: linear-gradient(135deg, #87CEEB 0%, #A8D8EA 100%);
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  user-select: none;
  flex-shrink: 0;
}

.header-title {
  font-weight: 600;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8f9fa;
}

.msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 14px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.msg.user {
  align-self: flex-end;
  background: linear-gradient(135deg, #FFB7B2 0%, #FFDAC1 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.msg.ai {
  align-self: flex-start;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-bottom-left-radius: 4px;
}

.input-area {
  padding: 12px;
  border-top: 1px solid #e8e8e8;
  display: flex;
  gap: 8px;
  background: white;
  flex-shrink: 0;
}

.input-area input {
  flex: 1;
  border: 1px solid #d9d9d9;
  padding: 8px 12px;
  border-radius: 6px;
  outline: none;
  font-size: 14px;
}

.input-area input:focus {
  border-color: #87CEEB;
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.2);
}

.input-area button {
  background: linear-gradient(135deg, #87CEEB 0%, #A8D8EA 100%);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.input-area button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(135, 206, 235, 0.4);
}
</style>
