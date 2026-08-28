"""多智能体行程规划脚本 - 独立于子图的业务逻辑层

高德多智能体流程: 景点Agent -> 天气Agent -> 酒店Agent -> 规划Agent
百度单智能体流程: 百度搜索Agent

数据隔离原则:
- 只读 state.selected_hotels 和 state.selected_transports，绝不修改
- 高德酒店数据仅作规划参考，不覆盖用户已确认的酒店
- 输出统一写入 state.itinerary，来源标记写入 state.itinerary_source
"""

import json
import re
from typing import Dict, Any, List

from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage
)

from app.api.llm import llm
from app.tools.amap_tools import (
    amap_search_poi, amap_get_weather, amap_search_hotel, AmapToolError
)
from app.tools.tools import baidu_web_search_tool


# ============ 系统提示词（复用 helloagent，适配 LangChain，移除反引号防解析错误） ============

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

请严格按照以下JSON格式返回旅行计划(禁止包含markdown标记或反引号，只输出纯JSON):
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
3. 直接返回JSON格式结果(禁止包含markdown标记或反引号，只输出纯JSON)，格式如下:

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

# ============ 核心编排类 ============

class ItineraryPlanner:
    """行程规划编排器 - 统一管理高德/百度两条流程"""

    def __init__(self):
        self.llm = llm
        # 高德子Agent（各自绑定对应工具）
        self.llm_attraction = llm.bind_tools([amap_search_poi])
        self.llm_weather = llm.bind_tools([amap_get_weather])
        self.llm_hotel = llm.bind_tools([amap_search_hotel])
        self.llm_planner = llm  # 规划Agent无需工具

    # ============ 通用Agent执行器 ============

    async def _run_agent_loop(
        self,
        llm_with_tools,
        sys_prompt: str,
        user_msg: str,
        tool_map: Dict[str, Any],
        max_iterations: int = 5
    ) -> str:
        """通用Agent执行器: ReAct循环

        调用工具直到得到最终文本回复。
        高德工具抛出AmapToolError时，立即向上传播。

        Args:
            llm_with_tools: 绑定了工具的LLM实例
            sys_prompt: 系统提示词
            user_msg: 用户消息
            tool_map: 工具名到工具实例的映射
            max_iterations: 最大迭代次数

        Returns:
            Agent的最终文本回复

        Raises:
            AmapToolError: 高德工具调用失败时向上抛出
        """
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_msg)
        ]

        for iteration in range(max_iterations):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            # 无工具调用 -> 返回文本回复
            if not (hasattr(response, "tool_calls") and response.tool_calls):
                return response.content

            # 执行所有工具调用
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
                    raise  # 高德异常，向上传播，由步骤四节点捕获降级
                except Exception as e:
                    result_str = f"工具执行失败: {e}"

                messages.append(ToolMessage(
                    content=result_str,
                    tool_call_id=tool_call_id
                ))

        return "达到最大迭代次数，未能完成行程规划。"

    # ============ 高德多智能体流程 ============

    async def run_amap(self, state: dict) -> dict:
        """高德多智能体流程: 景点->天气->酒店->规划

        任一环节抛出AmapToolError，立即终止并向上抛出，
        由行程子图节点捕获后降级到百度流程。

        数据隔离:
        - 仅读取 state.selected_hotels / selected_transports
        - 高德酒店结果仅作规划参考，不写入 state

        Returns:
            dict: 包含 itinerary, itinerary_source, attraction_data, weather_data
        """
        destination = state.get("destination", "未知")
        start_date = state.get("start_date", "")
        selected_hotels = state.get("selected_hotels", [])
        selected_transports = state.get("selected_transports", [])

        # ---- 1. 景点搜索Agent ----
        print(f"  [高德流程] 步骤1/4: 搜索景点 - {destination}")
        attraction_result = await self._run_agent_loop(
            self.llm_attraction,
            ATTRACTION_AGENT_PROMPT,
            f"请搜索{destination}的景点",
            {"amap_search_poi": amap_search_poi}
        )
        print(f"  [高德流程] 景点搜索完成，长度={len(attraction_result)}")

        # ---- 2. 天气查询Agent ----
        print(f"  [高德流程] 步骤2/4: 查询天气 - {destination}")
        weather_result = await self._run_agent_loop(
            self.llm_weather,
            WEATHER_AGENT_PROMPT,
            f"请查询{destination}的天气",
            {"amap_get_weather": amap_get_weather}
        )
        print(f"  [高德流程] 天气查询完成，长度={len(weather_result)}")

        # ---- 3. 酒店搜索Agent（仅供参考，绝不覆盖selected_hotels）----
        print(f"  [高德流程] 步骤3/4: 搜索酒店 - {destination}")
        hotel_result = await self._run_agent_loop(
            self.llm_hotel,
            HOTEL_AGENT_PROMPT,
            f"请搜索{destination}的酒店",
            {"amap_search_hotel": amap_search_hotel}
        )
        print(f"  [高德流程] 酒店搜索完成，长度={len(hotel_result)}")

        # ---- 4. 行程规划Agent ----
        print(f"  [高德流程] 步骤4/4: 生成行程计划")
        planner_input = self._build_planner_input(
            destination, start_date,
            selected_hotels, selected_transports,
            attraction_result, weather_result, hotel_result
        )
        plan_result = await self._run_agent_loop(
            self.llm_planner,
            PLANNER_AGENT_PROMPT,
            planner_input,
            {}  # 规划Agent无工具
        )
        print(f"  [高德流程] 行程规划完成，长度={len(plan_result)}")

        # 解析JSON
        itinerary = self._parse_json(plan_result)

        return {
            "itinerary": itinerary,
            "itinerary_source": "amap",
            "attraction_data": [{"raw": attraction_result}],
            "weather_data": [{"raw": weather_result}],
        }

    # ============ 百度单智能体流程 ============

    async def run_baidu(self, state: dict) -> dict:
        destination = state.get("destination", "未知")

        # 惰性加载：仅在需要时绑定百度搜索工具
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


    # ============ 辅助方法 ============

    def _build_planner_input(
        self,
        destination: str,
        start_date: str,
        selected_hotels: list,
        selected_transports: list,
        attraction_result: str,
        weather_result: str,
        hotel_result: str
    ) -> str:
        """构建规划Agent的输入上下文

        严格遵循数据隔离: selected_hotels/transports 仅拼入文本，绝不回写
        """
        # ---- 用户已确认的酒店（只读） ----
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

        # ---- 用户已确认的交通（只读） ----
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

        return f"""请根据以下信息生成{destination}的旅行计划:

**基本信息:**
- 城市: {destination}
- 出发日期: {start_date}

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

    @staticmethod
    def _parse_json(text: str) -> dict:
        if not text:
            return {}
        m2 = re.search(r'```\s*(\{[\s\S]*?\})\s*```', text)
        if m2:
            try:
                return json.loads(m2.group(1))
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
    """获取行程规划编排器实例(单例)"""
    global _itinerary_planner
    if _itinerary_planner is None:
        _itinerary_planner = ItineraryPlanner()
    return _itinerary_planner
