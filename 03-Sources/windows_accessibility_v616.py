"""Responsive layout metrics with DPI-independent thresholds. Abdelhalim Talbi."""
def display_metrics(width, height, scaling=1.0):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (width,height,scaling)):
        raise ValueError('Dimensions ou facteur DPI invalides')
    if not (640 <= width <= 20000 and 480 <= height <= 20000 and 0.5 <= scaling <= 4.0):
        raise ValueError('Dimensions ou facteur DPI hors limites')
    # Physical screen dimensions are normalized to 96-DPI logical pixels.
    logical_width, logical_height = width/scaling, height/scaling
    compact = logical_width < 1280 or logical_height < 720
    return {'compact':compact,'content_padding':10 if compact else 26,
            'rowheight':26 if compact else 29,'logical_width':round(logical_width),
            'logical_height':round(logical_height)}
