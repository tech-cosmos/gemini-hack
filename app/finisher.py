"""HOOK: Managed Agents run from Dan's lane: managed/finish.py `finish(task, html, mode)` runs the protected agent on
Managed Agents (every click it wants goes through brake.check). It re-does the whole task (~18 s live, kill test), so the
app calls it only when MANAGED_FINISH=1, after the local protected run finished. Returns None when off or unavailable."""
import os
import time


def finish(task: str, html: str, mode: str) -> dict | None:
    if os.environ.get("MANAGED_FINISH", "") in ("", "0"):
        return None
    try:
        from managed.finish import finish as _finish  # type: ignore
    except Exception:
        return None
    t = time.perf_counter()
    out = _finish(task, html, mode)
    return {"result": out, "done": bool((out or {}).get("done")), "s": round(time.perf_counter() - t, 3)}
