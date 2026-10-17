def escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input matches literally. Use with escape='\\\\'."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
