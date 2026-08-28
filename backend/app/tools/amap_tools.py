"""高德地图MCP工具封装 - LangChain Tool适配层"""
import os
import asyncio
from typing import Optional, List
from contextlib import AsyncExitStack
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()


class AmapToolError(Exception):
    """高德MCP工具调用异常"""
    pass


class AmapMCPManager:
    """高德地图MCP服务管理器(单例模式)

    管理MCP服务器子进程的生命周期，提供共享的MCP连接。
    所有Agent共享同一实例，避免重复启动多个MCP服务器进程。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_done = False
        return cls._instance

    def __init__(self):
        if self._setup_done:
            return
        self._setup_done = True
        self.api_key = os.getenv("AMAP_API_KEY", "")
        self._session = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._available_tools: List[str] = []
        self._healthy = False
        self._lock = asyncio.Lock()

    async def _do_initialize(self):
        """执行MCP连接初始化(内部方法，需在锁内调用)"""
        await self._cleanup()

        if not self.api_key:
            raise AmapToolError("AMAP_API_KEY未配置，请设置环境变量")

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise AmapToolError("mcp SDK未安装，请执行: pip install mcp")

        self._exit_stack = AsyncExitStack()

        try:
            await self._exit_stack.__aenter__()

            server_params = StdioServerParameters(
                command="uvx",
                args=["amap-mcp-server"],
                env={"AMAP_MAPS_API_KEY": self.api_key}
            )

            # 启动MCP服务器子进程并建立stdio通信
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            # 创建并初始化MCP会话
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()

            # 发现可用工具
            tools_result = await self._session.list_tools()
            self._available_tools = [t.name for t in tools_result.tools]
            self._healthy = True

            print(f"✅ 高德MCP初始化成功，可用工具({len(self._available_tools)}个):")
            for t in self._available_tools[:5]:
                print(f"  - {t}")
            if len(self._available_tools) > 5:
                print(f"  ... 还有{len(self._available_tools) - 5}个")

        except Exception as e:
            self._healthy = False
            self._session = None
            if self._exit_stack:
                try:
                    await self._exit_stack.aclose()
                except Exception:
                    pass
                self._exit_stack = None
            raise AmapToolError(f"高德MCP初始化失败: {e}")

    async def _ensure_initialized(self):
        """确保MCP连接可用(带并发保护)"""
        if self._healthy and self._session:
            return
        async with self._lock:
            if self._healthy and self._session:
                return
            await self._do_initialize()

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用MCP工具

        Args:
            tool_name: MCP工具名称，如 "maps_text_search"
            arguments: 工具参数字典

        Returns:
            工具返回的文本内容

        Raises:
            AmapToolError: 调用失败时抛出
        """
        await self._ensure_initialized()
        try:
            result = await self._session.call_tool(tool_name, arguments)
            if result.content:
                texts = [c.text for c in result.content if hasattr(c, "text")]
                return "\n".join(texts) if texts else str(result)
            return str(result)
        except AmapToolError:
            raise
        except Exception as e:
            self._healthy = False
            raise AmapToolError(f"调用MCP工具[{tool_name}]失败: {e}")

    async def _cleanup(self):
        """清理MCP连接"""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass
            self._exit_stack = None
        self._session = None
        self._healthy = False

    async def cleanup(self):
        """公开清理方法"""
        async with self._lock:
            await self._cleanup()

    def is_healthy(self) -> bool:
        """检查MCP服务是否可用"""
        return self._healthy

    @property
    def available_tools(self) -> List[str]:
        return self._available_tools


# 全局单例
amap_manager = AmapMCPManager()


# ============ LangChain Tool 定义 ============

@tool
async def amap_search_poi(keywords: str, city: str) -> str:
    """使用高德地图搜索POI(兴趣点)，如景点、餐厅、商场等。
    参数:
        keywords: 搜索关键词，如"故宫"、"历史文化景点"
        city: 城市名称，如"北京"
    """
    result = await amap_manager.call_tool("maps_text_search", {
        "keywords": keywords,
        "city": city
    })
    if not result or not result.strip():
        raise AmapToolError(f"高德POI搜索无结果: keywords={keywords}, city={city}")
    return result


@tool
async def amap_get_weather(city: str) -> str:
    """使用高德地图查询城市天气信息。
    参数:
        city: 城市名称或adcode，如"北京"
    """
    result = await amap_manager.call_tool("maps_weather", {
        "city": city
    })
    if not result or not result.strip():
        raise AmapToolError(f"高德天气查询无结果: city={city}")
    return result


@tool
async def amap_search_hotel(keywords: str, city: str) -> str:
    """使用高德地图搜索酒店/宾馆。
    参数:
        keywords: 搜索关键词，如"酒店"、"经济型酒店"
        city: 城市名称，如"北京"
    """
    result = await amap_manager.call_tool("maps_text_search", {
        "keywords": keywords,
        "city": city
    })
    if not result or not result.strip():
        raise AmapToolError(f"高德酒店搜索无结果: keywords={keywords}, city={city}")
    return result


@tool
async def amap_geo(address: str, city: str = "") -> str:
    """使用高德地图进行地理编码(地址转经纬度坐标)。
    参数:
        address: 地址文本，如"故宫博物院"
        city: 城市名称(可选)，如"北京"
    """
    args = {"address": address}
    if city:
        args["city"] = city
    result = await amap_manager.call_tool("maps_geo", args)
    if not result or not result.strip():
        raise AmapToolError(f"高德地理编码无结果: address={address}")
    return result
