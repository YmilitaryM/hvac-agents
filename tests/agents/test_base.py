import pytest
from unittest.mock import patch, MagicMock
from src.agents.base import create_llm_client, BaseAgent, AgentContext
from src.config import Config, LLMConfig, set_config, get_config


class TestCreateLLMClient:
    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Save and restore config around each test."""
        import src.config as cfg
        old = cfg._default_config
        yield
        cfg._default_config = old

    def test_anthropic_deep_model(self):
        cfg = Config(llm=LLMConfig(
            provider="anthropic",
            deep_model="claude-sonnet-4-6",
            quick_model="claude-haiku-4-5-20251001",
        ))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(deep=True)
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-6"

    def test_anthropic_quick_model(self):
        cfg = Config(llm=LLMConfig(
            provider="anthropic",
            deep_model="claude-sonnet-4-6",
            quick_model="claude-haiku-4-5-20251001",
        ))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(deep=False)
            call_kwargs = mock.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_openai_provider(self):
        cfg = Config(llm=LLMConfig(
            provider="openai",
            deep_model="gpt-4o",
            quick_model="gpt-4o-mini",
        ))
        set_config(cfg)
        with patch("src.agents.base.ChatOpenAI") as mock:
            create_llm_client(deep=True)
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"

    def test_explicit_model_overrides_config(self):
        cfg = Config(llm=LLMConfig(provider="anthropic"))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(model="claude-opus-4-7", deep=True)
            call_kwargs = mock.call_args[1]
            assert call_kwargs["model"] == "claude-opus-4-7"

    def test_google_provider_raises_not_implemented(self):
        cfg = Config(llm=LLMConfig(provider="google"))
        set_config(cfg)
        with pytest.raises(NotImplementedError, match="Google"):
            create_llm_client()

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            create_llm_client(provider="unknown_provider")

    def test_temperature_and_max_tokens_passed(self):
        cfg = Config(llm=LLMConfig(provider="anthropic"))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(temperature=0.7, max_tokens=1024)
            call_kwargs = mock.call_args[1]
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 1024

    def test_extra_kwargs_passed(self):
        cfg = Config(llm=LLMConfig(provider="anthropic"))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(streaming=True, timeout=30)
            call_kwargs = mock.call_args[1]
            assert call_kwargs["streaming"] is True
            assert call_kwargs["timeout"] == 30

    def test_explicit_api_key_and_base_url_override(self):
        cfg = Config(llm=LLMConfig(
            provider="anthropic",
            api_key="config-key",
            base_url="https://config.example.com",
        ))
        set_config(cfg)
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(api_key="override-key", base_url="https://override.example.com")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["api_key"] == "override-key"
            assert call_kwargs["base_url"] == "https://override.example.com"

    def test_provider_defaults_from_config(self):
        cfg = Config(llm=LLMConfig(
            provider="openai",
            deep_model="gpt-4o",
            quick_model="gpt-4o-mini",
        ))
        set_config(cfg)
        # provider=None should fall back to config's "openai"
        with patch("src.agents.base.ChatOpenAI") as mock:
            create_llm_client()  # provider=None, deep defaults to True
            mock.assert_called_once()

    def test_model_defaults_from_config_when_none(self):
        cfg = Config(llm=LLMConfig(
            provider="anthropic",
            deep_model="claude-sonnet-4-6",
            quick_model="claude-haiku-4-5-20251001",
        ))
        set_config(cfg)
        # model=None for quick should use quick_model from config
        with patch("src.agents.base.ChatAnthropic") as mock:
            create_llm_client(deep=False)  # model=None
            call_kwargs = mock.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


class TestAgentContext:
    def test_default_context(self):
        ctx = AgentContext()
        assert ctx.tools == []
        assert ctx.extra == {}

    def test_context_with_tools(self):
        def dummy_tool():
            pass

        ctx = AgentContext(tools=[dummy_tool], extra={"key": "value"})
        assert len(ctx.tools) == 1
        assert ctx.extra["key"] == "value"


class TestBaseAgent:
    def test_concrete_agent_implementation(self):
        from langchain_core.language_models import BaseChatModel

        class DummyLLM(BaseChatModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                pass

            def _llm_type(self):
                return "dummy"

        class TestAgent(BaseAgent):
            async def run(self, input_data):
                return {"result": input_data.get("key", "default")}

        llm = DummyLLM()
        agent = TestAgent(name="test_agent", llm=llm)
        assert agent.name == "test_agent"
        assert agent.llm is llm

    def test_reset_context(self):
        from langchain_core.language_models import BaseChatModel

        class DummyLLM(BaseChatModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                pass

            def _llm_type(self):
                return "dummy"

        class TestAgent(BaseAgent):
            async def run(self, input_data):
                return {}

        agent = TestAgent(name="test", llm=DummyLLM())
        old_ctx = agent.context
        new_ctx = AgentContext(tools=[lambda: None])
        agent.reset_context(new_ctx)
        assert agent.context is new_ctx
        assert agent.context is not old_ctx

    def test_abstract_run_enforced(self):
        from langchain_core.language_models import BaseChatModel

        class DummyLLM(BaseChatModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                pass

            def _llm_type(self):
                return "dummy"

        with pytest.raises(TypeError):
            BaseAgent(name="bad", llm=DummyLLM())
