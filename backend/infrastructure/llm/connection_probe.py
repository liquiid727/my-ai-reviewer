"""Provider connectivity probes used by LLM settings verification.

Lives in infrastructure so application code does not import provider SDKs.
"""

from __future__ import annotations

import asyncio


def _friendly_connection_error(exc: BaseException) -> str:
    message = str(exc).strip() or type(exc).__name__
    lowered = message.lower()
    if "socksio" in lowered or "socks proxy" in lowered:
        return (
            "当前环境启用了 SOCKS 代理，但缺少 socksio 依赖。"
            "请执行 `uv add 'httpx[socks]'` 后重启后端，或取消 ALL_PROXY/HTTPS_PROXY。"
        )
    if "encryption_key" in lowered:
        return "ENCRYPTION_KEY 未配置，无法读写已保存的 API Key。请先在 .env 中设置后重启后端。"
    if type(exc).__name__ == "InvalidToken" or "invalidtoken" in lowered:
        return (
            "已保存的 API Key 无法解密（ENCRYPTION_KEY 已变更或与写入时不一致）。"
            "请删除该配置后重新填写 API Key 保存，或在测试时重新输入 API Key。"
        )
    return message


async def run_connection_test(
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
) -> dict[str, object]:
    """Send a minimal provider request / list models to verify connectivity."""
    if provider == "anthropic":
        try:
            from anthropic import AsyncAnthropic

            anthropic_client = AsyncAnthropic(api_key=api_key, base_url=base_url)
            await asyncio.wait_for(
                anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                ),
                timeout=15,
            )
            return {"success": True, "models": [model_name]}
        except Exception as exc:
            return {"success": False, "error": _friendly_connection_error(exc)}

    try:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
        try:
            models_response = await asyncio.wait_for(
                openai_client.models.list(),
                timeout=15,
            )
            model_ids = sorted(
                {m.id for m in models_response.data if getattr(m, "id", None)},
                key=str.lower,
            )
            if model_name and model_name not in model_ids:
                model_ids = [model_name, *model_ids]
            elif model_name in model_ids:
                model_ids = [model_name, *[m for m in model_ids if m != model_name]]
            return {"success": True, "models": model_ids[:100]}
        except Exception as list_exc:
            try:
                await asyncio.wait_for(
                    openai_client.chat.completions.create(
                        model=model_name,
                        max_tokens=1,
                        messages=[{"role": "user", "content": "hi"}],
                    ),
                    timeout=15,
                )
                return {
                    "success": True,
                    "models": [model_name],
                    "warning": (
                        "models.list unavailable; verified via chat.completions instead: "
                        f"{_friendly_connection_error(list_exc)}"
                    ),
                }
            except Exception as chat_exc:
                return {"success": False, "error": _friendly_connection_error(chat_exc)}
    except Exception as exc:
        return {"success": False, "error": _friendly_connection_error(exc)}
