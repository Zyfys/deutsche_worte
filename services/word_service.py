def format_word_message(data: dict) -> str:
    lines = []

    # Заголовок
    word = data.get("word", "")
    article = data.get("article")
    pos = data.get("part_of_speech", "")

    if article:
        lines.append(f"🎯 *{article} {word}*")
    else:
        lines.append(f"🎯 *{word}*")

    # Формы глагола
    praet = data.get("präteritum")
    perf = data.get("perfekt")
    plural = data.get("plural")

    if praet:
        lines.append(f"Präteritum: _{praet}_")
    if perf:
        lines.append(f"Perfekt: _{perf}_")
    if plural:
        lines.append(f"Plural: _{plural}_")

    lines.append("")

    # Перевод
    translation = data.get("translation", "")
    if translation:
        lines.append(f"📖 {translation}")
        lines.append("")

    # Синонимы
    synonyms = data.get("synonyms", [])
    for s in synonyms:
        lines.append(f"🔄 {s['word']} – {s['translation']}")

    # Антонимы
    antonyms = data.get("antonyms", [])
    for a in antonyms:
        lines.append(f"❌ {a['word']} – {a['translation']}")

    if synonyms or antonyms:
        lines.append("")

    # Примеры
    examples = data.get("examples", [])
    for ex in examples:
        lines.append(f"✨ _{ex}_")

    if examples:
        lines.append("")

    # Объяснение
    explanation = data.get("explanation", "")
    if explanation:
        lines.append(f"📚 {explanation}")

    return "\n".join(lines)


def format_lookup_message(data: dict) -> str:
    return format_word_message(data)
