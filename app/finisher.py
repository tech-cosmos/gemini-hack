"""HOOK: Managed Agents finisher from Dan's `managed/` lane, which will provide `finish(task, page_url)`.

finish(task, page_url) -> dict or None when the managed lane isn't on main yet. The app calls it after the
protected run clicks the task button and shows whatever it returns. `page_url` is served by app/server.py
(/page/<id>.html)."""
import time


def finish(task: str, page_url: str) -> dict | None:
    try:
        from managed import finish as _finish  # type: ignore
    except Exception:
        return None
    t = time.perf_counter()
    out = _finish(task, page_url)
    return {"result": out, "s": round(time.perf_counter() - t, 3)}
