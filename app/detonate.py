"""Detonation chamber (DECISIONS 14:59): when the brake is unsure (route DETONATE), a sandboxed agent clicks the target
and reports what happened. Dan's managed/detonate.py replaces this stub; the signature is frozen:

  detonate(page_html, click_xy, task) -> {"what_happened": str, "verdict": str, "s": float}

The app treats verdict "safe" as allow; anything else (e.g. "harmful", "unknown") as a stop (fail closed).
"""
import time


def detonate(page_html: str, click_xy: tuple[int, int], task: str) -> dict:
    try:
        from managed.detonate import detonate as _real  # type: ignore
    except Exception:
        _real = None
    if _real is not None:
        return _real(page_html, click_xy, task)
    t = time.perf_counter()
    return {"what_happened": "stub: no sandbox yet (managed/detonate.py not on main); failing closed",
            "verdict": "unknown", "s": round(time.perf_counter() - t, 3), "stub": True}
