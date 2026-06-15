from app.agent.aiops.planner import MAX_PLAN_STEPS, _is_report_generation_step


def test_report_generation_step_is_filtered_by_policy_helper():
    assert _is_report_generation_step("综合以上信息生成 Markdown 诊断报告") is True
    assert _is_report_generation_step("使用 query_cpu_metrics 查询最近30分钟 CPU 指标") is False


def test_planner_demo_step_cap_is_six():
    assert MAX_PLAN_STEPS == 6
