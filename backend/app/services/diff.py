import difflib
import html

def _tokenize(text: str) -> list[str]:
    return text.split(" ")

def generate_diff_html(original: str, revised: str) -> str:
    original_words = _tokenize(original)
    revised_words = _tokenize(revised)

    matcher = difflib.SequenceMatcher(None, original_words, revised_words)
    parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            trecho = " ".join(revised_words[j1:j2])
            parts.append(html.escape(trecho))
        elif tag == "replace":
            removido = " ".join(original_words[i1:i2])
            adicionado = " ".join(revised_words[j1:j2])
            parts.append(f'<del>{html.escape(removido)}</del>')
            parts.append(f'<mark>{html.escape(adicionado)}</mark>')
        elif tag == "delete":
            removido = " ".join(original_words[i1:i2])
            parts.append(f'<del>{html.escape(removido)}</del>')
        elif tag == "insert":
            adicionado = " ".join(revised_words[j1:j2])
            parts.append(f'<mark>{html.escape(adicionado)}</mark>')

    return " ".join(parts)