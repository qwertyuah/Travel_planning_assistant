<template>
  <div id="amap-container" class="amap-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { DayPlan, Attraction } from '@/types'

interface MapAttraction extends Attraction {
  dayIndex: number
  attrIndex: number
}

const props = defineProps<{
  days: DayPlan[]
}>()

let map: any = null
let AMap: any = null

onMounted(async () => {
  await nextTick()
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.destroy()
    map = null
  }
})

const initMap = async () => {
  try {
    AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    // 创建地图实例
    map = new AMap.Map('amap-container', {
      zoom: 12,
      center: [116.397128, 39.916527],
      viewMode: '3D'
    })

    // 添加景点标记
    addAttractionMarkers()
  } catch (error) {
    console.error('地图加载失败:', error)
  }
}

const addAttractionMarkers = () => {
  if (!map || !props.days) return

  const markers: any[] = []
  const allAttractions: MapAttraction[] = []

  // 收集所有景点
  props.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction, attrIndex) => {
      if (attraction.location && attraction.location.longitude && attraction.location.latitude) {
        allAttractions.push({
          ...attraction,
          dayIndex,
          attrIndex
        })
      }
    })
  })

  // 创建标记
  allAttractions.forEach((attraction, index) => {
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      label: {
        content: `<div style="background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })

    // 创建信息窗口
    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding: 10px; max-width: 300px;">
          <h4 style="margin: 0 0 8px 0; font-size: 16px;">${attraction.name}</h4>
          <p style="margin: 4px 0; font-size: 13px;"><strong>地址:</strong> ${attraction.address}</p>
          <p style="margin: 4px 0; font-size: 13px;"><strong>游览时长:</strong> ${attraction.visit_duration}分钟</p>
          <p style="margin: 4px 0; font-size: 13px;"><strong>描述:</strong> ${attraction.description}</p>
          <p style="margin: 4px 0; font-size: 13px; color: #1890ff;"><strong>第${attraction.dayIndex + 1}天 景点${attraction.attrIndex + 1}</strong></p>
        </div>
      `,
      offset: new AMap.Pixel(0, -30)
    })

    // 点击标记显示信息窗口
    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition())
    })

    markers.push(marker)
  })

  // 添加标记到地图
  map.add(markers)

  // 自动调整视野以包含所有标记
  if (allAttractions.length > 0) {
    map.setFitView(markers)
  }

  // 绘制路线
  drawRoutes(allAttractions)
}

const drawRoutes = (attractions: MapAttraction[]) => {
  if (attractions.length < 2) return

  // 按天分组绘制路线
  const dayGroups: { [key: number]: MapAttraction[] } = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) {
      dayGroups[attr.dayIndex] = []
    }
    dayGroups[attr.dayIndex]!.push(attr)
  })

  // 为每天的景点绘制路线
  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
  
  Object.entries(dayGroups).forEach(([dayIndex, dayAttractions]) => {
    if (dayAttractions.length < 2) return

    const path = dayAttractions.map((attr: MapAttraction) => [
      attr.location.longitude,
      attr.location.latitude
    ])

    const colorIndex = parseInt(dayIndex) % colors.length

    const polyline = new AMap.Polyline({
      path: path,
      strokeColor: colors[colorIndex],
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeStyle: 'solid',
      showDir: true
    })

    map.add(polyline)
  })
}
</script>

<style scoped>
.amap-container {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
}
</style>
