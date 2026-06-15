from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def test_aiops_stream_uses_loading_classes_for_buttons():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    styles_css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    assert "this.aiOpsSidebarBtn.classList.toggle('is-loading', this.isStreaming)" in app_js
    assert "this.sendButton.classList.toggle('is-loading', this.isStreaming)" in app_js
    assert ".ai-ops-top-btn.is-loading svg" in styles_css
    assert ".send-btn-circle.is-loading svg" in styles_css
    assert ".message-avatar.aiops-active" in styles_css
    assert "messageAvatar.classList.add('aiops-active')" in app_js or "classList.toggle('aiops-active'" in app_js


def test_aiops_process_is_collapsed_and_report_is_primary_content():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "processDetails" in app_js
    assert "finalReport" in app_js
    assert "updateAIOpsProcessDetails" in app_js
    assert "查看诊断过程" in app_js


def test_streaming_buffers_are_declared_in_the_right_handlers():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    stream_handler = app_js.split("async sendStreamMessage", 1)[1].split("async sendAIOpsRequest", 1)[0]
    aiops_handler = app_js.split("async sendAIOpsRequest", 1)[1].split("formatAIOpsEvent", 1)[0]

    assert "let fullResponse = ''" in stream_handler
    assert "let finalReport = ''" in aiops_handler
    assert "let processDetails = ''" in aiops_handler
