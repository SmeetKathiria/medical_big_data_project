from __future__ import annotations


def chunk_text(text: str, max_chars: int = 700) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()] or [text.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= max_chars:
            current = f"{current}\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks
