"""Deterministic model client for coding-agent loop tests."""


class ScriptedApiClient:
    """Return scripted model responses and record prompts."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._responses:
            return "<final>done</final>"
        return self._responses.pop(0)
