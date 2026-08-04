"""LLM 配置门禁单元测试 —— 覆盖上传/重试硬拦截与已存 Key 验证路径。"""

import uuid
from datetime import datetime
from typing import Any

import pytest

from backend.api.v1.resume import (
    LLM_NOT_READY_CODE,
    retry_resume,
    upload_resume_endpoint,
)
from backend.api.v1.settings import LLMConfigTestRequest
from backend.api.v1.settings import test_llm_connection as llm_test_endpoint
from backend.application import llm_config_service


class _FakeSession:
    """最小化的 async session 桩：支持 get / commit。"""

    def __init__(self, config: Any = None) -> None:
        self._config = config
        self.commits = 0

    async def get(self, _model: Any, _pk: Any) -> Any:
        return self._config

    async def commit(self) -> None:
        self.commits += 1


class _FakeConfig:
    """最小化的 LLM 配置桩：仅承载验证逻辑访问的字段。"""

    def __init__(self) -> None:
        self.api_key_encrypted = "encrypted-key"
        self.verified = False
        self.last_verified_at: datetime | None = None


class _FakeEncryptor:
    def decrypt(self, value: str) -> str:
        assert value == "encrypted-key"
        return "sk-stored-plaintext"


class _FakeUploadFile:
    filename = "resume.pdf"

    async def read(self) -> bytes:
        return b"%PDF-1.4 fake"


# ---------------------------------------------------------------------------
# 上传 / 重试门禁
# ---------------------------------------------------------------------------


async def test_upload_blocked_when_llm_not_ready(monkeypatch: pytest.MonkeyPatch):
    async def _not_ready(_session: Any) -> bool:
        return False

    monkeypatch.setattr("backend.api.v1.resume.has_verified_config", _not_ready)

    res = await upload_resume_endpoint(_FakeUploadFile(), _FakeSession())  # type: ignore[arg-type]
    assert res.code == LLM_NOT_READY_CODE
    assert "LLM" in res.message


async def test_upload_passes_when_llm_ready(monkeypatch: pytest.MonkeyPatch):
    async def _ready(_session: Any) -> bool:
        return True

    async def _fake_upload(**_kwargs: Any) -> dict[str, str]:
        return {"resume_id": str(uuid.uuid4()), "file_id": "f1", "status": "uploaded"}

    monkeypatch.setattr("backend.api.v1.resume.has_verified_config", _ready)
    monkeypatch.setattr("backend.api.v1.resume.upload_resume", _fake_upload)

    res = await upload_resume_endpoint(_FakeUploadFile(), _FakeSession())  # type: ignore[arg-type]
    assert res.code == 0
    assert res.data.status == "uploaded"


async def test_retry_blocked_when_llm_not_ready(monkeypatch: pytest.MonkeyPatch):
    async def _not_ready(_session: Any) -> bool:
        return False

    monkeypatch.setattr("backend.api.v1.resume.has_verified_config", _not_ready)

    res = await retry_resume(uuid.uuid4(), _FakeSession())  # type: ignore[arg-type]
    assert res.code == LLM_NOT_READY_CODE


# ---------------------------------------------------------------------------
# 测试接口：已存 Key 验证路径
# ---------------------------------------------------------------------------


async def test_endpoint_rejects_without_api_key_and_config_id():
    body = LLMConfigTestRequest(provider="openai", model_name="gpt-5.5")
    res = await llm_test_endpoint(body, _FakeSession())  # type: ignore[arg-type]
    assert res.code == 400


async def test_connection_uses_stored_key_and_marks_verified(
    monkeypatch: pytest.MonkeyPatch,
):
    config = _FakeConfig()
    session = _FakeSession(config)
    received: dict[str, Any] = {}

    async def _fake_run(
        provider: str, api_key: str, model_name: str, base_url: str | None = None,
    ) -> dict[str, object]:
        received["api_key"] = api_key
        return {"success": True, "models": [model_name]}

    monkeypatch.setattr(llm_config_service, "_run_connection_test", _fake_run)
    monkeypatch.setattr(llm_config_service, "get_encryptor", lambda: _FakeEncryptor())

    result = await llm_config_service.test_connection(
        "openai", None, "gpt-5.5",
        session=session, config_id=uuid.uuid4(),  # type: ignore[arg-type]
    )

    # 用解密后的存储 Key 发起测试，并将配置标记为已验证
    assert result["success"] is True
    assert received["api_key"] == "sk-stored-plaintext"
    assert config.verified is True
    assert config.last_verified_at is not None
    assert session.commits == 1


async def test_connection_failure_resets_verified(monkeypatch: pytest.MonkeyPatch):
    config = _FakeConfig()
    config.verified = True
    session = _FakeSession(config)

    async def _fake_run(*_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {"success": False, "error": "invalid key"}

    monkeypatch.setattr(llm_config_service, "_run_connection_test", _fake_run)
    monkeypatch.setattr(llm_config_service, "get_encryptor", lambda: _FakeEncryptor())

    result = await llm_config_service.test_connection(
        "openai", None, "gpt-5.5",
        session=session, config_id=uuid.uuid4(),  # type: ignore[arg-type]
    )

    assert result["success"] is False
    assert config.verified is False


async def test_connection_without_any_key_fails():
    result = await llm_config_service.test_connection("openai", None, "gpt-5.5")
    assert result["success"] is False
    assert "API key" in str(result["error"])


async def test_run_connection_test_falls_back_to_chat_when_models_list_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    """OpenAI 兼容渠道未实现 models.list 时，回退 chat.completions 仍应成功。"""

    class _FakeModels:
        async def list(self) -> Any:
            raise RuntimeError("models endpoint not found")

    class _FakeCompletions:
        async def create(self, **_kwargs: Any) -> dict[str, str]:
            return {"id": "chatcmpl-test"}

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.models = _FakeModels()
            self.chat = _FakeChat()

    monkeypatch.setattr(
        "openai.AsyncOpenAI",
        _FakeOpenAI,
        raising=False,
    )
    # 直接 patch 导入路径：_run_connection_test 内部 from openai import AsyncOpenAI
    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "AsyncOpenAI", _FakeOpenAI)

    result = await llm_config_service._run_connection_test(
        "custom", "sk-test", "gpt-5.5", "https://example.com/v1",
    )
    assert result["success"] is True
    assert result["models"] == ["gpt-5.5"]
    assert "warning" in result


async def test_run_connection_test_returns_models_list(monkeypatch: pytest.MonkeyPatch):
    """models.list 成功时返回去重后的模型清单，当前模型置顶。"""

    class _Model:
        def __init__(self, model_id: str) -> None:
            self.id = model_id

    class _FakeModels:
        async def list(self) -> Any:
            return type(
                "Resp",
                (),
                {"data": [_Model("zeta"), _Model("alpha"), _Model("gpt-5.5")]},
            )()

    class _FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.models = _FakeModels()

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "AsyncOpenAI", _FakeOpenAI)

    result = await llm_config_service._run_connection_test(
        "openai", "sk-test", "gpt-5.5", None,
    )
    assert result["success"] is True
    assert result["models"][0] == "gpt-5.5"
    assert set(result["models"]) == {"gpt-5.5", "alpha", "zeta"}


async def test_run_connection_test_client_init_error_is_caught(
    monkeypatch: pytest.MonkeyPatch,
):
    """客户端构造失败（如缺 socksio）不得抛出，应返回 success=false。"""

    class _Boom:
        def __init__(self, **_kwargs: Any) -> None:
            raise ImportError(
                "Using SOCKS proxy, but the 'socksio' package is not installed."
            )

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "AsyncOpenAI", _Boom)

    result = await llm_config_service._run_connection_test(
        "openai", "sk-test", "gpt-5.5", None,
    )
    assert result["success"] is False
    assert "socksio" in str(result["error"]).lower() or "SOCKS" in str(result["error"])
