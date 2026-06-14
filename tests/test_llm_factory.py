from unittest.mock import patch


def test_create_chat_model_uses_configured_openai_compatible_endpoint(monkeypatch):
    monkeypatch.setattr("app.core.llm_factory.config.llm_model", "deepseek-ai/DeepSeek-V4-Flash")
    monkeypatch.setattr("app.core.llm_factory.config.llm_base_url", "https://api.siliconflow.cn/v1")
    monkeypatch.setattr("app.core.llm_factory.config.llm_api_key", "sk-test")

    with patch("app.core.llm_factory.ChatOpenAI") as chat_openai:
        from app.core.llm_factory import LLMFactory

        LLMFactory.create_chat_model(temperature=0.2, streaming=False)

    chat_openai.assert_called_once()
    kwargs = chat_openai.call_args.kwargs
    assert kwargs["model"] == "deepseek-ai/DeepSeek-V4-Flash"
    assert kwargs["base_url"] == "https://api.siliconflow.cn/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["temperature"] == 0.2
    assert kwargs["streaming"] is False
