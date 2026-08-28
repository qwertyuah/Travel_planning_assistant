"""双模式行程规划路由：表单模式 & 对话模式"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import TripRequest, ChatRequest, ItineraryResponse, TripPlan
from app.agents.agents import itinerary_subgraph, ItineraryState
from app.agents.itinerary_planner import get_itinerary_planner

router = APIRouter(prefix="/api/itinerary", tags=["行程规划"])

@router.post("/form-plan", response_model=ItineraryResponse)
async def form_plan(request: TripRequest):
    """表单模式：强类型输入，高德优先异常降级百度"""
    try:
        # 1. 将前端表单的 TripRequest 映射为子图需要的 ItineraryState
        state = ItineraryState(
            destination=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            preferences=request.preferences,
            transportation=request.transportation,
            accommodation=request.accommodation,
            selected_hotels=[],  # 表单模式暂无前置确认的交通和酒店
            selected_transports=[],
            amap_healthy=True
        )
        
        # 2. 调用行程子图（内部已封装高德优先、降级百度逻辑）
        result_state = await itinerary_subgraph.ainvoke(state)
        
        source = result_state.get("itinerary_source", "error")
        itinerary_data = result_state.get("itinerary")

        # 3. 数据强校验拦截：如果是高德数据，尝试解析为严格的 TripPlan
        validated_data = None
        if source == "amap" and itinerary_data:
            try:
                validated_data = TripPlan(**itinerary_data)
            except Exception as e:
                print(f"[表单路由] ⚠️ 高德数据强校验失败: {e}，降级为原始字典返回")
                source = "amap_fallback" # 标记高德数据结构异常，前端可用备用渲染

        # 4. 包装统一响应
        return ItineraryResponse(
            mode="form",
            source=source,
            data=validated_data,
            raw_data=itinerary_data if not validated_data else None,
            message="规划成功" if source != "error" else "规划失败，请重试"
        )
    except Exception as e:
        print(f"[表单路由] ❌ 异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-plan", response_model=ItineraryResponse)
async def chat_plan(request: ChatRequest):
    """对话模式：按信息完备度智能分流"""
    planner = get_itinerary_planner()
    ctx = request.current_context or {}
    
    # 1. 判断核心信息是否完备 (目的地、开始日期、结束日期)
    has_core_info = all([ctx.get("destination"), ctx.get("start_date"), ctx.get("end_date")])

    if has_core_info:
        # 信息完整 -> 走高德子图 (包含降级逻辑)
        state = ItineraryState(
            destination=ctx["destination"],
            start_date=ctx["start_date"],
            end_date=ctx["end_date"],
            preferences=ctx.get("preferences", []),
            transportation=ctx.get("transportation", "公共交通"),
            accommodation=ctx.get("accommodation", "舒适型酒店"),
            selected_hotels=ctx.get("selected_hotels", []),
            selected_transports=ctx.get("selected_transports", []),
            amap_healthy=True
        )
        result_state = await itinerary_subgraph.ainvoke(state)
        source = result_state.get("itinerary_source", "error")
        itinerary_data = result_state.get("itinerary")
        
        # 强校验
        validated_data = None
        if source == "amap" and itinerary_data:
            try:
                validated_data = TripPlan(**itinerary_data)
            except Exception:
                pass

        return ItineraryResponse(
            mode="chat",
            source=source,
            data=validated_data,
            raw_data=itinerary_data if not validated_data else None,
            message="已为您生成详细地图行程"
        )
    else:
        # 信息不全 -> 走百度扁平化快速推荐
        destination = ctx.get("destination", "未知城市")
        baidu_result = await planner.run_baidu({"destination": destination})
        
        return ItineraryResponse(
            mode="chat",
            source="baidu",
            raw_data=baidu_result.get("itinerary"),
            data=None,
            message=f"由于信息暂不完整，已通过搜索为您生成{destination}的初步建议。补充完整日期等信息，可获得更精准的地图规划。"
        )
