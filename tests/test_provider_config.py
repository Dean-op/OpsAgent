import importlib


def test_settings_loads_openai_compatible_provider(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("LLM_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
    monkeypatch.setenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")

    import app.config as config_module

    importlib.reload(config_module)
    settings = config_module.Settings()

    assert settings.llm_api_key == "sk-test"
    assert settings.llm_base_url == "https://api.siliconflow.cn/v1"
    assert settings.llm_model == "deepseek-ai/DeepSeek-V4-Flash"
    assert settings.embedding_model == "Qwen/Qwen3-Embedding-0.6B"
    assert settings.embedding_dimensions == 1024
    assert settings.dashscope_api_key == "sk-test"
    assert settings.rag_model == "deepseek-ai/DeepSeek-V4-Flash"
