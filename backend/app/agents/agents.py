import re
import json
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.models.state_definitions import TravelState
from app.api.llm import llm
from app.tools.tools import search_transport_api, search_hotel_api, confirm_transport, confirm_hotel, baidu_web_search_tool, submit_final_itinerary
from .helpers import get_recent_messages, should_continue, transport_should_continue

# --- 交通子图 ---
transport_tools = [search_transport_api, confirm_transport]
llm_transport = llm.bind_tools(transport_tools)
async def transport_agent_node(state):
    print("\n--- [交通子图] Agent 思考中...")
    try:
        msgs = state.get('messages', [])
        print(f"[DEBUG transport_agent_node] messages_count={len(msgs)} last_types={[type(m).__name__ for m in msgs[-3:]]}")
    except Exception as e:
        print("[DEBUG transport_agent_node] 无法读取 messages", e)
    if state.get("selected_transport"):
        selected = state["selected_transport"]
        seat_info = f"（{selected.get('seat_type', '默认座位')}）" if selected.get('seat_type') else ""
        reply = f"✅ 预订成功！您已成功预订 {selected['name']}{seat_info}，价格 {selected['price']} 元。祝您旅途愉快！"
        return {"messages": [AIMessage(content=reply)], "current_agent": "transport"}
        
    sys_prompt = SystemMessage(content=f"""
    你是交通规划专员。目的地:{state.get('destination', '未知')} 出行日期:{state.get('start_date', '未知')} 已订交通段数:{len(state.get('selected_transports', []))} 阶段:{state.get('current_booking_step', 'outbound')}(outbound=去程 return=返程)
    规则:
    1. 查交通: 必须调用 search_transport_api 工具。
    2. 展示结果: 清晰展示类型、名称、时间、价格、座位等。提示用户提供ID和座位(高铁)。
    3. 确认: 用户选择后调用 confirm_transport，必须传入 selection_id, transport_name, price, time_range, origin, destination, direction。
    4. 多段行程: 用户确认去程后继续问返程，则direction=return，并交换origin/destination。
    5. 无结果: 友好告知可能原因，建议调整条件。
    执行用户最新消息。
    """)
    recent_msgs = get_recent_messages(state['messages'])
    response = await llm_transport.ainvoke([sys_prompt] + recent_msgs)
    return {"messages": [response], "current_agent": "transport"}

async def transport_tool_node(state):
    last_message = state['messages'][-1]
    print(f"[DEBUG transport_tool_node] last_message_type={type(last_message).__name__} content={getattr(last_message,'content',None)}")
    tool_calls = last_message.tool_calls
    tool_messages = []
    new_state_updates = {}
    for tc in tool_calls:
        if tc["name"] == "search_transport_api":
            res = await search_transport_api.ainvoke(tc["args"])
            tool_messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"]))
            new_state_updates["transport_options"] = res
        elif tc["name"] == "confirm_transport":
            args = tc["args"]
            sel_id = args.get("selection_id")
            seat_type = args.get("seat_type")
            price = args.get("price")
            transport_name = args.get("transport_name")
            time_range = args.get("time_range")
            origin = args.get("origin")
            destination = args.get("destination")
            direction = args.get("direction", "outbound")
            if transport_name and price and time_range and origin and destination:
                selected_item = {
                    "id": sel_id,
                    "name": transport_name,
                    "type": "高铁" or "动车" or "火车" if seat_type else "飞机",
                    "price": price,
                    "time": time_range,
                    "from": origin,
                    "to": destination,
                    "seat_type": seat_type if seat_type else "默认",
                    "direction": direction
                }
                existing = state.get("selected_transports")
                if existing is None:
                    existing = []
                new_state_updates["selected_transports"] = existing + [selected_item]
                reply = f"已成功预订: {transport_name} {seat_type if seat_type else ''} (方向: {direction})"
            else:
                options = state.get("transport_options", [])
                selected_item = next((item for item in options if item.get("id") == sel_id), None)
                if selected_item:
                    selected_copy = selected_item.copy()
                    if seat_type:
                        selected_copy["seat_type"] = seat_type
                    if price:
                        selected_copy["price"] = price
                    selected_copy["direction"] = direction
                    new_state_updates["selected_transports"] = state.get("selected_transports", []) + [selected_copy]
                    reply = f"已成功预订: {selected_item['name']} (方向: {direction})"
                else:
                    reply = f"预订失败，未找到ID {sel_id}"
            new_state_updates["transport_options"] = None
            tool_messages.append(ToolMessage(content=reply, tool_call_id=tc["id"]))
    return {"messages": tool_messages, **new_state_updates}

transport_graph = StateGraph(TravelState)
transport_graph.add_node("agent", transport_agent_node)
transport_graph.add_node("tools", transport_tool_node)
transport_graph.set_entry_point("agent")
transport_graph.add_conditional_edges("agent", transport_should_continue, {"tools": "tools", END: END})
transport_graph.add_edge("tools", "agent")
transport_subgraph = transport_graph.compile()

# --- 酒店子图 ---
hotel_tools = [search_hotel_api, confirm_hotel]
llm_hotel = llm.bind_tools(hotel_tools)
async def hotel_agent_node(state):
    print("\n--- [酒店子图] Agent 思考中...")
    booked_count = len(state.get("selected_hotels", []))
    sys_prompt = SystemMessage(content=f"""
    你是酒店预订专员。目的地:{state.get('destination', '未知')} 出发日期:{state.get('start_date', '未知')} 已预订酒店数:{booked_count}
    规则:
    1. 查询酒店: 调用 search_hotel_api，参数 city, check_in, check_out。
    2. 展示结果: 清晰展示酒店名、地址、商圈、评分、价格、房型、窗户类型。提示用户输入ID选择。
    3. 确认: 用户选择后调用 confirm_hotel，必须传入 selection_id, hotel_name, check_in, check_out, price。
    4. 多段行程: 支持存储多个订单。
    执行用户最新消息。
    """)
    recent_msgs = get_recent_messages(state['messages'])
    response = await llm_hotel.ainvoke([sys_prompt] + recent_msgs)
    return {"messages": [response], "current_agent": "hotel"}

async def hotel_tool_node(state):
    last_message = state['messages'][-1]
    tool_calls = last_message.tool_calls
    tool_messages = []
    new_state_updates = {}
    for tc in tool_calls:
        if tc["name"] == "search_hotel_api":
            res = await search_hotel_api.ainvoke(tc["args"])
            tool_messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"]))
            new_state_updates["hotel_options"] = res
        elif tc["name"] == "confirm_hotel":
            args = tc["args"]
            selected_item = {
                "id": args.get("selection_id"),
                "name": args.get("hotel_name"),
                "check_in": args.get("check_in"),
                "check_out": args.get("check_out"),
                "price": args.get("price"),
                "type": "酒店"
            }
            current_list = state.get("selected_hotels", [])
            new_state_updates["selected_hotels"] = current_list + [selected_item]
            new_state_updates["hotel_options"] = None
            reply = f"✅ 预订成功！已确认: {selected_item['name']} ({selected_item['check_in']} 至 {selected_item['check_out']})"
            tool_messages.append(ToolMessage(content=reply, tool_call_id=tc["id"]))
    return {"messages": tool_messages, **new_state_updates}

hotel_graph = StateGraph(TravelState)
hotel_graph.add_node("agent", hotel_agent_node)
hotel_graph.add_node("tools", hotel_tool_node)
hotel_graph.set_entry_point("agent")
hotel_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
hotel_graph.add_edge("tools", "agent")
hotel_subgraph = hotel_graph.compile()

# --- 行程子图 ---

"""行程子图：高德优先 + 条件决策降级百度

核心逻辑：
1. 优先执行高德多智能体流程
2. 若高德 MCP 不可用或执行中抛出 AmapToolError，自动降级到百度搜索流程
3. 数据隔离：子图只读 state 中的酒店/交通确认信息，输出写入隔离字段
"""

from typing import Dict, Any, Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END

from app.agents.itinerary_planner import get_itinerary_planner, AmapToolError


class ItineraryState(TypedDict):
    """行程子图状态定义"""
    destination: str
    start_date: str
    end_date: str
    preferences: list
    transportation: str
    accommodation: str
    
    selected_hotels: list
    selected_transports: list
    
    amap_healthy: bool
    itinerary: dict
    itinerary_source: str
    amap_raw_data: dict

planner = get_itinerary_planner()


async def amap_itinerary(state: ItineraryState) -> Dict[str, Any]:
    print("\n[行程子图] 节点: amap_itinerary - 执行高德多智能体流程（试错降级）")
    try:
        result = await planner.run_amap(state)
        print("[行程子图] 高德流程执行成功")
        return result
    except AmapToolError as e:
        print(f"[行程子图] 高德流程失败(AmapToolError): {e}，降级到百度")
        # 标记高德不可用，但不直接调用百度，由路由决定
        return {
            "amap_healthy": False,
            "itinerary": None,
            "itinerary_source": None,
            "amap_raw_data": None,
        }
    except Exception as e:
        print(f"[行程子图] 高德流程未知异常: {e}，降级到百度")
        return {
            "amap_healthy": False,
            "itinerary": None,
            "itinerary_source": None,
            "amap_raw_data": None,
        }


async def baidu_itinerary(state: ItineraryState) -> Dict[str, Any]:
    print("\n[行程子图] 节点: baidu_itinerary - 执行百度搜索降级流程")
    try:
        result = await planner.run_baidu(state)
        print("[行程子图] 百度流程执行成功")
        return result
    except Exception as e:
        print(f"[行程子图] 百度流程异常: {e}")
        return {
            "itinerary": {"raw_text": "行程规划失败，请稍后重试"},
            "itinerary_source": "error",
        }


def route_after_amap(state: ItineraryState) -> Literal["baidu_itinerary", "__end__"]:
    # 如果高德成功，直接结束
    if state.get("itinerary_source") == "amap" and state.get("itinerary"):
        print("[行程子图] 路由: 高德成功 -> END")
        return END
    # 否则降级到百度
    print("[行程子图] 路由: 高德失败 -> 降级 baidu_itinerary")
    return "baidu_itinerary"



def create_itinerary_subgraph():
    workflow = StateGraph(ItineraryState)

    workflow.add_node("amap_itinerary", amap_itinerary)
    workflow.add_node("baidu_itinerary", baidu_itinerary)

    workflow.set_entry_point("amap_itinerary")

    workflow.add_conditional_edges(
        "amap_itinerary",
        route_after_amap,
        {
            "baidu_itinerary": "baidu_itinerary",
            END: END
        }
    )

    workflow.add_edge("baidu_itinerary", END)
    return workflow.compile()

itinerary_subgraph = create_itinerary_subgraph()


# ---- 在 agents.py 末尾，新增：用于主图调用的行程子图入口 ----
async def call_itinerary_subgraph(state: TravelState):
    """
    主图调用行程子图的适配节点：
    - 把 TravelState 映射成 ItineraryState
    - 调用 itinerary_subgraph
    - 把结果写回 TravelState
    """
    # 构建子图输入
    itinerary_input = {
        "destination": state.get("destination", "未知"),
        "start_date": state.get("start_date", ""),
        "end_date": state.get("end_date", ""),
        "preferences": state.get("preferences", []),
        "transportation": "",  # 可以后续补充
        "accommodation": "",   # 可以后续补充
        "selected_hotels": state.get("selected_hotels", []),
        "selected_transports": state.get("selected_transports", []),
        "amap_healthy": True,  # 默认健康，子图内部会自己判断
        "itinerary": None,
        "itinerary_source": None,
        "amap_raw_data": None,
    }
    # 调用子图
    sub_out = await itinerary_subgraph.ainvoke(itinerary_input)
    # 把子图结果写回 TravelState
    updates = {
        "itinerary": sub_out.get("itinerary"),
        "itinerary_source": sub_out.get("itinerary_source"),
        "amap_raw_data": sub_out.get("amap_raw_data"),
    }
    # 如果子图里还更新了其他字段（如 selected_hotels），也可以一并写回
    if sub_out.get("selected_hotels") is not None:
        updates["selected_hotels"] = sub_out["selected_hotels"]
    if sub_out.get("selected_transports") is not None:
        updates["selected_transports"] = sub_out["selected_transports"]
    return updates