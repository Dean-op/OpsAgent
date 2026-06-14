"""智能运维监控 MCP Server

本地实现的监控服务 MCP Server，提供：
- 监控数据查询（CPU、内存、磁盘、网络等）
- 进程信息查询
- 历史工单查询
- 服务信息查询

用于支持运维 Agent 的故障排查场景。
"""

import logging
import functools
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from fastmcp import FastMCP

from app.config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Monitor_MCP_Server")

mcp = FastMCP("Monitor")


def log_tool_call(func):
    """装饰器：记录工具调用的日志，包括方法名、参数和返回状态"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method_name = func.__name__

        # 记录调用信息
        logger.info(f"=" * 80)
        logger.info(f"调用方法: {method_name}")

        # 记录参数（排除self等）
        if kwargs:
            # 使用 json.dumps 格式化参数，处理可能的序列化错误
            try:
                params_str = json.dumps(kwargs, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                params_str = str(kwargs)
            logger.info(f"参数信息:\n{params_str}")
        else:
            logger.info("参数信息: 无")

        # 执行方法
        try:
            result = func(*args, **kwargs)

            # 记录返回状态
            logger.info(f"返回状态: SUCCESS")

            # 记录返回结果摘要（避免日志过长）
            if isinstance(result, dict):
                summary = {k: v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} with {len(v)} items>"
                          for k, v in list(result.items())[:5]}
                logger.info(f"返回结果摘要: {json.dumps(summary, ensure_ascii=False)}")
            else:
                logger.info(f"返回结果: {result}")

            logger.info(f"=" * 80)
            return result

        except Exception as e:
            # 记录错误状态
            logger.error(f"返回状态: ERROR")
            logger.error(f"错误信息: {str(e)}")
            logger.error(f"=" * 80)
            raise

    return wrapper


# ============================================================
# 辅助函数
# ============================================================

def parse_time_or_default(time_str: Optional[str], default_offset_hours: int = 0) -> datetime:
    """解析时间字符串或返回默认时间。

    Args:
        time_str: 时间字符串（格式：YYYY-MM-DD HH:MM:SS）
        default_offset_hours: 默认时间偏移（小时）

    Returns:
        datetime: 解析后的时间对象
    """
    if time_str:
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    # 返回默认时间（当前时间 + 偏移）
    return datetime.now() + timedelta(hours=default_offset_hours)


def generate_time_series(base_time: datetime, minutes_offset: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """生成时间序列字符串。

    Args:
        base_time: 基准时间
        minutes_offset: 分钟偏移量
        format_str: 时间格式字符串

    Returns:
        str: 格式化的时间字符串
    """
    result_time = base_time + timedelta(minutes=minutes_offset)
    return result_time.strftime(format_str)


def interval_to_seconds(interval: str) -> int:
    """将 Prometheus step 间隔转为秒。"""
    try:
        if interval.endswith("m"):
            return max(1, int(interval[:-1]) * 60)
        if interval.endswith("h"):
            return max(1, int(interval[:-1]) * 3600)
        if interval.endswith("s"):
            return max(1, int(interval[:-1]))
    except ValueError:
        return 60
    return 60


def query_prometheus_range(
    promql: str,
    start_dt: datetime,
    end_dt: datetime,
    step: str,
) -> Dict[str, Any]:
    """调用 Prometheus query_range API。"""
    base_url = config.prometheus_base_url.rstrip("/")
    api_url = f"{base_url}/api/v1/query_range"
    params = {
        "query": promql,
        "start": start_dt.timestamp(),
        "end": end_dt.timestamp(),
        "step": step,
    }
    logger.info("Querying Prometheus range: %s params=%s", api_url, params)
    with httpx.Client(timeout=config.prometheus_request_timeout) as client:
        response = client.get(api_url, params=params)
        response.raise_for_status()
        return response.json()


def _extract_series_points(result: Dict[str, Any]) -> list[dict[str, Any]]:
    """从 Prometheus matrix 结果中提取时间点和值。"""
    if result.get("status") != "success":
        raise RuntimeError(result.get("error") or "Prometheus returned non-success status")

    series = (result.get("data") or {}).get("result") or []
    data_points: list[dict[str, Any]] = []
    for item in series:
        metric = item.get("metric") or {}
        for ts, raw_value in item.get("values") or []:
            try:
                value = round(float(raw_value), 2)
            except (TypeError, ValueError):
                continue
            data_points.append(
                {
                    "timestamp": datetime.fromtimestamp(float(ts)).strftime("%H:%M"),
                    "value": value,
                    "metric": metric,
                }
            )
    data_points.sort(key=lambda point: point["timestamp"])
    return data_points


def _build_statistics(values: list[float], threshold: float, flag_name: str) -> Dict[str, Any]:
    if not values:
        return {}
    sorted_values = sorted(values)
    p95_index = min(len(sorted_values) - 1, int(len(sorted_values) * 0.95))
    max_value = max(values)
    return {
        "avg": round(sum(values) / len(values), 2),
        "max": max_value,
        "min": min(values),
        "p95": round(sorted_values[p95_index], 2),
        flag_name: max_value > threshold,
    }


def _error_result(service_name: str, metric_name: str, interval: str, error: str) -> Dict[str, Any]:
    return {
        "service_name": service_name,
        "metric_name": metric_name,
        "interval": interval,
        "data_points": [],
        "statistics": {},
        "success": False,
        "error": error,
        "message": "Prometheus 查询失败，请确认 Prometheus 已启动且指标名称/服务标签正确",
    }


def _service_filter(service_name: str) -> str:
    return f'{{job="{service_name}"}}'




# ============================================================
# 监控数据查询工具
# ============================================================

@mcp.tool()
@log_tool_call
def query_cpu_metrics(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    interval: str = "1m"
) -> Dict[str, Any]:
    """查询服务的 CPU 使用率监控数据。

    Args:
        service_name: 服务名称（必填）
            示例: "data-sync-service"
        
        start_time: 开始时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 10:00:00"
            默认值: 如果不传，默认为当前时间的1小时前
            注意: 必须使用字符串格式，而非时间戳
        
        end_time: 结束时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 11:00:00"
            默认值: 如果不传，默认为当前时间
            注意: 必须使用字符串格式，而非时间戳
        
        interval: 数据聚合间隔（可选）
            可选值: "1m" (1分钟), "5m" (5分钟), "1h" (1小时)
            默认值: "1m"
            说明: 控制数据点的时间间隔

    Returns:
        Dict: CPU 监控数据
            - service_name: 服务名称
            - metric_name: 指标名称 (cpu_usage_percent)
            - interval: 数据聚合间隔
            - data_points: 数据点列表，每个点包含:
                * timestamp: 时间点（格式: HH:MM）
                * value: CPU 使用率百分比
            - statistics: 统计信息
                * average: 平均值
                * max: 最大值
                * min: 最小值
            - alert: 告警信息（如有）
                * triggered: 是否触发告警
                * threshold: 告警阈值
                * message: 告警消息
    
    使用示例:
        # 示例1: 使用默认时间（最近1小时）
        query_cpu_metrics(service_name="data-sync-service")
        
        # 示例2: 指定时间范围
        query_cpu_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00",
            end_time="2026-02-14 11:00:00",
            interval="5m"
        )
        
        # 示例3: 只指定开始时间（结束时间自动为当前时间）
        query_cpu_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00"
        )
    """
    start_dt = parse_time_or_default(start_time, default_offset_hours=-1)
    end_dt = parse_time_or_default(end_time, default_offset_hours=0)
    step = f"{interval_to_seconds(interval)}s"
    promql = (
        f'(1 - avg by (instance) '
        f'(rate(node_cpu_seconds_total{{job="{service_name}",mode="idle"}}[5m]))) * 100'
    )

    try:
        result = query_prometheus_range(promql, start_dt, end_dt, step)
        data_points = _extract_series_points(result)
    except Exception as e:
        return _error_result(service_name, "cpu_usage_percent", interval, str(e))

    values = [point["value"] for point in data_points]
    statistics = _build_statistics(values, threshold=80.0, flag_name="spike_detected")
    spike_detected = bool(statistics.get("spike_detected"))
    return {
        "service_name": service_name,
        "metric_name": "cpu_usage_percent",
        "interval": interval,
        "promql": promql,
        "data_points": data_points,
        "statistics": statistics,
        "success": True,
        "alert_info": {
            "triggered": spike_detected,
            "threshold": 80.0,
            "message": "CPU 使用率超过 80% 阈值" if spike_detected else "CPU 使用率正常",
        },
    }


@mcp.tool()
@log_tool_call
def query_memory_metrics(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    interval: str = "1m"
) -> Dict[str, Any]:
    """查询服务的内存使用监控数据。

    Args:
        service_name: 服务名称（必填）
            示例: "data-sync-service"
        
        start_time: 开始时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 10:00:00"
            默认值: 如果不传，默认为当前时间的1小时前
            注意: 必须使用字符串格式，而非时间戳
        
        end_time: 结束时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 11:00:00"
            默认值: 如果不传，默认为当前时间
            注意: 必须使用字符串格式，而非时间戳
        
        interval: 数据聚合间隔（可选）
            可选值: "1m" (1分钟), "5m" (5分钟), "1h" (1小时)
            默认值: "1m"

    Returns:
        Dict: 内存监控数据
            - service_name: 服务名称
            - metric_name: 指标名称 (memory_usage_percent)
            - interval: 数据聚合间隔
            - data_points: 数据点列表，每个点包含:
                * timestamp: 时间点（格式: HH:MM）
                * value: 内存使用率百分比
                * used_gb: 已使用内存（GB）
                * total_gb: 总内存（GB）
            - statistics: 统计信息
                * average: 平均值
                * max: 最大值
                * min: 最小值
            - alert: 告警信息（如有）
                * triggered: 是否触发告警
                * threshold: 告警阈值
                * message: 告警消息
    
    使用示例:
        # 示例1: 使用默认时间（最近1小时）
        query_memory_metrics(service_name="data-sync-service")
        
        # 示例2: 指定时间范围
        query_memory_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00",
            end_time="2026-02-14 11:00:00",
            interval="5m"
        )
    """
    start_dt = parse_time_or_default(start_time, default_offset_hours=-1)
    end_dt = parse_time_or_default(end_time, default_offset_hours=0)
    step = f"{interval_to_seconds(interval)}s"
    promql = (
        f'(1 - (node_memory_MemAvailable_bytes{_service_filter(service_name)} '
        f'/ node_memory_MemTotal_bytes{_service_filter(service_name)})) * 100'
    )

    try:
        result = query_prometheus_range(promql, start_dt, end_dt, step)
        data_points = _extract_series_points(result)
    except Exception as e:
        return _error_result(service_name, "memory_usage_percent", interval, str(e))

    values = [point["value"] for point in data_points]
    statistics = _build_statistics(values, threshold=70.0, flag_name="memory_pressure")
    memory_pressure = bool(statistics.get("memory_pressure"))
    return {
        "service_name": service_name,
        "metric_name": "memory_usage_percent",
        "interval": interval,
        "promql": promql,
        "data_points": data_points,
        "statistics": statistics,
        "success": True,
        "alert_info": {
            "triggered": memory_pressure,
            "threshold": 70.0,
            "message": "内存使用率超过 70% 阈值，存在内存压力" if memory_pressure else "内存使用率正常",
        },
    }




if __name__ == "__main__":
    # 使用 streamable-http 模式，运行在 8004 端口
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8004, path="/mcp")
