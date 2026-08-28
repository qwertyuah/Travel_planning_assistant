// 类型定义 - 与后端 schemas.py 严格对齐

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  photos?: string[]
  poi_id?: string
  image_url?: string
  ticket_price: number
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack' | string
  name: string
  address?: string
  location?: Location
  description?: string
  estimated_cost: number
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  distance: string
  type: string
  estimated_cost: number
}

export interface DayPlan {
  date: string
  day_index: number
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

// 请求类型
export interface TripRequest {
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  current_context?: Record<string, any>
}

// 响应类型
export interface ItineraryResponse {
  mode: 'form' | 'chat'
  source: 'amap' | 'baidu' | 'error'
  data?: TripPlan
  raw_data?: {
    raw_text?: string
    [key: string]: any
  }
  message: string
}

// WebSocket 状态类型
export interface TransportOption {
  id: string
  type: string
  name: string
  time: string
  from: string
  to: string
  price: number
  seats?: Array<{
    type: string
    price: number
    available: number
  }>
}

export interface SelectedTransport {
  id: string | number
  name: string
  type: string
  price: number
  time: string
  from: string
  to: string
  seat_type?: string
  direction: 'outbound' | 'return'
}

export interface HotelOption {
  id: string
  name: string
  star?: string
  address: string
  business_circle?: string
  room_type: string
  window_type?: string
  score: string
  price: number
}

export interface SelectedHotel {
  id: string | number
  name: string
  check_in: string
  check_out: string
  price: number
  type: string
}

export interface ItineraryDay {
  date: string
  breakfast_recommendation: string
  morning_activity: string
  lunch_recommendation: string
  afternoon_activity: string
  dinner_recommendation: string
}

export interface ItineraryState {
  weather: string
  clothing: string
  days: ItineraryDay[]
  raw_text: string
}

// WebSocket 消息类型
export interface ChatMessage {
  type: 'chat'
  content: string
}

export interface StateUpdateMessage {
  type: 'state_update'
  state: {
    destination?: string
    selected_transports?: SelectedTransport[]
    transport_options?: TransportOption[]
    selected_hotels?: SelectedHotel[]
    hotel_options?: HotelOption[]
    itinerary?: ItineraryState | string
    itinerary_source?: 'amap' | 'baidu'
  }
}

export type WebSocketMessage = ChatMessage | StateUpdateMessage
