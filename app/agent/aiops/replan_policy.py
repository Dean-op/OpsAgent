"""AIOps 重规划策略。"""

from __future__ import annotations

import json
from typing import Iterable


def _looks_like_no_alerts(result_text: str) -> bool:
    text = result_text.strip()
    if not text:
        return False
    try:
        payload = json.loads(text)
    except Exception:
        return False
    total = payload.get("total")
    alerts = payload.get("alerts")
    return total == 0 or alerts == []


def should_force_continue(plan: list[str], past_steps: Iterable[tuple[str, str]]) -> bool:
    """决定是否强制继续执行剩余计划，而不是过早生成最终报告。

    AIOps 的前端会先展示完整计划。为了避免“展示 12 步但只执行 2 步”
    这种演示上很突兀的体验，只要还有剩余计划就继续执行。
    唯一例外是第一步已经明确证明当前没有活跃告警，此时可以提前收敛。
    """
    steps = list(past_steps)
    if not plan:
        return False

    if steps and _looks_like_no_alerts(steps[0][1]):
        return False

    return True
