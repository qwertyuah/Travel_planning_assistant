import operator
from typing import List, Optional, Annotated, TypedDict
from langchain_core.messages import BaseMessage


class TravelState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    destination: Optional[str]
    start_date: Optional[str]
    budget: Optional[float]
    transport_options: Optional[List[dict]]
    selected_transports: List[dict]
    current_booking_step: Optional[str]
    hotel_options: Optional[List[dict]]
    selected_hotels: List[dict]
    intent: Optional[str]  # "transport" / "hotel" / "itinerary"
    origin: Optional[str]

    end_date: Optional[str]
    preferences: Optional[List[str]]

    
    itinerary: Optional[dict]
    current_agent: Optional[str]
    search_count: Optional[int]

    # 行程子图内部状态（原有）
    itinerary_phase: Optional[str]       # "attraction" | "weather" | "plan" | "done"
    attraction_data: Optional[List[dict]]
    weather_data: Optional[List[dict]]

    # ============ 新增字段（行程子图流转专用） ============
    itinerary_source: Optional[str]      # 行程数据来源: "amap" | "baidu"
    amap_healthy: Optional[bool]         # 高德MCP服务是否可用
    amap_error: Optional[str]            # 高德MCP最近一次错误信息
