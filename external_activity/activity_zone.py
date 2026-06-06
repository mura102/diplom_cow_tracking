"""Определение зоны активности: кормовая зона (питание) или питьевая зона (питьё)."""

ZONE_FEED = "кормовая зона"
ZONE_DRINK = "питьевая зона"

FEED_KEYWORDS = (
    "кормов", "кормушк", "feed", "eat", "питан", "manger", "trough",
)
DRINK_KEYWORDS = (
    "питьев", "поилк", "drink", "water", "пить", "trough_water",
)


def normalize_zone(location: str) -> str:
    """
    Приводит строку локации к зоне: 'кормовая зона' или 'питьевая зона'.
    По умолчанию — кормовая зона.
    """
    text = (location or "").lower().strip()
    if any(k in text for k in DRINK_KEYWORDS):
        return ZONE_DRINK
    if any(k in text for k in FEED_KEYWORDS):
        return ZONE_FEED
    return ZONE_FEED


def zone_to_state(zone: str) -> str | None:
    """Зона камеры → состояние коровы на кадре."""
    z = normalize_zone(zone)
    if z == ZONE_DRINK:
        return "питье"
    if z == ZONE_FEED:
        return "питание"
    return "неизвестно"


def state_label(zone: str) -> str:
    z = normalize_zone(zone)
    return "питьё" if z == ZONE_DRINK else "питание"
