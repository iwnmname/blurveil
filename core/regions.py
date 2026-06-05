from __future__ import annotations


Rect = tuple[int, int, int, int]


def clamp_rect(rect: Rect, image_shape: tuple[int, ...]) -> Rect | None:
    x, y, w, h = rect
    height, width = image_shape[:2]

    x_min = max(0, x)
    y_min = max(0, y)
    x_max = min(width, x + w)
    y_max = min(height, y + h)

    if x_max <= x_min or y_max <= y_min:
        return None
    return (x_min, y_min, x_max - x_min, y_max - y_min)


def pad_rect(rect: Rect, pad: int, image_shape: tuple[int, ...] | None = None) -> Rect:
    x, y, w, h = rect
    padded = (max(0, x - pad), max(0, y - pad), w + pad * 2, h + pad * 2)
    if image_shape is None:
        return padded
    return clamp_rect(padded, image_shape) or padded


def pad_rect_xy(rect: Rect, image_shape: tuple[int, ...], pad_x: int, pad_y: int | None = None) -> Rect | None:
    if pad_y is None:
        pad_y = pad_x
    x, y, w, h = rect
    return clamp_rect((x - pad_x, y - pad_y, w + pad_x * 2, h + pad_y * 2), image_shape)


def union_rect(rects: list[Rect]) -> Rect | None:
    if not rects:
        return None

    x_min = min(rect[0] for rect in rects)
    y_min = min(rect[1] for rect in rects)
    x_max = max(rect[0] + rect[2] for rect in rects)
    y_max = max(rect[1] + rect[3] for rect in rects)
    return (x_min, y_min, x_max - x_min, y_max - y_min)


def dedupe_regions(regions: list[Rect]) -> list[Rect]:
    seen = set()
    result = []
    for region in regions:
        if region not in seen:
            seen.add(region)
            result.append(region)
    return result
