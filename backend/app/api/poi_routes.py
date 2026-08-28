from fastapi import APIRouter, HTTPException, Query
from app.services.amap_service import amap_service
from app.services.unsplash_service import unsplash_service
from app.models.schemas import POISearchResponse

router = APIRouter(prefix="/api/poi", tags=["POI服务"])

@router.get("/search", response_model=POISearchResponse)
async def search_poi(keywords: str = Query(...), city: str = Query(...), citylimit: bool = Query(True)):
    try:
        pois = await amap_service.search_poi(keywords, city, citylimit)
        return POISearchResponse(success=True, message="搜索成功", data=pois)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{poi_id}")
async def get_poi_detail(poi_id: str):
    try:
        detail = await amap_service.get_poi_detail(poi_id)
        return {"success": True, "message": "获取成功", "data": detail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/photo")
async def get_attraction_photo(name: str = Query(..., description="景点名称")):
    try:
        # 优先搜索中国地标
        photo_url = await unsplash_service.get_photo_url(f"{name} China landmark")
        if not photo_url:
            photo_url = await unsplash_service.get_photo_url(name)
        return {"success": True, "data": {"name": name, "photo_url": photo_url}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
