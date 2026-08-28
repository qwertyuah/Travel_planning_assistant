import uuid
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# 开发阶段无需挂载静态文件，删除以下导入
# from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, AIMessage
from app.agents.graph import app_graph

from contextlib import asynccontextmanager
from app.tools.amap_tools import amap_manager
from app.api.routes import router as itinerary_router

# 在 server.py 顶部增加导入
from app.api.routes import router as itinerary_router
from app.api.poi_routes import router as poi_router
from app.api.map_routes import router as map_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === 启动时执行 ===
    print(">>> [后端] 服务启动，资源初始化...")
    yield
    # === 关闭时执行 ===
    print(">>> [后端] 服务关闭，正在清理 MCP 资源...")
    await amap_manager.cleanup()  # 显式关闭 MCP 连接
    print(">>> [后端] MCP 资源清理完毕")


app = FastAPI(lifespan=lifespan)

# 配置CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        "http://localhost",      # Docker nginx
        "http://localhost:80",
        "http://127.0.0.1",
        "http://127.0.0.1:80"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册双模式行程规划路由
app.include_router(itinerary_router)
app.include_router(poi_router)
app.include_router(map_router)


# 健康检查端点（供 Docker healthcheck 使用）
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "travel-agent-backend"}


def safe_serialize(obj):
    """Recursively convert common objects to JSON-serializable forms."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(v) for v in obj]
    if hasattr(obj, 'content') or hasattr(obj, 'tool_calls'):
        return serialize_message(obj)
    try:
        data = getattr(obj, "__dict__", None)
        if data:
            return {k: safe_serialize(v) for k, v in data.items()}
    except Exception:
        pass
    try:
        return str(obj)
    except Exception:
        return None


def serialize_message(m):
    d = {"type": type(m).__name__}
    if hasattr(m, 'content'):
        d['content'] = getattr(m, 'content')
    if hasattr(m, 'tool_calls') and getattr(m, 'tool_calls'):
        calls = []
        for tc in m.tool_calls:
            calls.append({
                'id': tc.get('id'),
                'name': tc.get('name'),
                'args': safe_serialize(tc.get('args'))
            })
        d['tool_calls'] = calls
    return d


# ---------- 已移除静态文件挂载 ----------
# 开发阶段前端由 Vite 提供，后端仅需处理 /ws
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
# -----------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n>>> [后端] WebSocket 连接已建立！")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    current_state = {"messages": []}
    try:
        while True:
            data = await websocket.receive_text()
            print(f">>> [后端] 收到用户消息: {data}")
            input_state = {"messages": [HumanMessage(content=data)]}
            try:
                result_state = await app_graph.ainvoke(input_state, config)
                snapshot = app_graph.get_state(config)
                current_state = snapshot.values
                msgs = current_state.get('messages', [])
                deduped = []
                for m in msgs:
                    if not deduped:
                        deduped.append(m)
                        continue
                    prev = deduped[-1]
                    if type(prev) is type(m) and getattr(prev, 'content', None) == getattr(m, 'content', None):
                        continue
                    deduped.append(m)
                current_state['messages'] = deduped
                last_msg = current_state['messages'][-1]
                ai_response_raw = last_msg.content if isinstance(last_msg, AIMessage) else "处理完成。"
                confirm_pattern = r"CONFIRMED\|id=(\d+)\|name=([^|]+)\|price=(\d+)\|time=([^|]*)\|from=([^|]*)\|to=([^|]*)(?:\|seat=([^|]+))?\|dir=([^|]+)"
                match = re.search(confirm_pattern, ai_response_raw)
                if match:
                    transport_id = int(match.group(1))
                    transport_name = match.group(2)
                    price = int(match.group(3))
                    time_range = match.group(4)
                    origin = match.group(5)
                    destination = match.group(6)
                    seat_type = match.group(7) if match.group(7) else None
                    direction = match.group(8)
                    selected_transport = {
                        "id": transport_id,
                        "name": transport_name,
                        "type": "高铁" if seat_type else "飞机",
                        "price": price,
                        "time": time_range,
                        "from": origin,
                        "to": destination,
                        "seat_type": seat_type if seat_type else "默认",
                        "direction": direction
                    }
                    current_selected = current_state.get("selected_transports", [])
                    current_state["selected_transports"] = current_selected + [selected_transport]
                    current_state["transport_options"] = None
                    ai_response = f"✅ 已确认 {transport_name} {seat_type if seat_type else ''}（{direction}），票价 {price} 元。"
                else:
                    ai_response = ai_response_raw
                await websocket.send_json({"type": "chat", "content": ai_response})
                state_update = {
                    "destination": safe_serialize(current_state.get("destination")),
                    "selected_transports": safe_serialize(current_state.get("selected_transports", [])),
                    "transport_options": safe_serialize(current_state.get("transport_options")),
                    "selected_hotels": safe_serialize(current_state.get("selected_hotels", [])),
                    "hotel_options": safe_serialize(current_state.get("hotel_options")),
                    "itinerary": safe_serialize(current_state.get("itinerary")),
                    "itinerary_source": safe_serialize(current_state.get("itinerary_source", "amap"))
                }
                await websocket.send_json({"type": "state_update", "state": state_update})
                print(">>> [后端] 消息处理完毕")
            except Exception as e:
                print(f"!!! [后端] Agent 处理出错: {e}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({"type": "chat", "content": "抱歉，系统处理时发生错误。"})
    except WebSocketDisconnect:
        print(">>> [后端] 客户端断开连接")
