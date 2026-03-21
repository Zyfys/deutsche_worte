import pdfplumber


def extract_text(pdf_path: str, max_chars: int = 50000) -> str:
    """Извлекает текст из PDF. Ограничивает размер для хранения в БД."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    full_text = "\n\n".join(text_parts)
    return full_text[:max_chars]


def detect_level(text: str) -> str | None:
    """Пытается определить уровень учебника по его тексту."""
    text_lower = text[:2000].lower()
    for level in ["c2", "c1", "b2", "b1", "a2", "a1"]:
        if level in text_lower:
            return level.upper()
    return None
