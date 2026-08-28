"""Unsplash图片服务 - 异步版"""
import os
import httpx
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class UnsplashService:
    def __init__(self):
        self.access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.base_url = "https://api.unsplash.com"

    async def search_photos(self, query: str, per_page: int = 5) -> List[dict]:
        if not self.access_key:
            return []
        try:
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/search/photos", params=params)
                response.raise_for_status()
                data = response.json()
                
                photos = []
                for photo in data.get("results", []):
                    photos.append({
                        "id": photo.get("id"),
                        "url": photo.get("urls", {}).get("regular"),
                        "thumb": photo.get("urls", {}).get("thumb"),
                        "description": photo.get("description") or photo.get("alt_description"),
                        "photographer": photo.get("user", {}).get("name")
                    })
                return photos
        except Exception as e:
            print(f"❌ Unsplash搜索失败: {str(e)}")
            return []

    async def get_photo_url(self, query: str) -> Optional[str]:
        photos = await self.search_photos(query, per_page=1)
        return photos[0].get("url") if photos else None

# 全局单例
unsplash_service = UnsplashService()
