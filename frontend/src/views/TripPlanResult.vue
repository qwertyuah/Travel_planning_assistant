<template>
  <div class="trip-plan-result">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-button class="back-button" size="large" @click="goBack">
        ← 返回首页
      </a-button>
      <div class="header-actions">
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
            <a-button>
              📥 导出 <DownOutlined />
            </a-button>
          </a-dropdown>
          <a-button type="primary" @click="goToForm">
            🔄 重新规划
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 降级提示 -->
    <a-alert
      v-if="isFallback"
      message="已自动切换至百度搜索"
      description="高德地图服务暂不可用，已自动降级到百度搜索模式为您生成行程建议。"
      type="warning"
      show-icon
      class="fallback-alert"
    />

    <!-- 高德模式：结构化展示 -->
    <template v-if="isAmapMode && tripPlan">
      <div class="content-wrapper">
        <!-- 侧边导航 -->
        <div class="side-nav">
          <a-affix :offset-top="20">
            <a-menu mode="inline" :selected-keys="[activeSection]" @click="scrollToSection">
              <a-menu-item key="overview">
                <span>📋 行程概览</span>
              </a-menu-item>
              <a-menu-item key="budget" v-if="tripPlan.budget">
                <span>💰 预算明细</span>
              </a-menu-item>
              <a-menu-item key="map">
                <span>📍 景点地图</span>
              </a-menu-item>
              <a-sub-menu key="days" title="📅 每日行程">
                <a-menu-item v-for="(day, index) in tripPlan.days" :key="`day-${index}`">
                  第{{ day.day_index + 1 }}天
                </a-menu-item>
              </a-sub-menu>
              <a-menu-item key="weather" v-if="tripPlan.weather_info?.length">
                <span>🌤️ 天气信息</span>
              </a-menu-item>
            </a-menu>
          </a-affix>
        </div>

        <!-- 主内容区 -->
        <div class="main-content" ref="mainContentRef">
          <!-- 顶部信息区：左侧概览+预算，右侧地图 -->
          <div class="top-info-section">
            <!-- 左侧：行程概览和预算明细 -->
            <div class="left-info">
              <!-- 行程概览 -->
              <a-card id="overview" :title="`${tripPlan.city}旅行计划`" :bordered="false" class="overview-card">
                <div class="overview-content">
                  <div class="info-item">
                    <span class="info-label">📅 日期：</span>
                    <span class="info-value">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">💡 建议：</span>
                    <span class="info-value">{{ tripPlan.overall_suggestions }}</span>
                  </div>
                </div>
              </a-card>

              <!-- 预算明细 -->
              <a-card id="budget" v-if="tripPlan.budget" title="💰 预算明细" :bordered="false" class="budget-card">
                <div class="budget-grid">
                  <div class="budget-item">
                    <div class="budget-label">景点门票</div>
                    <div class="budget-value">¥{{ tripPlan.budget.total_attractions }}</div>
                  </div>
                  <div class="budget-item">
                    <div class="budget-label">酒店住宿</div>
                    <div class="budget-value">¥{{ tripPlan.budget.total_hotels }}</div>
                  </div>
                  <div class="budget-item">
                    <div class="budget-label">餐饮费用</div>
                    <div class="budget-value">¥{{ tripPlan.budget.total_meals }}</div>
                  </div>
                  <div class="budget-item">
                    <div class="budget-label">交通费用</div>
                    <div class="budget-value">¥{{ tripPlan.budget.total_transportation }}</div>
                  </div>
                </div>
                <div class="budget-total">
                  <span class="total-label">预估总费用</span>
                  <span class="total-value">¥{{ tripPlan.budget.total }}</span>
                </div>
              </a-card>
            </div>

            <!-- 右侧：地图 -->
            <div class="right-map">
              <a-card id="map" title="📍 景点地图" :bordered="false" class="map-card">
                <AMapContainer :days="tripPlan.days" />
              </a-card>
            </div>
          </div>

          <!-- 每日行程：可折叠 -->
          <a-card title="📅 每日行程" :bordered="false" class="days-card">
            <a-collapse v-model:activeKey="activeDays" accordion>
              <a-collapse-panel
                v-for="(day, index) in tripPlan.days"
                :key="index"
                :id="`day-${index}`"
              >
                <template #header>
                  <div class="day-header">
                    <span class="day-title">第{{ day.day_index + 1 }}天</span>
                    <span class="day-date">{{ day.date }}</span>
                  </div>
                </template>

                <!-- 行程基本信息 -->
                <div class="day-info">
                  <div class="info-row">
                    <span class="label">📝 行程描述：</span>
                    <span class="value">{{ day.description }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">🚗 交通方式：</span>
                    <span class="value">{{ day.transportation }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">🏨 住宿：</span>
                    <span class="value">{{ day.accommodation }}</span>
                  </div>
                </div>

                <!-- 景点安排 -->
                <a-divider orientation="left">🎯 景点安排</a-divider>
                <a-list
                  :data-source="day.attractions"
                  :grid="{ gutter: 16, column: 2 }"
                >
                  <template #renderItem="{ item, index: attrIndex }">
                    <a-list-item>
                      <a-card :title="item.name" size="small" class="attraction-card">
                        <!-- 景点图片 -->
                        <div class="attraction-image-wrapper">
                          <img
                            :src="getAttractionImage(item.name, attrIndex)"
                            :alt="item.name"
                            class="attraction-image"
                            @error="handleImageError"
                          />
                          <div class="attraction-badge">
                            <span class="badge-number">{{ attrIndex + 1 }}</span>
                          </div>
                          <div v-if="item.ticket_price" class="price-tag">
                            ¥{{ item.ticket_price }}
                          </div>
                        </div>

                        <div class="attraction-info">
                          <p><strong>地址：</strong>{{ item.address }}</p>
                          <p><strong>游览时长：</strong>{{ item.visit_duration }}分钟</p>
                          <p><strong>描述：</strong>{{ item.description }}</p>
                          <p v-if="item.rating"><strong>评分：</strong>{{ item.rating }}⭐</p>
                        </div>
                      </a-card>
                    </a-list-item>
                  </template>
                </a-list>

                <!-- 酒店推荐 -->
                <a-divider v-if="day.hotel" orientation="left">🏨 住宿推荐</a-divider>
                <a-card v-if="day.hotel" size="small" class="hotel-card">
                  <template #title>
                    <span class="hotel-title">{{ day.hotel.name }}</span>
                  </template>
                  <a-descriptions :column="2" size="small">
                    <a-descriptions-item label="地址">{{ day.hotel.address }}</a-descriptions-item>
                    <a-descriptions-item label="类型">{{ day.hotel.type }}</a-descriptions-item>
                    <a-descriptions-item label="价格范围">{{ day.hotel.price_range }}</a-descriptions-item>
                    <a-descriptions-item label="评分">{{ day.hotel.rating }}⭐</a-descriptions-item>
                    <a-descriptions-item label="距离" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
                  </a-descriptions>
                </a-card>

                <!-- 餐饮安排 -->
                <a-divider orientation="left">🍽️ 餐饮安排</a-divider>
                <a-descriptions :column="1" bordered size="small">
                  <a-descriptions-item
                    v-for="meal in day.meals"
                    :key="meal.type"
                    :label="getMealLabel(meal.type)"
                  >
                    {{ meal.name }}
                    <span v-if="meal.description"> - {{ meal.description }}</span>
                  </a-descriptions-item>
                </a-descriptions>
              </a-collapse-panel>
            </a-collapse>
          </a-card>

          <!-- 天气信息 -->
          <a-card
            id="weather"
            v-if="tripPlan.weather_info?.length"
            title="🌤️ 天气信息"
            :bordered="false"
            class="weather-card-section"
          >
            <a-list
              :data-source="tripPlan.weather_info"
              :grid="{ gutter: 16, column: 3 }"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-card size="small" class="weather-card">
                    <div class="weather-date">{{ item.date }}</div>
                    <div class="weather-info-row">
                      <span class="weather-icon">☀️</span>
                      <div>
                        <div class="weather-label">白天</div>
                        <div class="weather-value">{{ item.day_weather }} {{ item.day_temp }}°C</div>
                      </div>
                    </div>
                    <div class="weather-info-row">
                      <span class="weather-icon">🌙</span>
                      <div>
                        <div class="weather-label">夜间</div>
                        <div class="weather-value">{{ item.night_weather }} {{ item.night_temp }}°C</div>
                      </div>
                    </div>
                    <div class="weather-wind">
                      💨 {{ item.wind_direction }} {{ item.wind_power }}
                    </div>
                  </a-card>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </div>
      </div>
    </template>

    <!-- 百度模式：降级文本展示 -->
    <template v-else-if="isBaiduMode">
      <div class="baidu-content">
        <a-card title="📋 行程规划结果" :bordered="false" class="baidu-result-card">
          <div class="baidu-text-content" v-html="formattedBaiduText"></div>
        </a-card>
      </div>
    </template>

    <!-- 空状态 -->
    <a-empty v-else description="没有找到旅行计划数据">
      <template #image>
        <div style="font-size: 80px;">🗺️</div>
      </template>
      <template #description>
        <span style="color: #999;">暂无旅行计划数据，请先创建行程</span>
      </template>
      <a-button type="primary" @click="goToForm">前往创建行程</a-button>
    </a-empty>

    <!-- 回到顶部按钮 -->
    <a-back-top :visibility-height="300">
      <div class="back-top-button">↑</div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import AMapContainer from '@/components/AMapContainer.vue'
import type { ItineraryResponse, TripPlan } from '@/types'

const router = useRouter()

// 响应数据
const itineraryResponse = ref<ItineraryResponse | null>(null)
const tripPlan = computed(() => itineraryResponse.value?.data)

// 计算模式
const isAmapMode = computed(() => itineraryResponse.value?.source === 'amap')
const isBaiduMode = computed(() => itineraryResponse.value?.source === 'baidu')
const isFallback = computed(() => itineraryResponse.value?.source === 'baidu')

// 导航状态
const activeSection = ref('overview')
const activeDays = ref<number[]>([0])

// 格式化百度文本
const formattedBaiduText = computed(() => {
  const rawText = itineraryResponse.value?.raw_data?.raw_text
  if (!rawText) return '暂无内容'
  
  // 简单的文本格式化
  let formatted = rawText
    .replace(/\n/g, '<br/>')
    .replace(/(第[一二三四五六七八九十]+天)/g, '<h3 style="color: #1890ff; margin-top: 20px;">$1</h3>')
    .replace(/(天气[：:])/g, '<strong style="color: #52c41a;">$1</strong>')
    .replace(/(穿搭建议[：:])/g, '<strong style="color: #faad14;">$1</strong>')
    .replace(/(早餐|午餐|晚餐)[：:]/g, '<strong style="color: #f5222d;">$1：</strong>')
  
  return formatted
})

onMounted(() => {
  const data = sessionStorage.getItem('tripPlanResponse')
  if (data) {
    itineraryResponse.value = JSON.parse(data)
  }
})

const goBack = () => {
  router.push('/')
}

const goToForm = () => {
  router.push('/trip-plan')
}

const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

// 获取景点图片
const getAttractionImage = (name: string, index: number): string => {
  const colors = [
    { start: '#A8D8EA', end: '#FFB7B2' },
    { start: '#f093fb', end: '#f5576c' },
    { start: '#4facfe', end: '#00f2fe' },
    { start: '#43e97b', end: '#38f9d7' },
    { start: '#fa709a', end: '#fee140' }
  ]
  const colorIndex = Math.abs(index) % colors.length
  const start = colors[colorIndex]!.start
  const end = colors[colorIndex]!.end

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
    <defs>
      <linearGradient id="grad${index}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${start};stop-opacity:1" />
        <stop offset="100%" style="stop-color:${end};stop-opacity:1" />
      </linearGradient>
    </defs>
    <rect width="400" height="300" fill="url(#grad${index})"/>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="24" font-weight="bold" fill="white">${name}</text>
  </svg>`

  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18" fill="%23999"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}

// 导出为PDF
const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })

    const element = document.querySelector('.content-wrapper') as HTMLElement
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
              <div style="grid-column: 1 / -1; font-weight: bold; color: #1890ff; font-size: 16px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
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
    else if (isBaiduMode.value) {
      const rawText = itineraryResponse.value?.raw_data?.raw_text
      if (rawText) {
        pdfContent += `
          <div style="margin-bottom: 25px;">
            <h2 style="color: #333; border-left: 4px solid #A8D8EA; padding-left: 10px; margin-bottom: 15px;">📍 行程规划</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; line-height: 1.8; white-space: pre-wrap;">
              ${rawText.replace(/\n/g, '<br>')}
            </div>
          </div>
        `
      }
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

    const element = document.querySelector('.content-wrapper') as HTMLElement
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
.trip-plan-result {
  min-height: 100vh;
  background: linear-gradient(135deg, #FFFAFA 0%, #E8F5F2 100%);
  padding: 20px;
}

.page-header {
  max-width: 1400px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fallback-alert {
  max-width: 1400px;
  margin: 0 auto 20px;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  gap: 20px;
}

.side-nav {
  width: 220px;
  flex-shrink: 0;
}

.side-nav :deep(.ant-menu) {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background: white;
}

.main-content {
  flex: 1;
  min-width: 0;
}

/* 顶部信息区布局 */
.top-info-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.left-info {
  flex: 0 0 380px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-map {
  flex: 1;
}

/* 卡片样式 */
.overview-card,
.budget-card {
  height: fit-content;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}

.info-value {
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

/* 预算卡片 */
.budget-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.budget-item {
  text-align: center;
  padding: 10px;
  background: linear-gradient(135deg, #FFFAFA 0%, #FFFFFF 100%);
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.budget-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

.budget-value {
  font-size: 18px;
  font-weight: 700;
  color: #A8D8EA;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  border-radius: 8px;
  color: white;
}

.total-label {
  font-size: 14px;
  font-weight: 600;
}

.total-value {
  font-size: 24px;
  font-weight: 700;
}

/* 地图卡片 */
.map-card {
  height: 100%;
  min-height: 450px;
}

.map-card :deep(.ant-card-body) {
  height: calc(100% - 50px);
  padding: 0;
}

/* 每日行程 */
.days-card {
  margin-top: 20px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.day-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.day-date {
  font-size: 13px;
  color: #999;
}

.day-info {
  margin-bottom: 16px;
  padding: 12px;
  background: linear-gradient(135deg, #FFFAFA 0%, #ffffff 100%);
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.info-row {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  font-weight: 600;
  color: #666;
  min-width: 90px;
}

.info-row .value {
  color: #333;
  flex: 1;
}

/* 景点卡片 */
.attraction-card {
  margin-bottom: 12px;
}

.attraction-image-wrapper {
  position: relative;
  margin-bottom: 10px;
  border-radius: 8px;
  overflow: hidden;
}

.attraction-image {
  width: 100%;
  height: 150px;
  object-fit: cover;
}

.attraction-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  color: white;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.price-tag {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255, 77, 79, 0.9);
  color: white;
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: bold;
  font-size: 12px;
}

.attraction-info {
  font-size: 13px;
  line-height: 1.6;
}

.attraction-info p {
  margin: 4px 0;
}

/* 酒店卡片 */
.hotel-card {
  background: linear-gradient(135deg, #FFF5F5 0%, #B2EBF2 100%);
  border: none !important;
  margin-top: 12px;
}

.hotel-card :deep(.ant-card-head) {
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  border-radius: 8px 8px 0 0;
}

.hotel-title {
  color: white !important;
  font-weight: 600;
}

/* 天气卡片 */
.weather-card-section {
  margin-top: 20px;
}

.weather-card {
  background: linear-gradient(135deg, #FFF5F5 0%, #B2EBF2 100%);
  border: none !important;
}

.weather-date {
  font-size: 14px;
  font-weight: bold;
  color: #00796b;
  margin-bottom: 10px;
  text-align: center;
}

.weather-info-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.weather-icon {
  font-size: 20px;
}

.weather-label {
  font-size: 11px;
  color: #666;
}

.weather-value {
  font-size: 14px;
  font-weight: 600;
  color: #00796b;
}

.weather-wind {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(0, 121, 107, 0.2);
  text-align: center;
  color: #00796b;
  font-size: 12px;
}

/* 百度模式 */
.baidu-content {
  max-width: 900px;
  margin: 0 auto;
}

.baidu-result-card {
  background: white;
}

.baidu-text-content {
  line-height: 1.8;
  font-size: 14px;
}

/* 回到顶部按钮 */
.back-top-button {
  width: 45px;
  height: 45px;
  background: linear-gradient(135deg, #A8D8EA 0%, #FFB7B2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-top-button:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

/* Ant Design 组件样式覆盖 */
:deep(.ant-card) {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

:deep(.ant-card-head) {
  background: linear-gradient(135deg, #FFB7B2 0%, #FFDAC1 100%);
  color: white !important;
  border-radius: 12px 12px 0 0;
  font-weight: 600;
}

/* 不同类型卡片的不同马卡龙色彩 */
:deep(.ant-card.budget-card .ant-card-head) {
  background: linear-gradient(135deg, #7FDBDA 0%, #A8E6CF 100%);
}

:deep(.ant-card.hotel-card .ant-card-head) {
  background: linear-gradient(135deg, #87CEEB 0%, #A8D8EA 100%);
}

:deep(.ant-card.weather-card .ant-card-head) {
  background: linear-gradient(135deg, #87CEEB 0%, #A8D8EA 100%);
}

:deep(.ant-card-head-title) {
  color: white !important;
}

:deep(.ant-collapse) {
  border: none;
  background: transparent;
}

:deep(.ant-collapse-item) {
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  overflow: hidden;
  background: white;
}

/* 响应式 */
@media (max-width: 1024px) {
  .content-wrapper {
    flex-direction: column;
  }
  
  .side-nav {
    width: 100%;
  }
  
  .top-info-section {
    flex-direction: column;
  }
  
  .left-info {
    flex: 1;
  }
  
  .right-map {
    min-height: 300px;
  }
}
</style>
