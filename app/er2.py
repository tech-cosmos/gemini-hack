"""HOOK (not implemented yet): Gemini Robotics-ER 2 circles the element the user's task really needs.

circle_target(task, png) -> {"x", "y", "r", "label", "s"} in page pixels, or None when not available.
The app calls this after a STOP and draws a green circle if it gets a dict. Model: gemini-robotics-er-2-preview."""


def circle_target(task: str, png: bytes) -> dict | None:
    return None
