"""HOOK (not implemented yet): Gemini 4 Carbon writes a one-line reason for a stop (or an unsure pass).

explain(task, png, click, brake) -> {"text", "s", "model"} or None when not available.
`brake` is the brake.check() dict. The app shows `text` under the STOPPED card if it gets a dict."""


def explain(task: str, png: bytes, click: tuple[int, int], brake: dict) -> dict | None:
    return None
