def format_som(amount: int) -> str:
    """Narxni ko'rsatish uchun formatlash."""
    return f"{amount} so'm"


def percent_of(amount: int, percent: int) -> int:
    return amount * percent // 100
