from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.amap_service import amap_service
from app.models.schemas import RouteRequest, RouteResponse, WeatherResponse
from app.tools.amap_tools import amap_manager

router = APIRouter(prefix="/api/map", tags=["地图服务"])

@router.get("/weather", response_model=WeatherResponse)
async def get_weather(city: str = Query(...)):
    try:
        weather_info = await amap_service.get_weather(city)
        return WeatherResponse(success=True, message="查询成功", data=weather_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/route", response_model=RouteResponse)
async def plan_route(request: RouteRequest):
    try:
        route_info = await amap_service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type
        )
        return RouteResponse(success=True, message="规划成功", data=route_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """检查 MCP 服务是否可用"""
    is_healthy = amap_manager.is_healthy()
    if is_healthy:
        return {"status": "healthy", "mcp_tools_count": len(amap_manager.available_tools)}
    raise HTTPException(status_code=503, detail="高德 MCP 服务不可用")
