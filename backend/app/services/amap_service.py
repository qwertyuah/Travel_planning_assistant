"""高德地图服务封装 - 基于当前项目 MCP 异步单例"""
import json
import re
from typing import List, Dict, Any, Optional
from app.tools.amap_tools import amap_manager
from app.models.schemas import Location, POIInfo, WeatherInfo

class AmapService:
    async def _call_mcp(self, tool_name: str, arguments: dict) -> str:
        """统一调用 MCP 并返回文本"""
        return await amap_manager.call_tool(tool_name, arguments)

    def _extract_json_from_mcp(self, result_str: str) -> Any:
        """尝试从 MCP 返回的文本中提取 JSON 结构"""
        try:
            # 尝试直接解析
            return json.loads(result_str)
        except json.JSONDecodeError:
            # 提取 [] 或 {} 包裹的部分
            match = re.search(r'[\[\{].*[\]\}]', result_str, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    async def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        try:
            result_str = await self._call_mcp("maps_text_search", {
                "keywords": keywords, "city": city, "citylimit": str(citylimit).lower()
            })
            data = self._extract_json_from_mcp(result_str)
            
            if not data or not isinstance(data, list):
                return []
            
            pois = []
            for item in data[:10]:
                loc_str = item.get("location", "")
                lng, lat = 0.0, 0.0
                if loc_str and "," in loc_str:
                    try:
                        lng, lat = map(float, loc_str.split(","))
                    except ValueError:
                        pass
                
                pois.append(POIInfo(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    type=item.get("type", ""),
                    address=item.get("address", ""),
                    location=Location(longitude=lng, latitude=lat),
                    tel=item.get("tel")
                ))
            return pois
        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    async def get_weather(self, city: str) -> List[WeatherInfo]:
        try:
            result_str = await self._call_mcp("maps_weather", {"city": city})
            data = self._extract_json_from_mcp(result_str)
            # 简化处理：高德天气返回结构可能嵌套在 lives 或 forecasts 中
            # 实际解析需根据高德MCP真实返回微调，这里返回原始字典转 WeatherInfo 的尝试
            if isinstance(data, list) and data:
                return [WeatherInfo(**w) for w in data if isinstance(w, dict)]
            return []
        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    async def plan_route(self, origin_address: str, destination_address: str, 
                         origin_city: Optional[str] = None, destination_city: Optional[str] = None, 
                         route_type: str = "walking") -> Dict[str, Any]:
        try:
            tool_map = {
                "walking": "maps_direction_walking_by_address",
                "driving": "maps_direction_driving_by_address",
                "transit": "maps_direction_transit_integrated_by_address"
            }
            tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")
            
            args = {"origin_address": origin_address, "destination_address": destination_address}
            if origin_city: args["origin_city"] = origin_city
            if destination_city: args["destination_city"] = destination_city
            
            result_str = await self._call_mcp(tool_name, args)
            return self._extract_json_from_mcp(result_str) or {"raw_text": result_str}
        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return {}

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        try:
            args = {"address": address}
            if city: args["city"] = city
            result_str = await self._call_mcp("maps_geo", args)
            data = self._extract_json_from_mcp(result_str)
            if isinstance(data, list) and data and "location" in data[0]:
                lng, lat = map(float, data[0]["location"].split(","))
                return Location(longitude=lng, latitude=lat)
            return None
        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    async def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        try:
            result_str = await self._call_mcp("maps_search_detail", {"id": poi_id})
            data = self._extract_json_from_mcp(result_str)
            return data if isinstance(data, dict) else {"raw": result_str}
        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}

# 全局单例
amap_service = AmapService()
