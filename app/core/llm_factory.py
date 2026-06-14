"""LLM 工厂类 - 统一通过 OpenAI 兼容协议调用模型服务。"""

from langchain_openai import ChatOpenAI
from app.config import config
from loguru import logger


class LLMFactory:
    """LLM 工厂类 - 使用 OpenAI 兼容模式"""

    @staticmethod
    def create_chat_model(
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = True,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatOpenAI:
        model = model or config.llm_model
        base_url = base_url or config.llm_base_url
        api_key = api_key or config.llm_api_key

        if not api_key or api_key == "your-api-key-here":
            raise ValueError("请设置环境变量 LLM_API_KEY")

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            base_url=base_url,
            api_key=api_key,
        )

        logger.debug(f"Chat model 初始化完成: model={model}, base_url={base_url}, streaming={streaming}")
        return llm

# 全局 LLM 工厂实例
llm_factory = LLMFactory()
