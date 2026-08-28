import asyncio
import json
from typing import Optional
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langchain_community.tools import DuckDuckGoSearchRun
from app.api.tuniu_cli import tuniu_manager
from duckduckgo_search import DDGS

@tool
async def search_transport_api(
    origin: str,
    destination: str,
    date: str,
    mode: Optional[str] = None,
    origin_station: Optional[str] = None,
    direction: str = "outbound"
) -> list:
    """查询出发地到目的地的交通方案（飞机/火车）。
    - 必须传入 origin（出发城市）、destination（到达城市）、date（出发日期，格式 YYYY-MM-DD）。
    - mode 可选值："flight"（仅飞机）、"train"（仅火车），不传则同时查询。
    - origin_station 用于指定具体出发站点（如"北京南"），不传则返回所有站点方案。
    - direction 表示行程方向："outbound"（去程）或"return"（返程）。当用户询问返程时，应设为"return"。
    - 返回结果列表，每项包含类型、名称、价格、时间、起终点等字段。
    调用时机：用户明确需要查询交通方案时调用。
    """
    print(f"-> [真实调用] 交通查询: mode={mode}, {origin} -> {destination} | {date}, 方向={direction}")
    async def query_flight():
        return await asyncio.to_thread(tuniu_manager.get_flights, origin, destination, date)
    async def query_train():
        return await asyncio.to_thread(tuniu_manager.get_trains, origin, destination, date)
    flights = []
    trains = []
    if mode is None or mode == "flight":
        try:
            flights = await query_flight()
        except Exception as e:

            print(f"查询飞机出错: {e}")
    if mode is None or mode == "train":
        try:
            trains = await query_train()
        except Exception as e:
            print(f"查询火车出错: {e}")
    all_items = []
    for idx, flight in enumerate(flights, start=1):
        flight["id"] = idx
        if "type" not in flight:
            flight["type"] = "飞机"
        flight["direction"] = direction
        all_items.append(flight)
    base_id = len(flights) + 1
    for idx, train in enumerate(trains, start=base_id):
        train["id"] = idx
        train["direction"] = direction
        if "seats" not in train:
            train["seats"] = []
        all_items.append(train)
    if origin_station:
        keywords = origin_station.replace("站", "").replace("机场", "").strip()
        filtered = []
        for item in all_items:
            from_loc = item.get("from", "")
            if keywords in from_loc:
                filtered.append(item)
        if not filtered:
            print(f"⚠️ 未找到从 {origin_station} 出发的方案")
        all_items = filtered
    return all_items

"""args_schema={
    "city": {"description": "城市名称"},
    "check_in": {"description": "入住日期 YYYY-MM-DD"},
    "check_out": {"description": "离店日期 YYYY-MM-DD"},
    "price_range": {"description": "价格区间，如'200-500'", "default": None},
    "keyword": {"description": "酒店名关键词", "default": None}
}"""
@tool()
async def search_hotel_api(
    city: str,
    check_in: str,
    check_out: str,
    price_range: Optional[str] = None,
    keyword: Optional[str] = None
) -> list:
    """
    
    查询酒店，返回酒店列表。每项包含：酒店名、地址、评分、最低价、房型、窗户类型。"""
    print(f"-> [真实调用] 酒店查询: {city}, {check_in} - {check_out}, 价格: {price_range}")
    hotels = await asyncio.to_thread(
        tuniu_manager.get_hotels, city, check_in, check_out, price_range, keyword
    )
    return hotels

@tool
async def confirm_transport(
    selection_id: int,
    seat_type: str = None,
    price: int = None,
    transport_name: str = None,
    time_range: str = None,
    origin: str = None,
    destination: str = None,
    direction: str = "outbound"
) -> str:
    """构建并返回交通确认字符串（供系统解析）。"""
    parts = [
        f"id={selection_id}",
        f"name={transport_name or '未知'}",
        f"price={price or 0}",
        f"time={time_range or ''}",
        f"from={origin or ''}",
        f"to={destination or ''}",
        f"dir={direction}"
    ]
    if seat_type:
        parts.append(f"seat={seat_type}")
    confirm_str = "CONFIRMED|" + "|".join(parts)
    return confirm_str

@tool
def confirm_hotel(selection_id: int, hotel_name: str, check_in: str, check_out: str, price: int) -> str:
    """构建并返回酒店确认字符串（供系统解析）。"""
    return f"CONFIRMED_HOTEL|id={selection_id}|name={hotel_name}|checkin={check_in}|checkout={check_out}|price={price}"


import os
import json
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

BAIDU_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY")

def call_baidu_search(query: str, top_k: int = 10) -> list:
    """
    调用百度搜索API，返回结果列表（references）。
    """
    if not BAIDU_API_KEY:
        raise ValueError("请设置环境变量 BAIDU_API_KEY")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BAIDU_API_KEY}"
    }
    payload = {
        "messages": [{"role": "user", "content": query}],
        "search_source": "baidu_search_v2",
        "resource_type_filter": [{"type": "web", "top_k": top_k}]
    }
    try:
        resp = requests.post(BAIDU_SEARCH_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("references", [])
    except Exception as e:
        print(f"百度搜索失败: {e}")
        return []

def format_references(references: list) -> str:
    """
    将百度返回的 references 格式化为易读文本
    """
    if not references:
        return "未找到相关信息。"
    lines = []
    for idx, ref in enumerate(references, 1):
        title = ref.get("title", "无标题")
        content = ref.get("content", "无摘要")
        url = ref.get("url", "")
        lines.append(f"{idx}. {title}\n   摘要：{content}\n   链接：{url}")
    return "\n\n".join(lines)

@tool
def baidu_web_search_tool(query: str, result_num: int = 10) -> str:
    """
    使用百度搜索获取实时旅游信息（景点、美食、天气、交通、穿搭建议）。
    当你需要规划行程或查询某地信息时，务必使用此工具。
    建议搜索关键词格式：“目的地+一日游 景点 美食 天气”，例如“重庆一日游 景点 美食 天气”。
    
    参数:
    - query: 搜索关键词，如“重庆一日游 景点 美食 天气”
    - result_num: 返回结果数量，默认10条，最多30条。
    """
    print(f"\n-> [百度搜索] 正在搜索: {query} (请求{result_num}条)")
    if result_num > 30:
        result_num = 30
    refs = call_baidu_search(query, top_k=result_num)
    if refs:
        return format_references(refs)
    else:
        return "百度搜索未返回结果，请稍后重试或更换关键词。"



# def _search_sync(query: str) -> str:
#     """
#     同步搜索函数（由线程池执行），包含重试逻辑。
#     """
#     MAX_RETRIES = 3
#     for attempt in range(MAX_RETRIES):
#         try:
#             with DDGS() as ddgs:
#                 # 获取最多3条结果，timeout 10秒
#                 results = list(ddgs.text(query, max_results=3, timeout=10))
#                 if not results:
#                     return "未找到相关信息。"
#                 formatted = []
#                 for idx, r in enumerate(results, 1):
#                     title = r.get("title", "")
#                     body = r.get("body", "")
#                     formatted.append(f"{idx}. {title}：{body}")
#                 return "\n".join(formatted)[:2000]
#         except Exception as e:
#             if attempt == MAX_RETRIES - 1:
#                 return f"搜索失败：{str(e)}"
#             # 同步重试等待（不用 asyncio.sleep）
#             import time
#             time.sleep(2)
#     return "搜索失败，请稍后重试。"

# @tool
# async def web_search_tool(query: str) -> str:
#     """
#     异步联网搜索工具（免费，使用 DuckDuckGo）。
#     """
#     print(f"\n-> [联网工具] 正在搜索: {query}")
#     loop = asyncio.get_running_loop()
#     # 将同步阻塞搜索放到线程池执行，避免阻塞事件循环
#     result = await loop.run_in_executor(None, _search_sync, query)
#     return result

@tool
def submit_final_itinerary(json_str: str) -> str:
    """提交最终行程（返回带前缀的确认字符串）。"""
    return f"ITINERARY_SUBMITTED:{json_str}"
