<template>
  <div class="embedded-trip-result">
    <div class="result-header-compact">
      <a-button size="small" @click="$emit('back')">← 返回</a-button>
      <span class="header-title">行程规划结果</span>
      <a-space>
        <a-dropdown>
          <template #overlay>
            <a-menu>
              <a-menu-item key="pdf" @click="exportAsPDF">
                📄 导出为PDF
              </a-menu-item>
              <a-menu-item key="image" @click="exportAsImage">
                🖼️ 导出为图片
              </a-menu-item>
            </a-menu>
          </template>
          <a-button type="default" size="small">
            📥 导出 <DownOutlined />
          </a-button>
        </a-dropdown>
        <a-button type="primary" size="small" @click="$emit('retry')">重新规划</a-button>
      </a-space>
    </div>

    <!-- 降级提示 -->
    <a-alert
      v-if="isFallback"
      message="已自动切换至百度搜索"
      description="高德地图服务暂不可用，已自动降级到百度搜索模式为您生成行程建议。"
      type="warning"
      show-icon
      class="fallback-alert-compact"
    />

    <!-- 高德模式 -->
    <template v-if="isAmapMode && tripPlan">
      <div class="result-content-compact">
        <!-- 概览和预算 -->
        <a-card :title="`${tripPlan.city}旅行计划`" size="small" class="compact-card">
          <p><strong>📅 日期：</strong>{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</p>
          <p><strong>💡 建议：</strong>{{ tripPlan.overall_suggestions }}</p>
        </a-card>

        <a-card v-if="tripPlan.budget" title="💰 预算明细" size="small" class="compact-card">
          <div class="budget-compact">
            <span>门票：¥{{ tripPlan.budget.total_attractions }}</span>
            <span>酒店：¥{{ tripPlan.budget.total_hotels }}</span>
            <span>餐饮：¥{{ tripPlan.budget.total_meals }}</span>
            <span>交通：¥{{ tripPlan.budget.total_transportation }}</span>
            <span class="total">总计：¥{{ tripPlan.budget.total }}</span>
          </div>
        </a-card>

        <!-- 地图 -->
        <a-card title="📍 景点地图" size="small" class="compact-card map-card-compact">
          <AMapContainer :days="tripPlan.days" />
        </a-card>

        <!-- 每日行程 -->
        <a-card title="📅 每日行程" size="small" class="compact-card">
          <a-collapse v-model:activeKey="activeDays" accordion size="small">
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :header="`第${day.day_index + 1}天 - ${day.date}`"
            >
              <p class="day-desc">{{ day.description }}</p>
              <p class="day-info-small">🚗 {{ day.transportation }} | 🏨 {{ day.accommodation }}</p>
              
              <div v-if="day.attractions.length" class="attractions-compact">
                <div class="subsection-title">🎯 景点</div>
                <div
                  v-for="(attr, idx) in day.attractions"
                  :key="idx"
                  class="attraction-item-compact"
                >
                  <span class="attr-num">{{ idx + 1 }}</span>
                  <span class="attr-name">{{ attr.name }}</span>
                  <span class="attr-duration">{{ attr.visit_duration }}分钟</span>
                </div>
              </div>

              <div v-if="day.hotel" class="hotel-compact">
                <div class="subsection-title">🏨 住宿</div>
                <p>{{ day.hotel.name }} - {{ day.hotel.price_range }}</p>
              </div>

              <div v-if="day.meals.length" class="meals-compact">
                <div class="subsection-title">🍽️ 餐饮</div>
                <p v-for="meal in day.meals" :key="meal.type">
                  {{ getMealLabel(meal.type) }}：{{ meal.name }}
                </p>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 天气 -->
        <a-card v-if="tripPlan.weather_info?.length" title="🌤️ 天气信息" size="small" class="compact-card">
          <div class="weather-compact">
            <div
              v-for="w in tripPlan.weather_info"
              :key="w.date"
              class="weather-item-compact"
            >
              <div class="weather-date">{{ w.date }}</div>
              <div>☀️ {{ w.day_weather }} {{ w.day_temp }}°C</div>
              <div>🌙 {{ w.night_weather }} {{ w.night_temp }}°C</div>
            </div>
          </div>
        </a-card>
      </div>
    </template>

    <!-- 百度模式 - 结构化展示 -->
    <template v-else-if="isBaiduMode">
      <div class="result-content-compact">
        <!-- 概览信息 -->
        <a-card title="📋 行程规划概览" size="small" class="compact-card">
          <p><strong>🌤️ 天气：</strong>{{ baiduData.weather }}</p>
          <p><strong>👔 穿搭建议：</strong>{{ baiduData.clothing }}</p>
        </a-card>

        <!-- 每日行程 -->
        <a-card title="📅 每日行程" size="small" class="compact-card">
          <a-collapse v-model:activeKey="activeDays" accordion size="small">
            <a-collapse-panel
              v-for="(day, index) in baiduData.days"
              :key="index"
              :header="day.date"
            >
              <div class="day-schedule">
                <div class="schedule-item">
                  <div class="time-label">🌅 早餐</div>
                  <div class="content">{{ day.breakfast_recommendation }}</div>
                </div>
                <div class="schedule-item">
                  <div class="time-label">🌄 上午</div>
                  <div class="content">{{ day.morning_activity }}</div>
                </div>
                <div class="schedule-item">
                  <div class="time-label">🌞 午餐</div>
                  <div class="content">{{ day.lunch_recommendation }}</div>
                </div>
                <div class="schedule-item">
                  <div class="time-label">🌤️ 下午</div>
                  <div class="content">{{ day.afternoon_activity }}</div>
                </div>
                <div class="schedule-item">
                  <div class="time-label">🌙 晚餐</div>
                  <div class="content">{{ day.dinner_recommendation }}</div>
                </div>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>
      </div>
    </template>

    <!-- 空状态 -->
    <a-empty v-else description="暂无数据" class="compact-empty" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import AMapContainer from '@/components/AMapContainer.vue'
import type { ItineraryResponse, SelectedTransport, SelectedHotel } from '@/types'

const props = defineProps<{
  response: ItineraryResponse | null
  selectedTransports?: SelectedTransport[]
  selectedHotels?: SelectedHotel[]
}>()

const emit = defineEmits<{
  back: []
  retry: []
}>()

const tripPlan = computed(() => props.response?.data)
const isAmapMode = computed(() => props.response?.source === 'amap')
const isBaiduMode = computed(() => props.response?.source === 'baidu')
const isFallback = computed(() => props.response?.source === 'baidu')

const activeDays = ref<number[]>([0])

// 解析百度模式的数据
const baiduData = computed(() => {
  const rawData = props.response?.raw_data?.raw_text
  if (!rawData) {
    return {
      weather: '暂无天气信息',
      clothing: '暂无穿搭建议',
      days: []
    }
  }
  
  try {
    // 尝试解析 JSON
    let data: any
    if (typeof rawData === 'string') {
      data = JSON.parse(rawData)
    } else {
      data = rawData
    }
    
    return {
      weather: data.weather || '暂无天气信息',
      clothing: data.clothing || '暂无穿搭建议',
      days: Array.isArray(data.days) ? data.days : []
    }
  } catch (e) {
    // 如果解析失败，返回空数据结构
    console.error('解析百度数据失败:', e)
    return {
      weather: '暂无天气信息',
      clothing: '暂无穿搭建议',
      days: []
    }
  }
})

const formattedBaiduText = computed(() => {
  // 支持两种格式的百度数据：raw_data.raw_text 或 data（当data是字符串时）
  const rawText = props.response?.raw_data?.raw_text || 
                  (typeof props.response?.data === 'string' ? props.response?.data : null)
  if (!rawText) return '暂无内容'
  
  let formatted = rawText
    .replace(/\n/g, '<br/>')
    .replace(/(第[一二三四五六七八九十]+天)/g, '<h4 style="color: #A8D8EA; margin: 12px 0 8px;">$1</h4>')
    .replace(/(天气[：:])/g, '<strong style="color: #52c41a;">$1</strong>')
    .replace(/(穿搭建议[：:])/g, '<strong style="color: #faad14;">$1</strong>')
  
  return formatted
})

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

// 导出为PDF
const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })

    const element = document.querySelector('.result-content-compact') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建导出容器
    const exportContainer = document.createElement('div')
    exportContainer.style.width = '800px'
    exportContainer.style.backgroundColor = '#ffffff'
    exportContainer.style.padding = '30px'
    exportContainer.style.fontFamily = 'Arial, sans-serif'

    // 构建PDF内容HTML
    let pdfContent = `
      <div style="margin-bottom: 30px; border-bottom: 2px solid #A8D8EA; padding-bottom: 20px;">
        <h1 style="color: #A8D8EA; margin: 0 0 10px 0;">🌍 智能旅行计划</h1>
        <p style="color: #666; margin: 0;">生成时间：${new Date().toLocaleString()}</p>
      </div>
    `

    // 添加交通信息
    if (props.selectedTransports && props.selectedTransports.length > 0) {
      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h2 style="color: #333; border-left: 4px solid #A8D8EA; padding-left: 10px; margin-bottom: 15px;">🚗 交通预订</h2>
      `
      props.selectedTransports.forEach((transport, index) => {
        pdfContent += `
          <div style="background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 8px;">
            <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">${index + 1}. ${transport.name}</div>
            <div style="color: #666; line-height: 1.8;">
              <div>类型：${transport.type}</div>
              <div>路线：${transport.from} → ${transport.to}</div>
              <div>时间：${transport.time}</div>
              <div>座位：${transport.seat_type}</div>
              <div style="color: #A8D8EA; font-weight: bold;">价格：¥${transport.price}</div>
            </div>
          </div>
        `
      })
      pdfContent += '</div>'
    }

    // 添加酒店信息
    if (props.selectedHotels && props.selectedHotels.length > 0) {
      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h2 style="color: #333; border-left: 4px solid #A8D8EA; padding-left: 10px; margin-bottom: 15px;">🏨 酒店预订</h2>
      `
      props.selectedHotels.forEach((hotel, index) => {
        pdfContent += `
          <div style="background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 8px;">
            <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">${index + 1}. ${hotel.name}</div>
            <div style="color: #666; line-height: 1.8;">
              <div>位置：${hotel.location}</div>
              <div>价格：${hotel.price_range}</div>
            </div>
          </div>
        `
      })
      pdfContent += '</div>'
    }

    // 添加行程规划
    if (tripPlan.value) {
      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h2 style="color: #333; border-left: 4px solid #A8D8EA; padding-left: 10px; margin-bottom: 15px;">📍 行程规划</h2>
          <div style="background: #f0f7ff; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
            <div style="font-weight: bold; font-size: 18px; margin-bottom: 10px;">${tripPlan.value.city}旅行计划</div>
            <div style="color: #666; line-height: 1.8;">
              <div>📅 日期：${tripPlan.value.start_date} 至 ${tripPlan.value.end_date}</div>
              <div>💡 建议：${tripPlan.value.overall_suggestions}</div>
            </div>
          </div>
        </div>
      `

      // 预算明细
      if (tripPlan.value.budget) {
        pdfContent += `
          <div style="margin-bottom: 25px;">
            <h3 style="color: #333; margin-bottom: 10px;">💰 预算明细</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div>门票：¥${tripPlan.value.budget.total_attractions}</div>
              <div>酒店：¥${tripPlan.value.budget.total_hotels}</div>
              <div>餐饮：¥${tripPlan.value.budget.total_meals}</div>
              <div>交通：¥${tripPlan.value.budget.total_transportation}</div>
              <div style="grid-column: 1 / -1; font-weight: bold; color: #A8D8EA; font-size: 16px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
                总计：¥${tripPlan.value.budget.total}
              </div>
            </div>
          </div>
        `
      }

      // 每日行程
      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h3 style="color: #333; margin-bottom: 15px;">📅 每日行程</h3>
      `
      tripPlan.value.days.forEach((day, index) => {
        pdfContent += `
          <div style="margin-bottom: 20px; border: 1px solid #e8e8e8; border-radius: 8px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%); color: white; padding: 12px 15px; font-weight: bold;">
              第${day.day_index + 1}天 - ${day.date}
            </div>
            <div style="padding: 15px; background: #fff;">
              <div style="margin-bottom: 10px; color: #666;">${day.description}</div>
              <div style="margin-bottom: 15px; color: #999; font-size: 14px;">🚗 ${day.transportation} | 🏨 ${day.accommodation}</div>
              
              ${day.attractions.length > 0 ? `
                <div style="margin-bottom: 15px;">
                  <div style="font-weight: bold; margin-bottom: 8px; color: #333;">🎯 景点安排</div>
                  ${day.attractions.map((attr, idx) => `
                    <div style="padding: 10px; background: #f8f9fa; margin-bottom: 8px; border-radius: 6px;">
                      <div style="font-weight: 600;">${idx + 1}. ${attr.name}</div>
                      <div style="color: #666; font-size: 14px; margin-top: 4px;">
                        地址：${attr.address} | 游览时长：${attr.visit_duration}分钟
                      </div>
                      <div style="color: #888; font-size: 13px; margin-top: 4px;">${attr.description}</div>
                    </div>
                  `).join('')}
                </div>
              ` : ''}
              
              ${day.hotel ? `
                <div style="margin-bottom: 15px; background: #e3f2fd; padding: 12px; border-radius: 6px;">
                  <div style="font-weight: bold; color: #1976d2; margin-bottom: 5px;">🏨 住宿</div>
                  <div>${day.hotel.name} - ${day.hotel.price_range}</div>
                </div>
              ` : ''}
              
              ${day.meals.length > 0 ? `
                <div>
                  <div style="font-weight: bold; margin-bottom: 8px; color: #333;">🍽️ 餐饮安排</div>
                  ${day.meals.map(meal => `
                    <div style="padding: 8px 12px; background: #fff3e0; margin-bottom: 6px; border-radius: 6px; font-size: 14px;">
                      <strong>${getMealLabel(meal.type)}：</strong>${meal.name}
                      ${meal.description ? `<span style="color: #666;"> - ${meal.description}</span>` : ''}
                    </div>
                  `).join('')}
                </div>
              ` : ''}
            </div>
          </div>
        `
      })
      pdfContent += '</div>'

      // 天气信息
      if (tripPlan.value.weather_info && tripPlan.value.weather_info.length > 0) {
        pdfContent += `
          <div style="margin-bottom: 25px;">
            <h3 style="color: #333; margin-bottom: 15px;">🌤️ 天气信息</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
              ${tripPlan.value.weather_info.map(w => `
                <div style="background: #e0f7fa; padding: 15px; border-radius: 8px; text-align: center;">
                  <div style="font-weight: bold; margin-bottom: 8px; color: #00796b;">${w.date}</div>
                  <div style="font-size: 14px; color: #666;">☀️ ${w.day_weather} ${w.day_temp}°C</div>
                  <div style="font-size: 14px; color: #666;">🌙 ${w.night_weather} ${w.night_temp}°C</div>
                </div>
              `).join('')}
            </div>
          </div>
        `
      }
    }

    // 百度模式数据处理
    else if (isBaiduMode.value && baiduData.value) {
      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h2 style="color: #333; border-left: 4px solid #A8D8EA; padding-left: 10px; margin-bottom: 15px;">📍 行程规划</h2>
          <div style="background: #f0f7ff; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
            <div style="color: #666; line-height: 1.8;">
              <div>🌤️ 天气：${baiduData.value.weather}</div>
              <div>👔 穿搭建议：${baiduData.value.clothing}</div>
            </div>
          </div>
        </div>
      `

      pdfContent += `
        <div style="margin-bottom: 25px;">
          <h3 style="color: #333; margin-bottom: 15px;">📅 每日行程</h3>
      `
      baiduData.value.days.forEach((day: any, index: number) => {
        pdfContent += `
          <div style="margin-bottom: 20px; border: 1px solid #e8e8e8; border-radius: 8px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%); color: white; padding: 12px 15px; font-weight: bold;">
              ${day.date}
            </div>
            <div style="padding: 15px; background: #fff;">
              <div style="margin-bottom: 12px; padding: 10px; background: #fff3e0; border-radius: 6px;">
                <strong>🌅 早餐：</strong>${day.breakfast_recommendation}
              </div>
              <div style="margin-bottom: 12px; padding: 10px; background: #f3e5f5; border-radius: 6px;">
                <strong>🌞 上午行程：</strong>${day.morning_schedule}
              </div>
              <div style="margin-bottom: 12px; padding: 10px; background: #fff3e0; border-radius: 6px;">
                <strong>🌞 午餐：</strong>${day.lunch_recommendation}
              </div>
              <div style="margin-bottom: 12px; padding: 10px; background: #f3e5f5; border-radius: 6px;">
                <strong>🌅 下午行程：</strong>${day.afternoon_schedule}
              </div>
              <div style="margin-bottom: 12px; padding: 10px; background: #fff3e0; border-radius: 6px;">
                <strong>🌙 晚餐：</strong>${day.dinner_recommendation}
              </div>
              <div style="padding: 10px; background: #e3f2fd; border-radius: 6px;">
                <strong>🏨 住宿：</strong>${day.accommodation}
              </div>
            </div>
          </div>
        `
      })
      pdfContent += '</div>'
    }

    exportContainer.innerHTML = pdfContent

    // 添加到body(隐藏)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#ffffff',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    // 移除容器
    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const imgWidth = 210 // A4宽度(mm)
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    // 如果内容高度超过一页,分页处理
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297 // A4高度

    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }

    pdf.save(`旅行计划_${tripPlan.value?.city || '行程'}_${new Date().getTime()}.pdf`)

    message.success({ content: 'PDF导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    message.error({ content: `导出PDF失败: ${error.message}`, key: 'export' })
  }
}

// 导出为图片（JPG格式）
const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })

    const element = document.querySelector('.result-content-compact') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建导出容器（克隆内容以避免影响原页面）
    const exportContainer = element.cloneNode(true) as HTMLElement
    
    // 设置样式确保图片清晰
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#ffffff'
    exportContainer.style.padding = '20px'
    
    // 临时添加到body（隐藏）
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    exportContainer.style.top = '0'
    document.body.appendChild(exportContainer)

    // 等待渲染完成
    await new Promise(resolve => setTimeout(resolve, 500))

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#ffffff',
      scale: 2, // 高清质量
      logging: false,
      useCORS: true,
      allowTaint: true,
      windowWidth: exportContainer.scrollWidth,
      windowHeight: exportContainer.scrollHeight
    })

    // 移除临时容器
    document.body.removeChild(exportContainer)

    // 转换为JPG并下载
    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city || '行程'}_${new Date().getTime()}.jpg`
    link.href = canvas.toDataURL('image/jpeg', 0.9) // JPG格式，90%质量
    link.click()

    message.success({ content: '图片导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: `导出图片失败: ${error.message}`, key: 'export' })
  }
}
</script>

<style scoped>
.embedded-trip-result {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-header-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
  flex-shrink: 0;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.fallback-alert-compact {
  margin: 10px 12px 0;
  flex-shrink: 0;
}

.result-content-compact {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
}

.compact-card {
  margin-bottom: 10px;
}

.compact-card :deep(.ant-card-head) {
  padding: 8px 12px;
  min-height: 36px;
}

.compact-card :deep(.ant-card-head-title) {
  font-size: 13px;
}

.compact-card :deep(.ant-card-body) {
  padding: 12px;
}

.map-card-compact :deep(.ant-card-body) {
  padding: 0;
  height: 250px;
}

.budget-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}

.budget-compact .total {
  color: #f5222d;
  font-weight: 600;
}

.day-desc {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.day-info-small {
  font-size: 12px;
  color: #999;
  margin-bottom: 10px;
}

.subsection-title {
  font-size: 12px;
  font-weight: 600;
  color: #A8D8EA;
  margin: 10px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px dashed #e8e8e8;
}

.attractions-compact {
  font-size: 12px;
}

.attraction-item-compact {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}

.attraction-item-compact:last-child {
  border-bottom: none;
}

.attr-num {
  width: 18px;
  height: 18px;
  background: #A8D8EA;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
}

.attr-name {
  flex: 1;
  font-weight: 500;
}

.attr-duration {
  color: #999;
  font-size: 11px;
}

.hotel-compact,
.meals-compact {
  font-size: 12px;
}

.meals-compact p {
  margin: 4px 0;
}

.weather-compact {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.weather-item-compact {
  background: #FFF5F5;
  border-radius: 6px;
  padding: 8px;
  font-size: 11px;
  text-align: center;
}

.weather-date {
  font-weight: 600;
  color: #A8D8EA;
  margin-bottom: 4px;
}

.baidu-text-compact {
  font-size: 13px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

/* 百度模式 - 日程样式 */
.day-schedule {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.schedule-item {
  display: flex;
  gap: 12px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid #A8D8EA;
}

.time-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #A8D8EA;
  min-width: 60px;
}

.schedule-item .content {
  flex: 1;
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}

.compact-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
