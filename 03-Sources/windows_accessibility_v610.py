"""Deterministic Windows display sizing helpers; author Abdelhalim Talbi."""
def display_metrics(width, height):
    if not isinstance(width, int) or isinstance(width, bool) or not isinstance(height, int) or isinstance(height, bool) or width < 640 or height < 480:
        raise ValueError("invalid display dimensions")
    compact = width < 1280 or height < 720
    return {"compact": compact, "content_padding": 10 if compact else 26, "rowheight": 26 if compact else 29}
