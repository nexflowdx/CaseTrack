import re
import spacy

nlp = spacy.load("pt_core_news_md")


class UnresolvedIdentifierError(ValueError):
    def __init__(self, message: str, partial_text: str, unresolved: list[str]):
        super().__init__(message)
        self.partial_text = partial_text
        self.unresolved = unresolved


def anonymize(text: str, name_map: dict[str, str] | None = None) -> tuple[str, dict[str, str]]:
    if name_map is None:
        name_map = {}

    doc = nlp(text)
    result_parts: list[str] = []
    current_span: list = []

    def flush_span():
        if not current_span:
            return
        original = " ".join(t.text for t in current_span)
        trailing_ws = current_span[-1].whitespace_
        identifier = None
        for key, value in name_map.items():
            if value == original:
                identifier = key
                break
        if identifier is None:
            identifier = f"Pessoa {chr(65 + len(name_map))}"
            name_map[identifier] = original
        result_parts.append(identifier + trailing_ws)
        current_span.clear()

    for token in doc:
        is_name = token.pos_ == "PROPN" or token.ent_type_ == "PER"
        if is_name:
            current_span.append(token)
        else:
            flush_span()
            result_parts.append(token.text_with_ws)

    flush_span()

    return "".join(result_parts).strip(), name_map


def deanonymize(text: str, name_map: dict[str, str]) -> str:
    identifiers_in_text = set(re.findall(r'Pessoa [A-Z]', text))
    orphaned = identifiers_in_text - set(name_map.keys())
    for identifier, original in name_map.items():
        text = text.replace(identifier, original)
    if orphaned:
        raise UnresolvedIdentifierError(
            f"Identificadores não resolvidos: {', '.join(sorted(orphaned))}",
            partial_text=text,
            unresolved=sorted(orphaned),
        )
    return text