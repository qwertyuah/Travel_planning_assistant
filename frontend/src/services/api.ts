import axios from 'axios'
import type { TripRequest, ChatRequest, ItineraryResponse } from '@/types'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

export const itineraryApi = {
  formPlan: async (data: TripRequest): Promise<ItineraryResponse> => {
    const response = await apiClient.post<ItineraryResponse>('/api/itinerary/form-plan', data)
    return response.data
  },

  chatPlan: async (data: ChatRequest): Promise<ItineraryResponse> => {
    const response = await apiClient.post<ItineraryResponse>('/api/itinerary/chat-plan', data)
    return response.data
  }
}

export default apiClient
