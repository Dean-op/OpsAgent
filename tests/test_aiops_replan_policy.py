from app.agent.aiops.replan_policy import should_force_continue


def test_force_continue_when_plan_remains_and_too_few_steps_have_run():
    plan = ["查询指标", "查询日志", "生成报告"]
    past_steps = [
        ("查询告警", '{"total": 1, "alerts": [{"alert_name": "HighCPU"}]}'),
        ("解析告警", "发现 HighCPU 告警"),
    ]

    assert should_force_continue(plan, past_steps) is True


def test_allow_response_when_no_active_alerts_are_confirmed():
    plan = ["生成无告警报告"]
    past_steps = [
        ("查询告警", '{"success": true, "alerts": [], "total": 0}'),
    ]

    assert should_force_continue(plan, past_steps) is False


def test_force_continue_until_remaining_plan_is_done():
    plan = ["生成报告"]
    past_steps = [
        ("查询告警", '{"total": 1}'),
        ("解析告警", "prometheus demo alert"),
        ("查询 CPU 指标", "cpu ok"),
        ("查询内存指标", "memory ok"),
        ("查询日志", "no errors"),
    ]

    assert should_force_continue(plan, past_steps) is True


def test_allow_response_when_plan_is_done():
    plan = []
    past_steps = [
        ("查询告警", '{"total": 1}'),
        ("查询 CPU 指标", "cpu ok"),
    ]

    assert should_force_continue(plan, past_steps) is False
