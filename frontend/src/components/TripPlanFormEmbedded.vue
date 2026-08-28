<template>
  <div class="embedded-trip-form">
    <div class="form-header-compact">
      <a-button size="small" @click="$emit('cancel')">← 返回</a-button>
      <span class="header-title">规划您的旅行</span>
    </div>

    <a-form :model="formData" layout="vertical" @finish="handleSubmit" class="compact-form">
      <!-- 目的地和日期 -->
      <div class="form-section-compact">
        <div class="section-title-small">📍 目的地与日期</div>
        <a-row :gutter="12">
          <a-col :span="10">
            <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地' }]">
              <a-input v-model:value="formData.city" placeholder="目的地城市" size="middle">
                <template #prefix>🏙️</template>
              </a-input>
            </a-form-item>
          </a-col>
          <a-col :span="7">
            <a-form-item name="start_date" :rules="[{ required: true, message: '开始日期' }]">
              <a-date-picker v-model:value="formData.start_date" style="width: 100%" size="middle" placeholder="开始" />
            </a-form-item>
          </a-col>
          <a-col :span="7">
            <a-form-item name="end_date" :rules="[{ required: true, message: '结束日期' }]">
              <a-date-picker v-model:value="formData.end_date" style="width: 100%" size="middle" placeholder="结束" />
            </a-form-item>
          </a-col>
        </a-row>
        <div v-if="formData.start_date && formData.end_date" class="days-tag">
          共 {{ formData.travel_days }} 天
        </div>
      </div>

      <!-- 偏好设置 -->
      <div class="form-section-compact">
        <div class="section-title-small">⚙️ 偏好设置</div>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="交通方式">
              <a-select v-model:value="formData.transportation" size="middle">
                <a-select-option value="公共交通">🚇 公共交通</a-select-option>
                <a-select-option value="自驾">🚗 自驾</a-select-option>
                <a-select-option value="步行">🚶 步行</a-select-option>
                <a-select-option value="混合">🔀 混合</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="住宿偏好">
              <a-select v-model:value="formData.accommodation" size="middle">
                <a-select-option value="经济型酒店">💰 经济型</a-select-option>
                <a-select-option value="舒适型酒店">🏨 舒适型</a-select-option>
                <a-select-option value="豪华酒店">⭐ 豪华型</a-select-option>
                <a-select-option value="民宿">🏡 民宿</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="旅行偏好">
          <a-checkbox-group v-model:value="formData.preferences" class="compact-checkbox-group">
            <a-checkbox value="历史文化">🏛️ 历史文化</a-checkbox>
            <a-checkbox value="自然风光">🏞️ 自然风光</a-checkbox>
            <a-checkbox value="美食">🍜 美食</a-checkbox>
            <a-checkbox value="购物">🛍️ 购物</a-checkbox>
            <a-checkbox value="艺术">🎨 艺术</a-checkbox>
            <a-checkbox value="休闲">☕ 休闲</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </div>

      <!-- 额外要求 -->
      <div class="form-section-compact">
        <div class="section-title-small">💬 额外要求</div>
        <a-form-item>
          <a-textarea
            v-model:value="formData.free_text_input"
            placeholder="例如：想去看升旗、需要无障碍设施..."
            :rows="2"
            size="middle"
          />
        </a-form-item>
      </div>

      <!-- 提交按钮 -->
      <a-form-item class="submit-item">
        <a-button
          type="primary"
          html-type="submit"
          :loading="loading"
          :disabled="loading || isSubmitting"
          size="large"
          block
          class="submit-btn"
        >
          <span v-if="!loading && !isSubmitting">🚀 开始规划</span>
          <span v-else-if="isSubmitting">处理中...</span>
          <span v-else>生成中...</span>
        </a-button>
      </a-form-item>

      <!-- 进度条 -->
      <div v-if="loading" class="loading-area">
        <a-progress :percent="loadingProgress" status="active" :stroke-width="8" />
        <p class="loading-text">{{ loadingStatus }}</p>
      </div>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import type { TripRequest } from '@/types'

const props = defineProps<{
  isSubmitting?: boolean
}>()

const emit = defineEmits<{
  submit: [data: TripRequest]
  cancel: []
}>()

const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')
const progressInterval = ref<ReturnType<typeof setInterval> | null>(null)

interface FormData {
  city: string
  start_date: Dayjs | null
  end_date: Dayjs | null
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
}

const formData = reactive<FormData>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '舒适型酒店',
  preferences: [],
  free_text_input: ''
})

watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

const validateDates = () => {
  const today = dayjs().startOf('day')
  
  if (formData.start_date && formData.start_date.isBefore(today)) {
    message.error('开始日期不能早于今天')
    return false
  }
  
  if (formData.end_date && formData.end_date.isBefore(today)) {
    message.error('结束日期不能早于今天')
    return false
  }
  
  if (formData.start_date && formData.end_date) {
    if (formData.end_date.isBefore(formData.start_date)) {
      message.error('结束日期必须晚于开始日期')
      return false
    }
    
    const days = formData.end_date.diff(formData.start_date, 'day') + 1
    if (days > 30) {
      message.error('旅行天数不能超过30天')
      return false
    }
  }
  
  return true
}

const handleSubmit = async () => {
  if (!formData.city.trim()) {
    message.error('请输入目的地城市')
    return
  }

  if (!formData.start_date || !formData.end_date) {
    message.error('请选择开始日期和结束日期')
    return
  }

  if (!validateDates()) {
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '⏳ 正在初始化智能规划引擎...'

  // 定义固定进度阶段：25% -> 50% -> 75% -> 90%（等待结果）
  const progressStages = [
    { percent: 25, text: '🔍 正在搜索热门景点...', delay: 1500 },
    { percent: 50, text: '📍 正在获取景点地理位置...', delay: 1500 },
    { percent: 75, text: '🏨 正在查询酒店信息...', delay: 1500 },
    { percent: 90, text: '🗺️ 正在生成智能行程...', delay: 0 }
  ]

  let currentStage = 0
  
  progressInterval.value = setInterval(() => {
    if (currentStage < progressStages.length) {
      const stage = progressStages[currentStage]
      if (stage) {
        loadingProgress.value = stage.percent
        loadingStatus.value = stage.text
        
        // 如果是最后一个阶段（90%），清除定时器，等待后台返回
        if (currentStage === progressStages.length - 1) {
          if (progressInterval.value) {
            clearInterval(progressInterval.value)
            progressInterval.value = null
          }
        }
        
        currentStage++
      }
    }
  }, 1500)

  try {
    const requestData: TripRequest = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input
    }

    // 进度条继续运行，直到父组件通知完成
    loadingStatus.value = '🚀 正在提交规划请求...'
    
    // 延迟一下让用户看到进度
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 发出提交事件，但不关闭loading（由父组件控制）
    emit('submit', requestData)
    
  } catch (error) {
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
      progressInterval.value = null
    }
    loading.value = false
    message.error('提交失败')
  }
}

// 外部调用的方法：完成loading
const completeLoading = () => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
    progressInterval.value = null
  }
  loadingProgress.value = 100
  loadingStatus.value = '✅ 规划完成！'
  
  setTimeout(() => {
    loading.value = false
  }, 500)
}

// 外部调用的方法：失败处理
const failLoading = (errorMessage: string = '规划失败') => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
    progressInterval.value = null
  }
  loading.value = false
  message.error(errorMessage)
}

// 暴露方法给父组件
defineExpose({
  completeLoading,
  failLoading
})
</script>

<style scoped>
.embedded-trip-form {
  padding: 12px;
  height: 100%;
  overflow-y: auto;
}

.form-header-compact {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8e8e8;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.compact-form :deep(.ant-form-item) {
  margin-bottom: 12px;
}

.form-section-compact {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.section-title-small {
  font-size: 13px;
  font-weight: 600;
  color: #A8D8EA;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e8e8e8;
}

.days-tag {
  display: inline-block;
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.compact-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.compact-checkbox-group :deep(.ant-checkbox-wrapper) {
  margin: 0;
  font-size: 12px;
}

.submit-item {
  margin-top: 16px;
  margin-bottom: 0 !important;
}

.submit-btn {
  height: 42px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  border: none;
}

.loading-area {
  margin-top: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #FFF5F5 0%, #F0FCFA 100%);
  border-radius: 12px;
  border: 2px solid #FFB7B2;
  box-shadow: 0 4px 12px rgba(255, 183, 178, 0.2);
}

.loading-area :deep(.ant-progress) {
  margin-bottom: 12px;
}

.loading-area :deep(.ant-progress-bg) {
  border-radius: 100px;
  background: linear-gradient(90deg, #FFB7B2 0%, #7FDBDA 50%, #87CEEB 100%);
  background-size: 200% 100%;
  animation: progress-flow 2s linear infinite;
}

@keyframes progress-flow {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.loading-text {
  margin: 12px 0 0;
  text-align: center;
  color: #FFB7B2;
  font-size: 14px;
  font-weight: 500;
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.loading-text::before {
  content: '';
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #FFB7B2;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 进度百分比显示样式 */
.loading-area :deep(.ant-progress-text) {
  font-weight: 600;
  font-size: 14px;
  color: #FFB7B2;
}
</style>
