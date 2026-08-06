import asyncio

import pytest

from backend.workflow import checkpointer


@pytest.mark.asyncio
async def test_checkpointer_initialization_is_singleton_under_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory_calls = 0
    setup_calls = 0

    class FakeSaver:
        async def setup(self) -> None:
            nonlocal setup_calls
            setup_calls += 1
            await asyncio.sleep(0)

    class FakeContext:
        def __init__(self, saver: FakeSaver) -> None:
            self.saver = saver

        async def __aenter__(self) -> FakeSaver:
            return self.saver

        async def __aexit__(self, *_args: object) -> None:
            return None

    def fake_from_conn_string(_conn_string: str) -> FakeContext:
        nonlocal factory_calls
        factory_calls += 1
        return FakeContext(FakeSaver())

    monkeypatch.setattr(checkpointer, "_checkpointer", None)
    monkeypatch.setattr(checkpointer, "_exit_stack", None)
    monkeypatch.setattr(
        checkpointer.AsyncPostgresSaver,
        "from_conn_string",
        staticmethod(fake_from_conn_string),
    )

    first, second = await asyncio.gather(
        checkpointer.get_checkpointer(),
        checkpointer.get_checkpointer(),
    )

    assert first is second
    assert factory_calls == 1
    assert setup_calls == 1
