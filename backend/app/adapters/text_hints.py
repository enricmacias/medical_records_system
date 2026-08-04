"""Lightweight heuristics to help the LLM with messy clinic PDF layouts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.adapters.pet_breed_catalog import is_known_dog_or_cat_breed


_LABEL_HINTS = {
    "name": [r"nombre", r"name", r"paciente", r"mascota"],
    "species": [r"especie", r"species"],
    "breed": [r"raza", r"breed"],
    "sex": [r"sexo", r"sex", r"g[eé]nero"],
    "dob": [r"f/?nto", r"f\.?\s*nac", r"fecha\s+de\s+nacimiento", r"date\s+of\s+birth", r"dob"],
    "microchip": [r"n[ºo°]?\s*chip", r"microchip", r"chip"],
    "owner": [r"cliente", r"propietario", r"owner", r"tutor"],
}

_VISIT_HEADER = re.compile(
    r"(?m)^\s*[-–—]?\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*[-–—]\s*(?:\d{1,2}:\d{2})?\s*[-–—]?\s*$"
)

_DIAGNOSIS_KEYWORDS = [
    (r"giardia", "Giardiasis"),
    (r"conjuntivitis", "Conjuntivitis"),
    (r"otitis", "Otitis"),
    (r"cuerpo(?:s)?\s+extra[nñ]o", "Cuerpo extraño"),
    (r"deshidrat", "Deshidratación"),
    (r"diarrea", "Diarrea"),
    (r"enteritis", "Enteritis"),
    (r"alergia\s+alimentaria|intolerancia", "Intolerancia/alergia alimentaria"),
    (r"leishmania", "Leishmaniasis (test/vacuna)"),
    (r"papiloma", "Papiloma"),
]

_MEDICATION_NAMES = [
    "Metronidazol",
    "Metrobactin",
    "Metrocare",
    "Fortiflora",
    "Tobradex",
    "Tobrex",
    "Lubrithal",
    "Panacur",
    "Prazitel",
    "Milbemax",
    "Milpro",
    "Vetgastril",
    "Omeprazol",
    "Salazopyrina",
    "Entero Vital",
    "Promax",
    "Seresto",
    "Effitix",
    "Synoquin",
    "Impromune",
    "Cristalmina",
]

_INLINE_LABEL_VALUE = re.compile(
    r"(?i)(nacimiento|f/?nto|f\.?\s*nac(?:imiento)?|sexo|sex|especie|species|raza|breed|chip|microchip)"
    r"\s*:\s*"
    r"([^:]+?)"
    r"(?=\s+(?:nacimiento|f/?nto|f\.?\s*nac(?:imiento)?|sexo|sex|especie|species|raza|breed|estado|chip|microchip)\s*:|$)",
)

_INLINE_LABEL_TO_FIELD = {
    "nacimiento": "pet.date_of_birth",
    "f/nto": "pet.date_of_birth",
    "f.nac": "pet.date_of_birth",
    "f.nacimiento": "pet.date_of_birth",
    "fechadenacimiento": "pet.date_of_birth",
    "dateofbirth": "pet.date_of_birth",
    "dob": "pet.date_of_birth",
    "sexo": "pet.sex",
    "sex": "pet.sex",
    "especie": "pet.species",
    "species": "pet.species",
    "raza": "pet.breed",
    "breed": "pet.breed",
    "chip": "pet.microchip",
    "microchip": "pet.microchip",
    "nchip": "pet.microchip",
    "nochip": "pet.microchip",
}

_STANDALONE_SEX_LINE = re.compile(
    r"(?im)^(?:sexo\s+)?(hembra|macho|male|female)\b",
)

_NAME_NACIMIENTO_LINE = re.compile(
    r"(?im)^([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-']*)\s*[-–—]\s*nacimiento:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
)

_NOMBRE_PREFIX_LINE = re.compile(r"(?im)^nombre\s+(.+)$")

_HEMBRA_ESTADO_PESO_LINE = re.compile(
    r"(?im)^(hembra|macho|male|female)\s+estado:\s*(\S+)\s+peso:\s*([\d.,]+)\s*(kg|g)?",
)

_DATE_PATTERN = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")

_DOG_SPECIES = re.compile(r"(?i)(canino|canina|canine|perro|perros|dog|cão)")
_CAT_SPECIES = re.compile(r"(?i)(felino|felina|feline|gato|gatos|cat|gata)")

_SPECIES_TOKENS = (
    "canino",
    "canina",
    "canine",
    "perro",
    "felino",
    "felina",
    "feline",
    "gato",
    "dog",
    "cat",
)
_SPECIES_TOKEN_PATTERN = "|".join(_SPECIES_TOKENS)

_SPECIES_BREED_LINE = re.compile(
    rf"(?im)^(?P<species>{_SPECIES_TOKEN_PATTERN})\s*[-–—]\s*(?P<breed>.+)$",
)
_SPECIES_BREED_SPACE_LINE = re.compile(
    rf"(?im)^(?P<species>{_SPECIES_TOKEN_PATTERN})\s+(?P<breed>[A-Za-zÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-']{{2,}})$",
)
_STANDALONE_SPECIES_LINE = re.compile(
    rf"(?im)^(?P<species>{_SPECIES_TOKEN_PATTERN})\s*[.:]?\s*$",
)
_FEMALE_SPECIES_FORMS = frozenset({"canina", "felina", "gata"})

_PET_NAME_LABEL_WITH_COLON = re.compile(
    r"(?i)(?:pet|mascota|paciente|patient)\s*:\s*([^,\n|]+)",
)
_PET_NAME_NOMBRE_LABEL = re.compile(
    r"(?i)(?:nombre|name)\s*:\s*([^,\n|]+)",
)
_PET_NAME_LABEL_WORD = re.compile(
    r"(?i)(?:patient|pet|paciente|mascota)\s+([A-Za-zÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ'-]+)\b",
)
_STANDALONE_CAPS_NAME_LINE = re.compile(
    r"^(?P<name>[A-ZÁÉÍÓÚÜÑ]{2,}(?:'[A-ZÁÉÍÓÚÜÑ]+)?)\s*[.:]?\s*$",
)
_STANDALONE_TITLE_CASE_NAME_LINE = re.compile(
    r"^(?P<name>[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{1,14})\s*[.:]?\s*$",
)
_STANDALONE_QUOTED_NAME_LINE = re.compile(
    r'^["\'](?P<name>[^"\']{2,30})["\']\s*[.:]?\s*$',
)
_LABELED_QUOTED_PET_NAME = re.compile(
    r'(?i)(?:pet|mascota|paciente|patient|nombre|name)\s*[:\-]?\s*["\']([^"\']{2,30})["\']',
)
_QUOTED_PET_NAME_PHRASE = re.compile(
    r'(?i)(?:known\s+as|aka|se\s+llama|nickname|alias|responds\s+to|apodado)\s*'
    r'["\']([^"\']{2,30})["\']',
)
_ALL_CAPS_NAME_TOKEN = re.compile(r"\b([A-ZÁÉÍÓÚÜÑ]{2,}(?:'[A-ZÁÉÍÓÚÜÑ]+)?)\b")

_PET_NAME_REJECT_FOLLOWING = frozenset(
    {
        "record",
        "datos",
        "del",
        "de",
        "la",
        "el",
        "los",
        "las",
        "the",
        "information",
        "info",
        "file",
        "chart",
        "history",
        "historial",
        "consulta",
        "visit",
        "visita",
        "revision",
        "rutina",
        "routine",
        "check",
        "information",
    }
)

_PET_NAME_SKIP_TOKENS = frozenset(
    {
        "clinica",
        "clínica",
        "veterinaria",
        "veterinario",
        "historial",
        "consulta",
        "nombre",
        "name",
        "especie",
        "species",
        "raza",
        "breed",
        "sexo",
        "sex",
        "canino",
        "canina",
        "felino",
        "felina",
        "perro",
        "gato",
        "dog",
        "cat",
        "macho",
        "hembra",
        "male",
        "female",
        "fertil",
        "estado",
        "peso",
        "propietario",
        "cliente",
        "owner",
        "tutor",
        "fecha",
        "nacimiento",
        "microchip",
        "chip",
        "datos",
        "mascota",
        "paciente",
        "patient",
        "pet",
        "historia",
        "revision",
        "rutina",
        "routine",
        "check",
        "visit",
        "visita",
        "madrid",
        "boadilla",
        "sunshine",
        "vet",
        "clinic",
        "central",
        "parque",
        "oeste",
        "kivet",
        "ave",
        "reptil",
        "domestic",
        "shorthair",
        "labrador",
        "retriever",
        "terrier",
        "persa",
        "yorkshire",
        "phone",
        "email",
        "address",
        "owner",
        "tel",
        "teléfono",
        "telefono",
        "correo",
        "direccion",
        "dirección",
        "domicilio",
    }
)

_COMMON_NON_NAME_WORDS = frozenset(
    {
        # Document / linguistic meta (EN)
        "summary",
        "grammar",
        "punctuation",
        "introduction",
        "conclusion",
        "abstract",
        "appendix",
        "section",
        "chapter",
        "paragraph",
        "sentence",
        "document",
        "page",
        "footer",
        "header",
        "title",
        "subtitle",
        "note",
        "notes",
        "reminder",
        "warning",
        "error",
        "example",
        "sample",
        "template",
        "format",
        "formatting",
        "style",
        "spelling",
        "vocabulary",
        "syntax",
        "language",
        "english",
        "spanish",
        "content",
        "contents",
        "index",
        "table",
        "figure",
        "reference",
        "references",
        "citation",
        "attachment",
        "subject",
        "topic",
        "theme",
        "overview",
        "outline",
        "draft",
        "final",
        "copy",
        "original",
        "duplicate",
        "version",
        "revision",
        "edition",
        "text",
        "typing",
        "writing",
        "reading",
        "lesson",
        "exercise",
        "homework",
        "assignment",
        "question",
        "answer",
        "definition",
        "meaning",
        "translation",
        "description",
        "instruction",
        "instructions",
        "guideline",
        "guidelines",
        "policy",
        "policies",
        "agreement",
        "contract",
        "terms",
        "conditions",
        "disclaimer",
        "copyright",
        "trademark",
        "license",
        "permission",
        "approval",
        "signature",
        "signed",
        "unsigned",
        "blank",
        "empty",
        "null",
        "none",
        "unknown",
        "pending",
        "missing",
        "incomplete",
        "complete",
        "completed",
        "active",
        "inactive",
        "enabled",
        "disabled",
        "true",
        "false",
        "yes",
        "no",
        "male",
        "female",
        # Document / linguistic meta (ES)
        "resumen",
        "gramática",
        "gramatica",
        "puntuación",
        "puntuacion",
        "introducción",
        "introduccion",
        "conclusión",
        "párrafo",
        "parrafo",
        "sección",
        "seccion",
        "capítulo",
        "capitulo",
        "documento",
        "página",
        "pagina",
        "nota",
        "notas",
        "ejemplo",
        "muestra",
        "plantilla",
        "formato",
        "estilo",
        "ortografía",
        "ortografia",
        "vocabulario",
        "sintaxis",
        "idioma",
        "inglés",
        "ingles",
        "español",
        "espanol",
        "contenido",
        "índice",
        "indice",
        "tabla",
        "figura",
        "referencia",
        "referencias",
        "asunto",
        "tema",
        "borrador",
        "copia",
        "original",
        "duplicado",
        "versión",
        "version",
        "revisión",
        "texto",
        "escritura",
        "lectura",
        "lección",
        "leccion",
        "ejercicio",
        "tarea",
        "pregunta",
        "respuesta",
        "definición",
        "definicion",
        "significado",
        "traducción",
        "traduccion",
        "descripción",
        "descripcion",
        "instrucción",
        "instruccion",
        "instrucciones",
        "política",
        "politica",
        "acuerdo",
        "contrato",
        "condiciones",
        "permiso",
        "aprobación",
        "aprobacion",
        "firma",
        "vacío",
        "vacio",
        "ninguno",
        "desconocido",
        "pendiente",
        "incompleto",
        "completo",
        "completado",
        # Clinical / admin generic
        "diagnosis",
        "diagnóstico",
        "diagnostico",
        "treatment",
        "tratamiento",
        "medication",
        "medications",
        "prescription",
        "receta",
        "vaccine",
        "vacuna",
        "vaccination",
        "procedure",
        "procedimiento",
        "examination",
        "examen",
        "assessment",
        "evaluation",
        "observation",
        "observación",
        "observacion",
        "symptom",
        "symptoms",
        "síntoma",
        "sintoma",
        "condition",
        "disorder",
        "disease",
        "enfermedad",
        "allergy",
        "alergia",
        "anesthesia",
        "anestesia",
        "surgery",
        "cirugía",
        "cirugia",
        "hospitalization",
        "discharge",
        "admission",
        "billing",
        "invoice",
        "payment",
        "total",
        "subtotal",
        "quantity",
        "amount",
        "price",
        "cost",
        "balance",
        "account",
        "statement",
        "report",
        "reports",
        "informe",
        "informes",
        "result",
        "results",
        "resultado",
        "resultados",
        "laboratory",
        "laboratorio",
        "analysis",
        "análisis",
        "analisis",
        "radiograph",
        "radiografía",
        "radiografia",
        "ultrasound",
        "ecografía",
        "ecografia",
        "appointment",
        "cita",
        "schedule",
        "calendar",
        "reminder",
        "followup",
        "follow-up",
        "seguimiento",
    }
)

# Demographic heuristics scan the header region (first N lines of raw_text).
HEADER_SCAN_LINES = 100
_INFERENCE_SAMPLE_CHARS = 8000


def _header_sample(text: str) -> str:
    """First HEADER_SCAN_LINES lines used for demographic hints and global inference."""
    sample = "\n".join(text.splitlines()[:HEADER_SCAN_LINES])
    if len(sample) > _INFERENCE_SAMPLE_CHARS:
        return sample[:_INFERENCE_SAMPLE_CHARS]
    return sample


def _strip_surrounding_quotes(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "\"'":
        return cleaned[1:-1].strip()
    return cleaned


def _clean_inferred_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    cleaned = re.sub(r"^\|+\s*", "", cleaned)
    cleaned = re.sub(r"\s*\|+$", "", cleaned)
    cleaned = cleaned.strip(" ,;")
    cleaned = _strip_surrounding_quotes(cleaned)
    if not cleaned or cleaned in ("—", "-", "n/a", "n/d"):
        return None
    return cleaned


def _is_pipe_table_row_value(value: str) -> bool:
    """True when a label matcher captured a whole Word table row instead of one cell."""
    return "|" in value


def _is_likely_pet_proper_name(name: str) -> bool:
    """Reject generic document words that are not plausible pet proper names."""
    candidate = name.strip()
    if not candidate:
        return False
    tokens = [t.strip(".,;:'\"") for t in re.split(r"[\s\-]+", candidate)]
    tokens = [t for t in tokens if t]
    if not tokens:
        return False
    if len(tokens) > 2:
        return False
    for token in tokens:
        lower = token.lower()
        if lower in _COMMON_NON_NAME_WORDS:
            return False
        if lower in _PET_NAME_SKIP_TOKENS or lower in _PET_NAME_REJECT_FOLLOWING:
            return False
        if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", token):
            return False
    return True


def validated_pet_name(value: str | None) -> str | None:
    """Return the name when it passes structural and proper-name checks; else None."""
    if value is None or not str(value).strip():
        return None
    name, _ = _split_name_and_nacimiento(str(value).strip())
    candidate = (name or str(value).strip()).strip()
    if not _is_plausible_pet_name_candidate(candidate):
        return None
    if not _is_likely_pet_proper_name(candidate):
        return None
    return candidate


def resolve_pet_name(
    record_name: str | None,
    hint_name: str | None,
) -> str | None:
    """Prefer a validated record name; fall back to a validated hint name."""
    validated = validated_pet_name(record_name)
    if validated:
        return validated
    return validated_pet_name(hint_name)


@dataclass(frozen=True)
class _PetNameCandidate:
    name: str
    source: str
    line_index: int | None = None


_PET_NAME_SOURCE_SCORES: dict[str, int] = {
    "colon_pet_label": 100,
    "colon_name_label": 85,
    "quoted_label": 88,
    "label_word": 75,
    "quoted_phrase": 78,
    "nombre_prefix": 70,
    "standalone_title": 50,
    "quoted_line": 55,
    "standalone_caps": 45,
    "caps_token": 25,
}
_PET_NAME_WEAK_SOURCES = frozenset(
    {"standalone_caps", "caps_token", "standalone_title", "quoted_line"}
)
_DEMOGRAPHIC_CONTEXT_PATTERN = re.compile(
    r"(?i)(?:especie|species|raza|breed|sexo|sex|macho|hembra|male|female|"
    r"canino|felino|canine|feline|perro|gato|dog|cat|microchip|chip|"
    r"nacimiento|spayed|neutered|fertil|esteril)"
)
_OWNER_LABEL_LINE = re.compile(
    r"(?im)^(?:owner|propietario|cliente|tutor)\s*[:\-]?\s+(.+?)\s*$"
)
_NOMBRE_PET_OWNER_LINE = re.compile(
    r"(?im)^\s*nombre\s+([A-Za-zÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ\-']+)\s+([A-Za-zÁÉÍÓÚÜÑ].+)$"
)


def _line_index_at(text: str, position: int) -> int:
    return text.count("\n", 0, position)


def _append_pet_name_candidate(
    candidates: list[_PetNameCandidate],
    raw: str | None,
    *,
    source: str,
    line_index: int | None = None,
) -> None:
    if not raw:
        return
    cleaned = _clean_inferred_value(raw)
    if not cleaned:
        return
    if re.search(r"(?i)propietario|owner|cliente|tutor", cleaned):
        return
    name, _ = _split_name_and_nacimiento(cleaned)
    value = (name or cleaned).strip()
    if not value:
        return
    candidates.append(
        _PetNameCandidate(name=value, source=source, line_index=line_index)
    )


def _collect_scored_pet_name_candidates(text: str) -> list[_PetNameCandidate]:
    candidates: list[_PetNameCandidate] = []
    lines = text.splitlines()[:HEADER_SCAN_LINES]

    for match in _PET_NAME_LABEL_WITH_COLON.finditer(text):
        _append_pet_name_candidate(
            candidates,
            match.group(1),
            source="colon_pet_label",
            line_index=_line_index_at(text, match.start()),
        )

    for match in _PET_NAME_NOMBRE_LABEL.finditer(text):
        _append_pet_name_candidate(
            candidates,
            match.group(1),
            source="colon_name_label",
            line_index=_line_index_at(text, match.start()),
        )

    for match in _LABELED_QUOTED_PET_NAME.finditer(text):
        _append_pet_name_candidate(
            candidates,
            match.group(1),
            source="quoted_label",
            line_index=_line_index_at(text, match.start()),
        )

    for match in _QUOTED_PET_NAME_PHRASE.finditer(text):
        _append_pet_name_candidate(
            candidates,
            match.group(1),
            source="quoted_phrase",
            line_index=_line_index_at(text, match.start()),
        )

    for match in _PET_NAME_LABEL_WORD.finditer(text):
        token = _clean_inferred_value(match.group(1))
        if token and token.lower() not in _PET_NAME_REJECT_FOLLOWING:
            _append_pet_name_candidate(
                candidates,
                token,
                source="label_word",
                line_index=_line_index_at(text, match.start()),
            )

    for line_index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if _SPECIES_BREED_LINE.match(line) or _SPECIES_BREED_SPACE_LINE.match(line):
            continue
        if _STANDALONE_SPECIES_LINE.match(line):
            continue

        standalone = _STANDALONE_CAPS_NAME_LINE.match(line)
        if standalone:
            _append_pet_name_candidate(
                candidates,
                standalone.group("name"),
                source="standalone_caps",
                line_index=line_index,
            )

        quoted_line = _STANDALONE_QUOTED_NAME_LINE.match(line)
        if quoted_line:
            _append_pet_name_candidate(
                candidates,
                quoted_line.group("name"),
                source="quoted_line",
                line_index=line_index,
            )

        title_case = _STANDALONE_TITLE_CASE_NAME_LINE.match(line)
        if title_case and _line_demographic_bonus(lines, line_index) > 0:
            _append_pet_name_candidate(
                candidates,
                title_case.group("name"),
                source="standalone_title",
                line_index=line_index,
            )

        nombre_prefix = re.match(r"(?i)^(?:nombre|name)\s+(.+)$", line)
        if nombre_prefix:
            first_token = nombre_prefix.group(1).strip().split()[0]
            _append_pet_name_candidate(
                candidates,
                first_token.strip(".,;"),
                source="nombre_prefix",
                line_index=line_index,
            )

        for token_match in _ALL_CAPS_NAME_TOKEN.finditer(line):
            _append_pet_name_candidate(
                candidates,
                token_match.group(1),
                source="caps_token",
                line_index=line_index,
            )

    return candidates


def _extract_owner_first_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in _OWNER_LABEL_LINE.finditer(text):
        value = _clean_inferred_value(match.group(1))
        if not value:
            continue
        first = value.split()[0].strip(".,;")
        if first:
            tokens.add(first.lower())
    for match in _NOMBRE_PET_OWNER_LINE.finditer(text):
        owner_rest = match.group(2)
        first = owner_rest.strip().split()[0].strip(".,;")
        if first:
            tokens.add(first.lower())
    return tokens


def _line_demographic_bonus(lines: list[str], line_index: int | None) -> int:
    if line_index is None or not (0 <= line_index < len(lines)):
        return 0
    if _DEMOGRAPHIC_CONTEXT_PATTERN.search(lines[line_index]):
        return 35
    for offset in (-1, 1):
        adjacent = line_index + offset
        if 0 <= adjacent < len(lines) and _DEMOGRAPHIC_CONTEXT_PATTERN.search(
            lines[adjacent]
        ):
            return 18
    return 0


def _pet_name_repeat_bonus(name: str, text: str) -> int:
    pattern = re.compile(
        rf"(?<![\wÁÉÍÓÚÜÑáéíóúüñ]){re.escape(name)}(?![\wÁÉÍÓÚÜÑáéíóúüñ])",
        flags=re.I,
    )
    count = len(pattern.findall(text))
    return min(max(0, count - 1) * 12, 36)


def _weak_source_owner_penalty(
    name: str,
    source: str,
    line_indices: list[int],
    lines: list[str],
    owner_tokens: set[str],
) -> int:
    if source not in _PET_NAME_WEAK_SOURCES:
        return 0
    penalty = 0
    if name.lower() in owner_tokens:
        penalty += 45
    for line_index in line_indices:
        if not (0 <= line_index < len(lines)):
            continue
        line = lines[line_index]
        if _OWNER_LABEL_LINE.match(line) and re.search(
            rf"(?i)\b{re.escape(name)}\b", line
        ):
            penalty += 55
            break
    return penalty


def _rank_pet_name_candidates(
    text: str,
    candidates: list[_PetNameCandidate],
) -> list[tuple[str, int]]:
    lines = text.splitlines()[:HEADER_SCAN_LINES]
    owner_tokens = _extract_owner_first_tokens(text)
    grouped: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        key = candidate.name.lower()
        base_score = _PET_NAME_SOURCE_SCORES[candidate.source]
        entry = grouped.get(key)
        if entry is None:
            grouped[key] = {
                "name": candidate.name,
                "best_base": base_score,
                "best_source": candidate.source,
                "line_indices": [],
            }
        else:
            if base_score > entry["best_base"]:
                entry["best_base"] = base_score
                entry["best_source"] = candidate.source
                entry["name"] = candidate.name
        if candidate.line_index is not None:
            entry = grouped[key]
            if candidate.line_index not in entry["line_indices"]:
                entry["line_indices"].append(candidate.line_index)

    ranked: list[tuple[str, int]] = []
    for entry in grouped.values():
        name = entry["name"]
        score = entry["best_base"]
        line_indices = entry["line_indices"]
        score += max(
            (_line_demographic_bonus(lines, line_index) for line_index in line_indices),
            default=0,
        )
        score += _pet_name_repeat_bonus(name, text)
        score -= _weak_source_owner_penalty(
            name,
            entry["best_source"],
            line_indices,
            lines,
            owner_tokens,
        )
        ranked.append((name, score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def validate_and_refine_pet_name(likely: dict[str, str], head: str) -> None:
    """Drop non-proper-name values and pick the best-ranked pet.name in the header."""
    ranked_best = infer_pet_name_from_text(head)
    current = likely.get("pet.name")
    if current is not None:
        validated_current = validated_pet_name(str(current))
        if validated_current:
            likely["pet.name"] = ranked_best or validated_current
            return
        likely.pop("pet.name", None)
    if ranked_best:
        likely["pet.name"] = ranked_best


def _is_plausible_pet_name_candidate(name: str) -> bool:
    candidate = name.strip()
    if not candidate or len(candidate) < 2 or len(candidate) > 30:
        return False
    lower = candidate.lower()
    if lower in _PET_NAME_SKIP_TOKENS or lower in _PET_NAME_REJECT_FOLLOWING:
        return False
    if _DATE_PATTERN.search(candidate):
        return False
    if re.fullmatch(r"\d+", candidate):
        return False
    if normalize_species_dog_cat(candidate):
        return False
    if normalize_sex_male_female(candidate):
        return False
    if re.match(r"(?i)c/\s", candidate):
        return False
    if re.search(r"(?i)propietario|owner|cliente|tutor", candidate):
        return False
    return True


def infer_pet_name_from_text(text: str) -> str | None:
    """Pick the highest-scoring validated pet name from header heuristics."""
    candidates = _collect_scored_pet_name_candidates(text)
    for name, _score in _rank_pet_name_candidates(text, candidates):
        validated = validated_pet_name(name)
        if validated:
            return validated
    return None


_BREED_LABEL_PATTERNS = (
    re.compile(r"(?i)(?:raza|breed)\s*:\s*\|?\s*([^|]+?)(?=\s*\|)"),
    re.compile(r"(?i)(?:raza|breed)\s*:\s*([^,\n|]+)"),
)


def validated_breed(value: str | None) -> str | None:
    """Return breed when structurally plausible and a known dog/cat breed."""
    if value is None or not str(value).strip():
        return None
    cleaned = _normalize_breed_value(_clean_inferred_value(str(value)) or "")
    if not cleaned or not _is_plausible_breed(cleaned):
        return None
    if not is_known_dog_or_cat_breed(cleaned):
        return None
    return cleaned


def resolve_breed(
    record_breed: str | None,
    hint_breed: str | None,
) -> str | None:
    """Prefer a validated record breed; fall back to a validated hint breed."""
    validated = validated_breed(record_breed)
    if validated:
        return validated
    return validated_breed(hint_breed)


def _add_breed_candidate(candidates: list[str], seen: set[str], raw: str | None) -> None:
    if not raw:
        return
    cleaned = _normalize_breed_value(_clean_inferred_value(raw) or "")
    key = _normalize_breed_key_for_dedup(cleaned)
    if key and key not in seen:
        seen.add(key)
        candidates.append(cleaned)


def _normalize_breed_key_for_dedup(value: str) -> str:
    return value.strip().lower()


def _collect_breed_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    for pattern in _BREED_LABEL_PATTERNS:
        for match in pattern.finditer(text):
            _add_breed_candidate(candidates, seen, match.group(1))

    for raw_line in text.splitlines()[:HEADER_SCAN_LINES]:
        line = raw_line.strip()
        if not line:
            continue
        compound = _SPECIES_BREED_LINE.match(line)
        if compound:
            _add_breed_candidate(candidates, seen, compound.group("breed"))
            continue
        space_sep = _SPECIES_BREED_SPACE_LINE.match(line)
        if space_sep:
            _add_breed_candidate(candidates, seen, space_sep.group("breed"))

    return candidates


def validate_and_refine_breed(likely: dict[str, str], head: str) -> None:
    """Drop unknown breeds and scan for a recognized dog/cat breed in the header."""
    current = likely.get("pet.breed")
    if current is not None:
        validated = validated_breed(str(current))
        if validated:
            likely["pet.breed"] = validated
        else:
            likely.pop("pet.breed", None)
    if not likely.get("pet.breed"):
        inferred = infer_pet_breed_from_text(head)
        if inferred:
            likely["pet.breed"] = inferred


def infer_pet_breed_from_text(text: str) -> str | None:
    for candidate in _collect_breed_candidates(text):
        validated = validated_breed(candidate)
        if validated:
            return validated
    return None


def infer_pet_sex_from_text(text: str) -> str | None:
    patterns = [
        r"(?i)(?:sexo|sex)\s*:\s*\|?\s*([^|\n]+?)(?=\s*\||$)",
        r"(?i)\|\s*(?:sexo|sex)\s*\|\s*([^|\n]+)",
        r"(?i)(?:sexo|sex)\s*\|\s*([^|\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = _clean_inferred_value(match.group(1))
        if value:
            return normalize_sex_male_female(value)
    return None


def infer_pet_date_of_birth_from_text(text: str) -> str | None:
    patterns = [
        r"(?i)(?:f/?nto|f\.?\s*nac(?:imiento)?|fecha\s+de\s+nacimiento|date\s+of\s+birth|dob)\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(?i)nacimiento\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    iso = re.search(r"(?i)(?:date\s+of\s+birth|dob)\s*:?\s*(\d{4}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    return None


def infer_pet_microchip_from_text(text: str) -> str | None:
    patterns = [
        r"(?i)(?:microchip|chip|n[ºo°]?\s*chip)\s*:?\s*\|?\s*(\d{9,20})",
        r"(?i)(?:microchip|chip)\D{0,12}(\d{9,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def infer_owner_name_from_text(text: str) -> str | None:
    patterns = [
        r"(?i)(?:owner|propietario|cliente|tutor)\s*:\s*([^,\n|]+)",
        r"(?i)(?:owner|propietario|cliente|tutor)\s*\|\s*([^|]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = _clean_inferred_value(match.group(1))
        if value and not re.search(r"(?i)nacimiento|microchip", value):
            return value
    return None


def infer_owner_phone_from_text(text: str) -> str | None:
    labeled = re.search(
        r"(?i)(?:tel(?:é|e)fono|telefono|phone|móvil|movil|mobile|tel)\s*:\s*([+\d][\d\s\-().]{6,})",
        text,
    )
    if labeled:
        return _clean_inferred_value(labeled.group(1))
    for match in re.finditer(r"(?<!\d)(\+\d{1,3}[-.\s]?\d[\d\s\-().]{7,})(?!\d)", text):
        candidate = _clean_inferred_value(match.group(1))
        if candidate and len(re.sub(r"\D", "", candidate)) >= 9:
            return candidate
    return None


def infer_owner_email_from_text(text: str) -> str | None:
    labeled = re.search(
        r"(?i)(?:email|e-mail|correo)\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        text,
    )
    if labeled:
        return labeled.group(1).strip()
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def infer_owner_address_from_text(text: str) -> str | None:
    labeled = re.search(
        r"(?i)(?:address|dirección|direccion|domicilio)\s*:\s*(.+?)(?:\n|$)",
        text,
    )
    if labeled:
        value = _clean_inferred_value(labeled.group(1))
        if value:
            return value
    return extract_owner_address(text)


_GLOBAL_FIELD_INFERERS: list[tuple[str, Any]] = [
    ("pet.name", infer_pet_name_from_text),
    ("pet.breed", infer_pet_breed_from_text),
    ("pet.sex", infer_pet_sex_from_text),
    ("pet.date_of_birth", infer_pet_date_of_birth_from_text),
    ("pet.microchip", infer_pet_microchip_from_text),
    ("owner.name", infer_owner_name_from_text),
    ("owner.phone", infer_owner_phone_from_text),
    ("owner.email", infer_owner_email_from_text),
    ("owner.address", infer_owner_address_from_text),
]


def apply_global_demographic_inference(hints: dict[str, Any], head: str) -> None:
    """Fill missing likely_fields via global scan (same strategy as infer_species_from_text)."""
    likely = hints.get("likely_fields") or {}
    sample = head

    for field_key, infer_fn in _GLOBAL_FIELD_INFERERS:
        current = likely.get(field_key)
        if current is not None and str(current).strip():
            if not _is_pipe_table_row_value(str(current)):
                continue
        inferred = infer_fn(sample)
        if inferred:
            likely[field_key] = inferred

    raw_species = likely.get("pet.species")
    normalized = normalize_species_dog_cat(raw_species)
    if normalized:
        likely["pet.species"] = normalized
    elif not likely.get("pet.species"):
        inferred_species = infer_species_from_text(sample)
        if inferred_species:
            likely["pet.species"] = inferred_species

    normalized_sex = normalize_sex_male_female(likely.get("pet.sex"))
    if normalized_sex:
        likely["pet.sex"] = normalized_sex

    _sanitize_compound_pet_name(likely)
    validate_and_refine_pet_name(likely, sample)
    validate_and_refine_breed(likely, sample)
    hints["likely_fields"] = likely


def normalize_species_dog_cat(value: str | None) -> str | None:
    """Map Spanish/English species labels to canonical Dog or Cat."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    lower = text.lower()
    if lower in ("dog", "d"):
        return "Dog"
    if lower in ("cat", "c"):
        return "Cat"
    if _DOG_SPECIES.search(lower):
        return "Dog"
    if _CAT_SPECIES.search(lower):
        return "Cat"
    return None


def normalize_sex_male_female(value: str | None) -> str | None:
    """Map Spanish/English sex labels to canonical Male or Female."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    core = re.sub(r"\s*\([^)]*\)", "", text).strip()
    lower = core.lower()
    if lower in ("m", "male", "macho"):
        return "Male"
    if lower in ("f", "h", "female", "hembra"):
        return "Female"
    if re.search(r"(?i)\bfemale\b|\bhembra\b", lower):
        return "Female"
    if re.search(r"(?i)\bmale\b|\bmacho\b", lower):
        return "Male"
    return None


def _is_plausible_breed(text: str) -> bool:
    """Reject address fragments and compound demographic tails mistaken as breed."""
    candidate = text.strip()
    if not candidate or len(candidate) < 2:
        return False
    if re.match(r"(?i)c/\s", candidate):
        return False
    if _DATE_PATTERN.search(candidate):
        return False
    if re.search(r"(?i)nacimiento|microchip|historial|cliente|propietario", candidate):
        return False
    return True


def _normalize_breed_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _sex_hint_from_species_token(token: str) -> str | None:
    if token.lower() in _FEMALE_SPECIES_FORMS:
        return "Female"
    return None


def extract_unlabeled_species_breed_hints(head: str) -> dict[str, str]:
    """Infer species and breed from header lines without Especie/Raza labels."""
    found: dict[str, str] = {}
    for raw_line in head.splitlines()[:HEADER_SCAN_LINES]:
        line = raw_line.strip()
        if not line:
            continue

        compound = _SPECIES_BREED_LINE.match(line)
        if compound:
            species_token = compound.group("species")
            breed_part = _normalize_breed_value(compound.group("breed"))
            species = normalize_species_dog_cat(species_token)
            if species:
                found.setdefault("pet.species", species)
            if _is_plausible_breed(breed_part):
                validated = validated_breed(breed_part)
                if validated:
                    found.setdefault("pet.breed", validated)
            sex_hint = _sex_hint_from_species_token(species_token)
            if sex_hint:
                found.setdefault("pet.sex", sex_hint)
            continue

        space_sep = _SPECIES_BREED_SPACE_LINE.match(line)
        if space_sep:
            species_token = space_sep.group("species")
            breed_part = _normalize_breed_value(space_sep.group("breed"))
            species = normalize_species_dog_cat(species_token)
            if species and _is_plausible_breed(breed_part):
                validated = validated_breed(breed_part)
                if validated:
                    found.setdefault("pet.species", species)
                    found.setdefault("pet.breed", validated)
                sex_hint = _sex_hint_from_species_token(species_token)
                if sex_hint:
                    found.setdefault("pet.sex", sex_hint)
            continue

        standalone = _STANDALONE_SPECIES_LINE.match(line)
        if standalone:
            species_token = standalone.group("species")
            species = normalize_species_dog_cat(species_token)
            if species:
                found.setdefault("pet.species", species)
            sex_hint = _sex_hint_from_species_token(species_token)
            if sex_hint:
                found.setdefault("pet.sex", sex_hint)

    return found


def infer_species_from_text(text: str) -> str | None:
    """Infer Dog vs Cat from header sample when species field is missing or ambiguous."""
    sample = text[:_INFERENCE_SAMPLE_CHARS]
    labeled = re.search(
        r"(?i)(?:especie|species)\s*:?\s*(canino|canina|felino|felina|perro|gato|dog|cat|canine|feline)",
        sample,
    )
    if labeled:
        return normalize_species_dog_cat(labeled.group(1))

    dog = bool(_DOG_SPECIES.search(sample))
    cat = bool(_CAT_SPECIES.search(sample))
    if dog and not cat:
        return "Dog"
    if cat and not dog:
        return "Cat"
    return None


def apply_species_normalization(hints: dict[str, Any], head: str) -> None:
    """Normalize species and run global inference for all demographic fields."""
    apply_global_demographic_inference(hints, head)


def normalize_extracted_text(text: str) -> str:
    """Normalize whitespace while preserving line breaks useful for visit dates."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language_hint(text: str) -> str | None:
    sample = text[:4000].lower()
    spanish_markers = [
        "mascota",
        "especie",
        "historial",
        "exploracion",
        "exploración",
        "tratamiento",
        "canino",
        "felino",
        "heces",
        "vacuna",
    ]
    english_markers = [
        "patient",
        "owner",
        "diagnosis",
        "treatment",
        "examination",
        "canine",
        "feline",
        "vaccination",
    ]
    es = sum(1 for m in spanish_markers if m in sample)
    en = sum(1 for m in english_markers if m in sample)
    if es == 0 and en == 0:
        return None
    return "es" if es >= en else "en"


def extract_visit_dates(text: str) -> list[str]:
    patterns = [
        r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1)
            if value not in found:
                found.append(value)
    return found


def extract_visit_blocks(text: str, max_entries: int = 12) -> list[dict[str, str]]:
    """Split multi-visit histories into dated blocks and keep concise summaries."""
    matches = list(_VISIT_HEADER.finditer(text))
    if not matches:
        return []

    blocks: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = re.sub(r"\s+", " ", text[start:end]).strip()
        if not body:
            continue
        summary = body[:280] + ("…" if len(body) > 280 else "")
        blocks.append({"date": match.group(1), "summary": summary})

    if len(blocks) <= max_entries:
        return blocks
    # Keep earliest context + most recent visits.
    head_n = min(3, max_entries // 3)
    return blocks[:head_n] + blocks[-(max_entries - head_n) :]


def extract_diagnosis_hints(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for pattern, label in _DIAGNOSIS_KEYWORDS:
        if re.search(pattern, lower, flags=re.I) and label not in found:
            found.append(label)
    return found


def extract_medication_hints(text: str) -> list[dict[str, str | None]]:
    found: list[dict[str, str | None]] = []
    lower = text.lower()
    for name in _MEDICATION_NAMES:
        if name.lower() in lower:
            found.append({"name": name, "dosage": None, "frequency": None})
    return found[:8]


def extract_clinic_name(text: str) -> str | None:
    head = "\n".join(text.splitlines()[:12])
    if re.search(r"parque\s+oeste", head, flags=re.I):
        return "Parque Oeste"
    if re.search(r"\bkivet\b", text, flags=re.I):
        return "Kivet"
    first = next((ln.strip() for ln in head.splitlines() if ln.strip()), "")
    if first and len(first) <= 40 and not re.search(r"\d{4,}", first):
        return first.title() if first.isupper() else first
    return None


def extract_owner_address(text: str) -> str | None:
    head = "\n".join(text.splitlines()[:40])
    parts: list[str] = []
    street = re.search(
        r"(?im)^especie\s+\S+\s+(C/\s?.+)$",
        head,
    )
    if street:
        parts.append(street.group(1).strip())
    city = re.search(
        r"(?im)^raza\s+.+\s+([A-ZÁÉÍÓÚÜÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÜÑ]{3,})?)\s*$",
        head,
    )
    # Prefer explicit town after breed on same messy line.
    town = re.search(r"(?im)^raza\s+.+?\s+(BOADILLA|MADRID|ALCORC[OÓ]N)\b", head)
    postal = re.search(
        r"(?im)^(?:f/?nto|f\.?\s*nac(?:imiento)?)\s+\d{1,2}/\d{1,2}/\d{2,4}\s+(\d{5}\s+[A-ZÁÉÍÓÚÜÑ ]+)",
        head,
    )
    if town:
        parts.append(town.group(1).title())
    if postal:
        parts.append(postal.group(1).strip().title())
    if not parts and city:
        parts.append(city.group(1).title())
    return ", ".join(dict.fromkeys(parts)) if parts else None


def _normalize_inline_label(label: str) -> str:
    text = re.sub(r"\s+", " ", label.strip().lower())
    compact = re.sub(r"\s+", "", text)
    if compact in _INLINE_LABEL_TO_FIELD:
        return compact
    if text in _INLINE_LABEL_TO_FIELD:
        return text
    return compact


def _normalize_inline_value(field: str, raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if field == "pet.date_of_birth":
        date_match = _DATE_PATTERN.search(value)
        return date_match.group(0) if date_match else None
    if field == "pet.microchip":
        chip_match = re.search(r"\d{9,20}", value)
        return chip_match.group(0) if chip_match else None
    return value


def _split_name_and_nacimiento(text: str) -> tuple[str | None, str | None]:
    """Split 'ALYA - Nacimiento: 05/07/2018' into name and date of birth."""
    value = text.strip()
    if not value:
        return None, None
    compound = re.match(
        r"^(.+?)\s*[-–—]\s*nacimiento:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*$",
        value,
        flags=re.I,
    )
    if compound:
        return compound.group(1).strip(), compound.group(2).strip()
    return value, None


def _apply_pet_name_hint(likely: dict[str, str], raw_name: str) -> None:
    name, dob = _split_name_and_nacimiento(raw_name)
    validated = validated_pet_name(name or raw_name)
    if validated:
        likely["pet.name"] = validated
    if dob:
        likely.setdefault("pet.date_of_birth", dob)


def _sanitize_compound_pet_name(likely: dict[str, str]) -> None:
    raw_name = likely.get("pet.name")
    if not raw_name or not re.search(r"nacimiento\s*:", raw_name, flags=re.I):
        return
    name, dob = _split_name_and_nacimiento(raw_name)
    validated = validated_pet_name(name or raw_name)
    if validated:
        likely["pet.name"] = validated
    elif "pet.name" in likely:
        likely.pop("pet.name", None)
    if dob:
        likely["pet.date_of_birth"] = dob


def extract_inline_demographic_hints(head: str) -> dict[str, str]:
    """Parse multi-field and inline Label: value lines common in clinic PDF headers."""
    found: dict[str, str] = {}
    lines = head.splitlines()[:HEADER_SCAN_LINES]

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        name_dob = _NAME_NACIMIENTO_LINE.match(line)
        if name_dob:
            validated_name = validated_pet_name(name_dob.group(1).strip())
            if validated_name:
                found.setdefault("pet.name", validated_name)
            found.setdefault("pet.date_of_birth", name_dob.group(2).strip())
            continue

        sex_estado_peso = _HEMBRA_ESTADO_PESO_LINE.match(line)
        if sex_estado_peso:
            found.setdefault("pet.sex", sex_estado_peso.group(1).strip())
            continue

        standalone_sex = _STANDALONE_SEX_LINE.match(line)
        if standalone_sex and "pet.sex" not in found:
            found["pet.sex"] = standalone_sex.group(1).strip()

        for match in _INLINE_LABEL_VALUE.finditer(line):
            label = _normalize_inline_label(match.group(1))
            field = _INLINE_LABEL_TO_FIELD.get(label)
            if not field or field in found:
                continue
            normalized = _normalize_inline_value(field, match.group(2))
            if normalized:
                found[field] = normalized

    return found


def build_layout_hints(text: str) -> dict[str, Any]:
    """Produce non-authoritative hints from common ES/EN clinic header labels."""
    head = _header_sample(text)
    hints: dict[str, Any] = {
        "language_hint": detect_language_hint(text),
        "visit_dates_found": extract_visit_dates(text)[:20],
        "visit_blocks": extract_visit_blocks(text),
        "diagnosis_hints": extract_diagnosis_hints(text),
        "medication_hints": extract_medication_hints(text),
        "likely_fields": {},
    }

    joined = "\n".join(ln.strip() for ln in head.splitlines() if ln.strip())

    chip = re.search(r"(?:chip|microchip)\D{0,12}(\d{9,20})", joined, flags=re.I)
    if chip:
        hints["likely_fields"]["pet.microchip"] = chip.group(1)

    clinic = extract_clinic_name(text)
    if clinic:
        hints["likely_fields"]["visit.clinic_name"] = clinic

    address = extract_owner_address(text)
    if address:
        hints["likely_fields"]["owner.address"] = address

    nombre_line = re.search(
        r"(?im)^\s*nombre\s+([A-Za-zÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ\-']+)\s+([A-Za-zÁÉÍÓÚÜÑ].+)$",
        head,
    )
    if nombre_line:
        pet_name = validated_pet_name(nombre_line.group(1).strip())
        if pet_name:
            hints["likely_fields"]["pet.name"] = pet_name
        hints["likely_fields"]["owner.name"] = nombre_line.group(2).strip()

    for raw_line in head.splitlines():
        nombre_prefixed = _NOMBRE_PREFIX_LINE.match(raw_line.strip())
        if not nombre_prefixed:
            continue
        rest = nombre_prefixed.group(1).strip()
        if re.search(r"nacimiento\s*:", rest, flags=re.I):
            _apply_pet_name_hint(hints["likely_fields"], rest)
            break

    especie = re.search(
        r"(?im)^especie\s+(canino|felino|gato|perro|ave|reptil|canine|feline|dog|cat)\b",
        head,
    )
    if especie:
        hints["likely_fields"]["pet.species"] = especie.group(1)

    raza = re.search(
        r"(?im)^raza\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-]+?)(?:\s{2,}|\s+[A-ZÁÉÍÓÚÜÑ]{3,}|\s+\d|$)",
        head,
    )
    if raza:
        validated = validated_breed(raza.group(1).strip())
        if validated:
            hints["likely_fields"]["pet.breed"] = validated

    sexo = re.search(r"(?im)^sexo\s+([MHFAmfha]|Macho|Hembra|Male|Female)\b", head)
    if sexo:
        hints["likely_fields"]["pet.sex"] = sexo.group(1)

    dob = re.search(
        r"(?im)^(?:f/?nto|f\.?\s*nac(?:imiento)?)\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        head,
    )
    if dob:
        hints["likely_fields"]["pet.date_of_birth"] = dob.group(1)

    key_to_target = {
        "name": "pet.name",
        "species": "pet.species",
        "breed": "pet.breed",
        "sex": "pet.sex",
        "dob": "pet.date_of_birth",
        "microchip": "pet.microchip",
        "owner": "owner.name",
    }
    for key, labels in _LABEL_HINTS.items():
        target = key_to_target[key]
        if target in hints["likely_fields"]:
            continue
        label = "|".join(labels)
        match = re.search(rf"(?im)^(?:{label})\s*[:\-]?\s+(.+?)\s*$", head)
        if match:
            value = match.group(1).strip()
            if _is_pipe_table_row_value(value):
                continue
            if target == "pet.name":
                _apply_pet_name_hint(hints["likely_fields"], value)
            elif target == "pet.breed":
                validated = validated_breed(value)
                if validated:
                    hints["likely_fields"][target] = validated
            else:
                hints["likely_fields"][target] = value

    inline = extract_inline_demographic_hints(head)
    for key, value in inline.items():
        hints["likely_fields"][key] = value

    for key, value in extract_unlabeled_species_breed_hints(head).items():
        hints["likely_fields"].setdefault(key, value)

    _sanitize_compound_pet_name(hints["likely_fields"])

    apply_species_normalization(hints, head)
    validate_and_refine_pet_name(hints["likely_fields"], head)
    validate_and_refine_breed(hints["likely_fields"], head)

    return hints


def split_for_long_document(text: str, max_chars: int = 28000) -> tuple[str, str]:
    """Return (header_chunk, body_chunk) for long multi-visit PDFs."""
    if len(text) <= max_chars:
        return text, text

    header = text[:3500]
    tail = text[-(max_chars - len(header) - 200) :]
    body = (
        header
        + "\n\n[... middle of document omitted for length ...]\n\n"
        + tail
    )
    return header, body


def clinical_focus_text(text: str, max_chars: int = 12000) -> str:
    """Prefer the visit chronology for the clinical LLM pass."""
    match = re.search(r"(?is)historial.*", text)
    chunk = match.group(0) if match else text
    if len(chunk) <= max_chars:
        return chunk
    return chunk[:2000] + "\n\n[...]\n\n" + chunk[-(max_chars - 2200) :]
