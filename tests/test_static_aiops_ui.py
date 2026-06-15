from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def test_aiops_stream_uses_loading_classes_for_buttons():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    styles_css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    assert "this.aiOpsSidebarBtn.classList.toggle('is-loading', this.isStreaming)" in app_js
    assert "this.sendButton.classList.toggle('is-loading', this.isStreaming)" in app_js
    assert ".ai-ops-top-btn.is-loading svg" in styles_css
    assert ".send-btn-circle.is-loading svg" in styles_css
