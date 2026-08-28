import os
import json
import subprocess
import logging
import shutil
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TuniuCLIManager:
    """途牛 CLI 调用客户端 (支持绝对路径查找)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self.api_key = os.getenv("TUNIU_API_KEY")
        if not self.api_key:
            print("❌ [初始化错误] 未检测到环境变量 TUNIU_API_KEY")
        else:
            print(f"✅ [初始化] TUNIU_API_KEY 已加载: {self.api_key[:4]}***")

        self.tuniu_cmd = self._find_tuniu_command()
        if not self.tuniu_cmd:
            print("❌ [初始化错误] 未找到 'tuniu' 命令，请确认已执行: npm install -g tuniu-cli")
        else:
            print(f"✅ [初始化] 找到 tuniu 命令: {self.tuniu_cmd}")
            self._test_cli()

        self.initialized = True

    def _find_tuniu_command(self) -> str | None:
        cmd_path = shutil.which("tuniu")
        if cmd_path:
            return cmd_path
        if os.name == 'nt':
            npm_global_bin = os.path.expandvars(r"%AppData%\\npm")
            candidate = os.path.join(npm_global_bin, "tuniu.cmd")
            if os.path.isfile(candidate):
                return candidate
        common_paths = [
            "/usr/local/bin/tuniu",
            os.path.expanduser("~/.npm-global/bin/tuniu"),
            os.path.expanduser("~/.local/bin/tuniu")
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path
        return None

    def _test_cli(self):
        try:
            result = subprocess.run(
                [self.tuniu_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ [CLI 测试] tuniu 版本: {result.stdout.strip()}")
            else:
                print(f"⚠️ [CLI 测试] 执行失败: {result.stderr}")
        except Exception as e:
            print(f"⚠️ [CLI 测试] 异常: {e}")

    def _run_command(self, server: str, tool: str, args: Dict[str, Any], timeout: int = 30) -> Dict:
        if not self.tuniu_cmd:
            print("❌ [严重错误] tuniu 命令未找到，无法执行。")
            return {"error": "CLI命令未找到，请检查安装"}

        args_json = json.dumps(args, ensure_ascii=False)
        cmd = [self.tuniu_cmd, "call", server, tool, "-a", args_json, "--output", "json"]
        print(f"⚙️ [CLI 准备执行] 命令: {' '.join(cmd)}")

        env = os.environ.copy()
        if self.api_key:
            env["TUNIU_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                env=env
            )
            if result.returncode != 0:
                print(f"❌ [CLI 执行失败] Exit Code: {result.returncode}")
                print(f"❌ [错误详情] {result.stderr}")
                return {"error": result.stderr or "CLI执行失败", "raw": result.stdout}

            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    return data
                except json.JSONDecodeError:
                    print(f"⚠️ [CLI 解析警告] 返回内容非JSON: {result.stdout[:100]}")
                    return {"error": "返回格式错误", "raw": result.stdout}
            return {}
        except subprocess.TimeoutExpired:
            print(f"❌ [超时错误] 命令执行超过 {timeout} 秒")
            return {"error": "请求超时"}
        except UnicodeDecodeError as e:
            print(f"❌ [编码错误] {e}")
            return {"error": f"输出编码错误: {e}"}
        except Exception as e:
            print(f"❌ [未知异常] {e}")
            return {"error": str(e)}

    def _parse_cli_response(self, res: Dict) -> List[Dict]:
        if not res.get("success"):
            error_msg = res.get("error", {}).get("message", "未知错误")
            print(f"   [CLI响应] 接口返回失败: {error_msg}")
            return []
        content = res.get("result", {}).get("content", [])
        if not content:
            print("   [CLI响应] 没有 content 字段")
            return []
        text_content = content[0].get("text", "")
        if not text_content:
            print("   [CLI响应] text 字段为空")
            return []
        try:
            inner_data = json.loads(text_content)
            items = inner_data.get("data", [])
            if not items:
                items = inner_data.get("hotels", [])
            print(f"   [CLI响应] 成功解析到 {len(items)} 条数据")
            return items
        except json.JSONDecodeError as e:
            print(f"   [CLI响应] 解析 text JSON 失败: {e}")
            return []

    def get_flights(self, origin: str, destination: str, date: str) -> List[Dict]:
        args = {
            "departureCityName": origin,
            "arrivalCityName": destination,
            "departureDate": date
        }
        res = self._run_command("flight", "searchLowestPriceFlight", args)
        if "error" in res:
            print(f"   [航班查询] 接口返回错误: {res['error']}")
            return []
        items = self._parse_cli_response(res)
        results = []
        for item in items:
            flight_number = item.get("flightNumber", "未知")
            airline = item.get("airlineCompany", "")
            price_str = item.get("basePrice", "0")
            try:
                price = int(float(price_str))
            except:
                price = 0
            dep_time = item.get("departureTime", "")
            arr_time = item.get("arrivalTime", "")
            dep_airport = item.get("departureAirport", origin).replace(" ", "")
            arr_airport = item.get("arrivalAirport", destination).replace(" ", "")
            results.append({
                "type": "飞机",
                "name": f"{airline} {flight_number}" if airline else flight_number,
                "price": price,
                "time": f"{dep_time}-{arr_time}",
                "from": dep_airport,
                "to": arr_airport,
                "flight_number": flight_number,
                "_raw": item
            })
        return results

    def get_trains(self, origin: str, destination: str, date: str) -> List[Dict]:
        args = {
            "departureCityName": origin,
            "arrivalCityName": destination,
            "departureDate": date
        }
        res = self._run_command("train", "searchLowestPriceTrain", args)
        if "error" in res:
            print(f"   [火车查询] 接口返回错误: {res['error']}")
            return []
        items = self._parse_cli_response(res)
        results = []
        for item in items:
            train_number = item.get("trainNum", "未知")
            dep_station = item.get("departStationName", origin)
            arr_station = item.get("destStationName", destination)
            dep_time = item.get("departureTime", "")
            arr_time = item.get("arrivalTime", "")
            duration = item.get("duration", "")
            price_obj = item.get("price", {})
            seat_obj = item.get("seatAvailable", {})
            seat_fields = [
                ("高级软卧", "gjrwPrice", "gjrwNum"),
                ("软卧", "rwPrice", "rwNum"),
                ("软座", "rzPrice", "rzNum"),
                ("商务座", "swzPrice", "swzNum"),
                ("特等座", "tdzPrice", "tdzNum"),
                ("无座", "wzPrice", "wzNum"),
                ("硬卧", "ywPrice", "ywNum"),
                ("硬座", "yzPrice", "yzNum"),
                ("二等座", "edzPrice", "edzNum"),
                ("一等座", "ydzPrice", "ydzNum"),
                ("动卧", "dwPrice", "dwNum"),
                ("一等卧", "ydwPrice", "ydwNum"),
                ("二等卧", "edwPrice", "edwNum"),
            ]
            seats = []
            for seat_name, price_field, num_field in seat_fields:
                price_str = price_obj.get(price_field, "")
                if price_str and price_str.strip():
                    try:
                        price_val = int(float(price_str))
                    except:
                        price_val = 0
                    avail = seat_obj.get(num_field)
                    if avail is not None:
                        avail_num = int(avail) if isinstance(avail, (int, float)) else 0
                        seats.append({
                            "type": seat_name,
                            "price": price_val,
                            "available": avail_num
                        })
            if not seats:
                continue
            lowest_price = min(s["price"] for s in seats)
            raw_type = item.get("trainTypeName", "")
            if "高铁" in raw_type:
                transport_type = "高铁"
            elif "动车" in raw_type:
                transport_type = "动车"
            else:
                transport_type = raw_type if raw_type else "火车"

            results.append({
                "type": transport_type,
                "name": train_number,
                "price": lowest_price,
                "time": f"{dep_time}-{arr_time}",
                "from": dep_station,
                "to": arr_station,
                "duration": duration,
                "seats": seats,
                "_raw": item})
        return results

    def get_hotels(self, city: str, checkin: str, checkout: str, price_range: str = None, keyword: str = None) -> List[Dict]:
        args = {
            "cityName": city,
            "checkIn": checkin,
            "checkOut": checkout
        }
        if price_range:
            args["prices"] = price_range
        if keyword:
            args["keyword"] = keyword
        res = self._run_command("hotel", "tuniu_hotel_search", args)
        items = self._parse_cli_response(res)
        results = []
        for item in items:
            results.append({
                "id": item.get("hotelId"),
                "name": item.get("hotelName", "未知酒店"),
                "address": item.get("address", ""),
                "business_circle": item.get("business", ""),
                "score": item.get("commentScore", 0),
                "price": item.get("lowestPrice", 0),
                "city": item.get("cityName", ""),
                "room_type": item.get("roomName", ""),
                "window_type": item.get("roomWindow", ""),
                "star": item.get("starName", ""),
                "image": item.get("firstPic", ""),
                "meal": item.get("meal", ""),
                "refund": item.get("refund", ""),
                "_raw": item
            })
        return results


# 单例
tuniu_manager = TuniuCLIManager()