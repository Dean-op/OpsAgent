from unittest.mock import patch


def test_openai_compatible_embeddings_use_configurable_endpoint():
    from app.services.vector_embedding_service import OpenAICompatibleEmbeddings

    with patch("app.services.vector_embedding_service.OpenAI") as openai_client:
        embeddings = OpenAICompatibleEmbeddings(
            api_key="sk-test",
            base_url="https://api.siliconflow.cn/v1",
            model="Qwen/Qwen3-Embedding-0.6B",
            dimensions=1024,
        )

    openai_client.assert_called_once_with(
        api_key="sk-test",
        base_url="https://api.siliconflow.cn/v1",
    )
    assert embeddings.model == "Qwen/Qwen3-Embedding-0.6B"
    assert embeddings.dimensions == 1024


def test_embed_query_sends_dimensions_to_provider():
    from app.services.vector_embedding_service import OpenAICompatibleEmbeddings

    with patch("app.services.vector_embedding_service.OpenAI") as openai_client:
        client_instance = openai_client.return_value
        response_item = type("EmbeddingItem", (), {"embedding": [0.1, 0.2]})
        client_instance.embeddings.create.return_value = type(
            "EmbeddingResponse",
            (),
            {"data": [response_item]},
        )
        embeddings = OpenAICompatibleEmbeddings(
            api_key="sk-test",
            base_url="https://api.siliconflow.cn/v1",
            model="Qwen/Qwen3-Embedding-0.6B",
            dimensions=1024,
        )

        result = embeddings.embed_query("hello")

    assert result == [0.1, 0.2]
    client_instance.embeddings.create.assert_called_once_with(
        model="Qwen/Qwen3-Embedding-0.6B",
        input="hello",
        dimensions=1024,
        encoding_format="float",
    )
