"""Lightweight heuristics to help the LLM with messy clinic PDF layouts."""

from __future__ import annotations

import re
from typing import Any


_LABEL_HINTS = {
    "name": [r"nombre", r"name", r"paciente", r"mascota"],
    "species": [r"especie", r"species"],
    "breed": [r"raza", r"breed"],
    "sex": [r"sexo", r"sex", r"g[eé]nero"],
    "dob": [r"f/?nto", r"f\.?\s*nac", r"fecha\s+de\s+nacimiento", r"date\s+of\s+birth", r"dob"],
    "microchip": [r"n[ºo°]?\s*chip", r"microchip", r"chip"],
    "coat": [r"capa", r"coat", r"color"],
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


def build_layout_hints(text: str) -> dict[str, Any]:
    """Produce non-authoritative hints from common ES/EN clinic header labels."""
    head = "\n".join(text.splitlines()[:80])
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

    weights = re.findall(
        r"(?:peso|pv|weight)?\s*[:=]?\s*(\d{1,2}(?:[.,]\d{1,2})?\s*kg)",
        text,
        flags=re.I,
    )
    if weights:
        hints["likely_fields"]["pet.weight"] = weights[-1].replace(",", ".")

    clinic = extract_clinic_name(text)
    if clinic:
        hints["likely_fields"]["visit.clinic_name"] = clinic

    address = extract_owner_address(text)
    if address:
        hints["likely_fields"]["owner.address"] = address

    nombre_line = re.search(
        r"(?im)^nombre\s+([A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ\-']+)\s+([A-ZÁÉÍÓÚÜÑ].+)$",
        head,
    )
    if nombre_line:
        hints["likely_fields"]["pet.name"] = nombre_line.group(1).strip()
        hints["likely_fields"]["owner.name"] = nombre_line.group(2).strip()

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
        hints["likely_fields"]["pet.breed"] = raza.group(1).strip()

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
        "coat": "pet.coat_color",
        "owner": "owner.name",
    }
    for key, labels in _LABEL_HINTS.items():
        target = key_to_target[key]
        if target in hints["likely_fields"]:
            continue
        label = "|".join(labels)
        match = re.search(rf"(?im)^(?:{label})\s*[:\-]?\s+(.+?)\s*$", head)
        if match:
            hints["likely_fields"][target] = match.group(1).strip()

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
