from datetime import datetime, timedelta
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.models.state_definitions import TravelState
from app.agents.agents import transport_subgraph, hotel_subgraph, call_itinerary_subgraph

import json
import re
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage
from app.api.llm import llm
EXTRACT_SYSTEM_PROMPT = """你是旅行需求提取助手。从用户对话中提取以下信息，严格按JSON输出：
{
  "intent": "意图分类，必须是 transport/hotel/itinerary 之一",
  "origin": "出发城市",
  "destination": "目的地城市",
  "start_date": "出发日期(YYYY-MM-DD)",
  "travel_days": "旅行天数(整数)",
  "budget": "预算(整数,元)",
  "preferences": ["兴趣标签1", "兴趣标签2"]
}
规则：
1. 意图判断：查票/高铁/飞机/大巴等选transport；酒店/住宿/宾馆等选hotel；游玩/行程/规划/旅游等选itinerary。
2. 只输出纯JSON，不要markdown标记，无法判断填null。
3. 根据系统提供的当前日期推算相对时间。"""

async def entry_node(state):
    current_date = datetime.now().strftime("%Y-%m-%d")
    dynamic_prompt = EXTRACT_SYSTEM_PROMPT + f"\n当前日期：{current_date}"
    user_msg = state['messages'][-1].content
    messages = [
        SystemMessage(content=dynamic_prompt),
        HumanMessage(content=user_msg)
    ]
    response = await llm.ainvoke(messages)
    text = response.content
    data = {}
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
    # 提取意图，默认为 itinerary
    intent = data.get("intent") or "itinerary"
    # 提取出发地和目的地
    origin = data.get("origin") or "未知"
    dest = data.get("destination") or "未知"
    
    start_date = data.get("start_date") or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    travel_days = data.get("travel_days") or 2
    budget = data.get("budget") or 5000
    prefs = data.get("preferences") or []
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=int(travel_days) - 1)
        end_date = end_dt.strftime("%Y-%m-%d")
    except Exception:
        end_date = start_date
    # ... 前面的提取逻辑保持不变 ...

    print(f"-> [主图] 提取结果: 意图={intent}, 出发地={origin}, 目的地={dest}, 日期={start_date}~{end_date}")

    updates = {
        "intent": intent,
        "origin": origin,
        "destination": dest,
        "start_date": start_date,
        "end_date": end_date,
        "budget": float(budget),
        "preferences": prefs,
        "current_agent": None,
        "current_booking_step": None
    }
    
    # 核心修复：仅在状态中还没有这些列表时才初始化，绝不覆盖已有数据
    if state.get("selected_transports") is None:
        updates["selected_transports"] = []
    if state.get("selected_hotels") is None:
        updates["selected_hotels"] = []

    return updates


from langchain_core.messages import HumanMessage

def route_intent(state):
    # 1. 优先看 LLM 提取的 intent 字段
    intent = state.get("intent")
    if intent == "transport":
        return "transport_flow"
    if intent == "hotel":
        return "hotel_flow"
    if intent == "itinerary":
        return "itinerary_flow"
    # 2. 如果没有 intent，再看消息内容做兜底
    last_msg = state['messages'][-1]
    if isinstance(last_msg, HumanMessage):
        text = last_msg.content.lower()
        if any(k in text for k in ["高铁", "火车", "飞机", "汽车", "票", "查票"]):
            return "transport_flow"
        if any(k in text for k in ["酒店", "住宿", "宾馆"]):
            return "hotel_flow"
        if any(k in text for k in ["行程", "规划", "游玩", "旅游"]):
            return "itinerary_flow"
    # 3. 都没命中，按默认完整性兜底
    if not state.get("selected_transports"):
        return "transport_flow"
    if not state.get("selected_hotels"):
        return "hotel_flow"
    if not state.get("itinerary"):
        return "itinerary_flow"
    return END

main_builder = StateGraph(TravelState)
main_builder.add_node("entry", entry_node)
main_builder.add_node("transport_flow", transport_subgraph)
main_builder.add_node("hotel_flow", hotel_subgraph)
main_builder.add_node("itinerary_flow", call_itinerary_subgraph)
main_builder.set_entry_point("entry")
main_builder.add_conditional_edges("entry", route_intent)
main_builder.add_edge("transport_flow", END)
main_builder.add_edge("hotel_flow", END)
main_builder.add_edge("itinerary_flow", END)

checkpointer = MemorySaver()
app_graph = main_builder.compile(checkpointer=checkpointer)

# 在 app_graph 编译之后添加

def visualize_graph(graph, output_file="graph.png"):
    """尝试生成 PNG 图片，如果环境不支持则保存 Mermaid 代码"""
    try:
        # 尝试生成 PNG（需要安装 graphviz 和 pydot）
        png_data = graph.get_graph().draw_mermaid_png()
        with open(output_file, "wb") as f:
            f.write(png_data)
        print(f"✅ 图已保存为 {output_file}")
    except Exception as e:
        print(f"⚠️ 无法生成 PNG: {e}")
        # 降级：输出 Mermaid 代码
        mermaid_code = graph.get_graph().draw_mermaid()
        with open(output_file.replace(".png", ".mmd"), "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"✅ Mermaid 代码已保存为 {output_file.replace('.png', '.mmd')}")
        # print("您可以使用 https://mermaid.live  ️ 在线查看")

# 可视化主图
# visualize_graph(app_graph, "travel_planner_graph_1.png")

# from IPython.display import Image, display
# display(Image(app_graph.get_graph().draw_mermaid_png()))

# 如果要单独查看子图，也可以：
# visualize_graph(transport_subgraph, "transport_subgraph.png")
# visualize_graph(hotel_subgraph, "hotel_subgraph.png")
# visualize_graph(itinerary_subgraph, "itinerary_subgraph.png")
# 在您的脚本末尾添加
# 或保存子图的 Mermaid