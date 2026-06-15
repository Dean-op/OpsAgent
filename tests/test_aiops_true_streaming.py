from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_aiops_service_streams_final_report_content_chunks():
    service_py = (ROOT / "app" / "services" / "aiops_service.py").read_text(encoding="utf-8")

    assert '"type": "content"' in service_py
    assert "streaming=True" in service_py
    assert "astream" in service_py


def test_aiops_frontend_handles_content_chunks_incrementally():
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert "sseMessage.type === 'content'" in app_js
    assert "this.updateAIOpsStreamContent(loadingMessageElement, fullResponse)" in app_js
