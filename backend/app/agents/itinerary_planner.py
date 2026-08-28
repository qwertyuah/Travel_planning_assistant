"""多智能体行程规划脚本 - 独立于子图的业务逻辑层

高德多智能体流程: 景点Agent -> 天气Agent -> 酒店Agent -> 规划Agent (强校验+兜底)
百度单智能体流程: 百度搜索Agent (简单兜底)

数据隔离原则:
- 只读 state.selected_hotels 和 state.selected_transports，绝不修改
- 高德酒店数据仅作规划参考，不覆盖用户已确认的酒店
- 输出统一写入 state.itinerary，来源标记写入 state.itinerary_source
"""

import json
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta

from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage
)

from app.api.llm import llm
from app.tools.amap_tools import (
    amap_search_poi, amap_get_weather, amap_search_hotel, AmapToolError
)
from app.tools.tools import baidu_web_search_tool
from app.models.schemas import (
    TripRequest, TripPlan, DayPlan, Attraction, Meal, Location
)


ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:** 你必须使用 amap_search_poi 工具来搜索景点！不要自己编造景点信息！

**工具使用说明:**
- 工具名: amap_search_poi
- 参数: keywords (搜索关键词，如"历史文化景点"), city (城市名称，如"北京")

**示例:**
用户: "搜索北京的历史文化景点"
你应该调用: amap_search_poi(keywords="历史文化景点", city="北京")

**注意:**
1. 必须使用工具，不要直接回答
2. 根据用户偏好提炼关键词
3. 返回搜索结果的摘要信息
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:** 你必须使用 amap_get_weather 工具来查询天气！不要自己编造天气信息！

**工具使用说明:**
- 工具名: amap_get_weather
- 参数: city (城市名称，如"北京")

**示例:**
用户: "查询北京天气"
你应该调用: amap_get_weather(city="北京")

**注意:**
1. 必须使用工具，不要直接回答
2. 返回完整的天气信息，包括温度、天气状况、风向风力等
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市搜索合适的酒店。

**重要提示:** 你必须使用 amap_search_hotel 工具来搜索酒店！不要自己编造酒店信息！

**工具使用说明:**
- 工具名: amap_search_hotel
- 参数: keywords (搜索关键词，如"酒店"或"经济型酒店"), city (城市名称，如"北京")

**示例:**
用户: "搜索北京的酒店"
你应该调用: amap_search_hotel(keywords="酒店", city="北京")

**注意:**
1. 必须使用工具，不要直接回答
2. 关键词使用"酒店"或"宾馆"
3. 返回搜索结果中的酒店名称、地址、价格等信息
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息，生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划(禁止包含markdown标记，只输出纯JSON):
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. 必须包含预算信息
8. 只返回纯JSON，不要返回其他文字
"""

BAIDU_AGENT_PROMPT = """你是行程规划助手。你需要通过百度搜索获取信息来规划行程。

**工具使用说明:**
- 工具名: baidu_web_search_tool
- 参数: query (搜索关键词), result_num (返回数量，默认10)

**强制步骤:**
1. 调用 baidu_web_search_tool 一次，搜索关键词："{destination} 景点 美食 天气 穿搭"
2. 从搜索结果中提取：主要景点、特色美食、当日天气、推荐穿搭
3. 直接返回JSON格式结果(禁止包含markdown标记，只输出纯JSON)，格式如下:

{{
  "weather": "白天晴 22-28℃，夜间多云 18-20℃",
  "clothing": "建议穿短袖+薄外套，注意防晒",
  "days": [
    {{
      "date": "第1天",
      "breakfast_recommendation": "具体餐厅和菜品",
      "morning_activity": "上午景点+活动",
      "lunch_recommendation": "午餐推荐",
      "afternoon_activity": "下午景点+活动",
      "dinner_recommendation": "晚餐推荐"
    }}
  ]
}}

**规则:**
- 返回的JSON必须包含 weather, clothing, days 三个顶层字段
- days是一个数组（即使只有一天）
- 禁止输出Markdown格式，不要输出其他文字
- 如果无法获取准确天气，请根据季节给出合理推测并说明
"""

class ItineraryPlanner:
    def __init__(self):
        self.llm = llm
        self.llm_attraction = llm.bind_tools([amap_search_poi])
        self.llm_weather = llm.bind_tools([amap_get_weather])
        self.llm_hotel = llm.bind_tools([amap_search_hotel])
        self.llm_planner = llm

    async def _run_agent_loop(
        self,
        llm_with_tools,
        sys_prompt: str,
        user_msg: str,
        tool_map: Dict[str, Any],
        max_iterations: int = 5
    ) -> str:
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_msg)
        ]

        for iteration in range(max_iterations):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not (hasattr(response, "tool_calls") and response.tool_calls):
                return response.content

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_call_id = tc["id"]

                tool = tool_map.get(tool_name)
                if not tool:
                    messages.append(ToolMessage(
                        content=f"未知工具: {tool_name}",
                        tool_call_id=tool_call_id
                    ))
                    continue

                try:
                    result = await tool.ainvoke(tool_args)
                    result_str = str(result) if not isinstance(result, str) else result
                except AmapToolError:
                    raise
                except Exception as e:
                    result_str = f"工具执行失败: {e}"

                messages.append(ToolMessage(
                    content=result_str,
                    tool_call_id=tool_call_id
                ))

        return "达到最大迭代次数，未能完成行程规划。"

    async def run_amap(self, state: dict) -> dict:
        destination = state.get("destination", "未知")
        start_date = state.get("start_date", "")
        end_date = state.get("end_date", "")
        selected_hotels = state.get("selected_hotels", [])
        selected_transports = state.get("selected_transports", [])

        preferences = state.get("preferences", [])
        if isinstance(preferences, str):
            preferences = [preferences]

        try:
            travel_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
        except ValueError:
            travel_days = 1

        request = TripRequest(
            city=destination,
            start_date=start_date,
            end_date=end_date,
            travel_days=travel_days,
            preferences=preferences,
            transportation=state.get("transportation", "公共交通"),
            accommodation=state.get("accommodation", "经济型酒店")
        )

        print(f"  [高德流程] 步骤1/4: 搜索景点 - {destination}")
        attraction_result = await self._run_agent_loop(
            self.llm_attraction,
            ATTRACTION_AGENT_PROMPT,
            f"请搜索{destination}的景点",
            {"amap_search_poi": amap_search_poi}
        )
        print(f"  [高德流程] 景点搜索完成，长度={len(attraction_result)}")

        print(f"  [高德流程] 步骤2/4: 查询天气 - {destination}")
        weather_result = await self._run_agent_loop(
            self.llm_weather,
            WEATHER_AGENT_PROMPT,
            f"请查询{destination}的天气",
            {"amap_get_weather": amap_get_weather}
        )
        print(f"  [高德流程] 天气查询完成，长度={len(weather_result)}")

        print(f"  [高德流程] 步骤3/4: 搜索酒店 - {destination}")
        hotel_result = await self._run_agent_loop(
            self.llm_hotel,
            HOTEL_AGENT_PROMPT,
            f"请搜索{destination}的酒店",
            {"amap_search_hotel": amap_search_hotel}
        )
        print(f"  [高德流程] 酒店搜索完成，长度={len(hotel_result)}")

        print(f"  [高德流程] 步骤4/4: 生成行程计划")
        planner_input = self._build_planner_input(
            request, selected_hotels, selected_transports,
            attraction_result, weather_result, hotel_result
        )

        messages = [
            SystemMessage(content=PLANNER_AGENT_PROMPT),
            HumanMessage(content=planner_input)
        ]
        planner_response = await self.llm_planner.ainvoke(messages)
        response_text = planner_response.content if hasattr(planner_response, "content") else str(planner_response)

        trip_plan = self._parse_response(response_text, request)
        print(f"  [高德流程] 行程规划完成")

        return {
            "itinerary": trip_plan.model_dump(),
            "itinerary_source": "amap",
            "attraction_data": [{"raw": attraction_result}],
            "weather_data": [{"raw": weather_result}],
        }

    async def run_baidu(self, state: dict) -> dict:
        destination = state.get("destination", "未知")
        llm_baidu = self.llm.bind_tools([baidu_web_search_tool])

        print(f"  [百度流程] 搜索综合信息 - {destination}")
        result = await self._run_agent_loop(
            llm_baidu,
            BAIDU_AGENT_PROMPT.format(destination=destination),
            f"请为{destination}规划行程，搜索景点、美食、天气、穿搭信息",
            {"baidu_web_search_tool": baidu_web_search_tool}
        )
        print(f"  [百度流程] 行程生成完成，长度={len(result)}")

        itinerary = self._parse_json(result)

        if not isinstance(itinerary, dict):
            itinerary = {"raw_text": result}
        itinerary.setdefault("weather", "天气信息暂缺")
        itinerary.setdefault("clothing", "建议穿着舒适衣物")
        if "days" not in itinerary or not isinstance(itinerary.get("days"), list):
            itinerary["days"] = [{
                "date": "第1天",
                "breakfast_recommendation": "当地特色早餐",
                "morning_activity": "游览主要景点",
                "lunch_recommendation": "当地特色午餐",
                "afternoon_activity": "继续游览",
                "dinner_recommendation": "当地特色晚餐"
            }]

        return {
            "itinerary": itinerary,
            "itinerary_source": "baidu",
        }

    async def close(self):
        """显式关闭 MCP 会话，避免跨任务退出 cancel scope"""
        from app.tools.amap_tools import amap_manager
        print("🔄 正在关闭 ItineraryPlanner 底层 MCP 资源...")
        await amap_manager.cleanup()
        print("✅ ItineraryPlanner MCP 资源已关闭")


    def _build_planner_input(
        self,
        request: TripRequest,
        selected_hotels: list,
        selected_transports: list,
        attraction_result: str,
        weather_result: str,
        hotel_result: str
    ) -> str:
        if selected_hotels:
            hotel_parts = []
            for h in selected_hotels:
                hotel_parts.append(
                    f"  - {h.get('name', '未知')} "
                    f"(入住{h.get('check_in', '?')}-离店{h.get('check_out', '?')}, "
                    f"价格{h.get('price', '?')}元)"
                )
            hotel_info = "\n".join(hotel_parts)
        else:
            hotel_info = "未确认酒店，请参考高德搜索结果推荐"

        if selected_transports:
            transport_parts = []
            for t in selected_transports:
                direction = "去程" if t.get("direction") == "outbound" else "返程"
                transport_parts.append(
                    f"  - [{direction}] {t.get('name', '未知')} "
                    f"{t.get('from', '?')}->{t.get('to', '?')} "
                    f"时间{t.get('time', '?')} 票价{t.get('price', '?')}元"
                )
            transport_info = "\n".join(transport_parts)
        else:
            transport_info = "未确认交通"

        return f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**用户已确认的交通:**
{transport_info}

**用户已确认的酒店:**
{hotel_info}

**高德地图景点搜索结果:**
{attraction_result}

**高德地图天气查询结果:**
{weather_result}

**高德地图酒店搜索结果（供规划参考，不替代用户已确认的酒店）:**
{hotel_result}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 优先使用用户已确认的酒店，若未确认则从高德搜索结果中推荐
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
6. 景点的经纬度坐标要真实准确
7. 必须包含预算信息
"""

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        try:
            json_str = None
            m1 = re.search(r'\x60\x60\x60json\s*(\{[\s\S]*?\})\s*\x60\x60\x60', response)
            if m1:
                json_str = m1.group(1)
            else:
                m2 = re.search(r'\x60\x60\x60\s*(\{[\s\S]*?\})\s*\x60\x60\x60', response)
                if m2:
                    json_str = m2.group(1)
                else:
                    start = response.find('{')
                    end = response.rfind('}')
                    if start != -1 and end > start:
                        json_str = response[start:end + 1]

            if not json_str:
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            return TripPlan(**data)

        except Exception as e:
            print(f"  [高德流程] 解析行程计划失败: {str(e)}，将使用备用方案")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01, latitude=39.9 + i*0.01),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    ) for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        if not text:
            return {}
        m1 = re.search(r'```\s*(\{[\s\S]*?\})\s*```', text)
        if m1:
            try:
                return json.loads(m1.group(1))
            except json.JSONDecodeError:
                pass
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"raw_text": text}


_itinerary_planner = None

def get_itinerary_planner() -> ItineraryPlanner:
    global _itinerary_planner
    if _itinerary_planner is None:
        _itinerary_planner = ItineraryPlanner()
    return _itinerary_planner
