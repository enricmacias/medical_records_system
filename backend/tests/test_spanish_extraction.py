"""Tests for Spanish multi-visit extraction helpers and FakeLLM."""

from app.adapters.llm import FakeLLMStructurer
from app.adapters.text_hints import (
    build_layout_hints,
    detect_language_hint,
    extract_visit_blocks,
)
from tests.test_inline_demographics import (
    INLINE_ALYA_DOC,
    INLINE_HEMBRA_DOC,
    INLINE_NOMBRE_DOC,
)


SPANISH_HEADER = """
PARQUE OESTE
AVDA EUROPA
28922 ALCORCÓN
Datos de la Mascota Datos del Cliente
Nombre MARLEY BEATRIZ ABARCA
Especie Canino C/ ORTEGA Y GASSET 1 PORTAL 3 1F
Raza Labrador Retriever BOADILLA
F/Nto 04/10/19 28660 MADRID
Capa
Nº Chip 941000024967769
Sexo M
HISTORIAL COMPLETO DE MARLEY DESDE LA PRIMERA VISITA A NUESTRO CENTRO
- 08/12/19 - 16:12 -
Vienen de urgencias porque tiene una costrita.
- 08/04/20 - 19:37
test giardia positivo
- 03/10/20 - 18:05 -
Conjuntiva inflamada. Test de giardia: positivo!!
Peso 29.6kg
Tobradex y Fortiflora.
"""


def test_detects_spanish_language() -> None:
    assert detect_language_hint(SPANISH_HEADER) == "es"


def test_layout_hints_from_spanish_header() -> None:
    hints = build_layout_hints(SPANISH_HEADER)
    likely = hints["likely_fields"]
    assert likely.get("pet.name") == "MARLEY"
    assert "BEATRIZ" in (likely.get("owner.name") or "")
    assert likely.get("pet.species") == "Dog"
    assert "Labrador" in (likely.get("pet.breed") or "")
    assert likely.get("pet.microchip") == "941000024967769"
    assert likely.get("pet.date_of_birth") == "04/10/19"
    assert likely.get("visit.clinic_name") == "Parque Oeste"
    assert hints["language_hint"] == "es"
    assert "Giardiasis" in hints["diagnosis_hints"]
    assert hints["visit_blocks"]


def test_extract_visit_blocks() -> None:
    blocks = extract_visit_blocks(SPANISH_HEADER)
    assert len(blocks) >= 3
    assert blocks[0]["date"] == "08/12/19"
    assert "costrita" in blocks[0]["summary"].lower()


def test_fake_llm_structures_spanish_historial() -> None:
    record = FakeLLMStructurer().structure(SPANISH_HEADER)
    assert record.meta.source_language == "es"
    assert record.pet.name == "MARLEY"
    assert record.owner.name and "BEATRIZ" in record.owner.name
    assert record.pet.microchip == "941000024967769"
    assert record.pet.species == "Dog"
    assert record.clinical.history_entries
    assert record.clinical.diagnosis
    assert record.clinical.medications
    assert record.visit.clinic_name == "Parque Oeste"


def test_ollama_hybrid_skips_llm_when_historial_hints_exist() -> None:
    """Multi-visit Spanish PDFs should complete without calling Ollama."""
    from app.adapters.llm import OllamaStructurer

    structurer = OllamaStructurer(
        base_url="http://127.0.0.1:9",  # unreachable on purpose
        model="qwen2.5:7b",
        timeout_seconds=1,
        clinical_mode="hybrid",
        skip_demographics_when_hinted=True,
    )
    record = structurer.structure(SPANISH_HEADER)
    assert record.pet.name == "MARLEY"
    assert record.meta.source_language == "es"
    assert record.clinical.history_entries
    assert record.clinical.diagnosis


def test_inline_compound_lines_in_layout_hints() -> None:
    """Integration check: compound header lines map to separate pet fields."""
    aliya = build_layout_hints(INLINE_ALYA_DOC)["likely_fields"]
    assert aliya["pet.name"] == "ALYA"
    assert aliya["pet.date_of_birth"] == "05/07/2018"

    nombre = build_layout_hints(INLINE_NOMBRE_DOC)["likely_fields"]
    assert nombre["pet.name"] == "ALYA"
    assert nombre["pet.date_of_birth"] == "05/07/2018"

    hembra = build_layout_hints(INLINE_HEMBRA_DOC)["likely_fields"]
    assert hembra["pet.sex"] == "Hembra"


def test_fake_llm_structures_inline_compound_headers() -> None:
    aliya = FakeLLMStructurer().structure(INLINE_ALYA_DOC)
    assert aliya.pet.name == "ALYA"
    assert aliya.pet.date_of_birth == "05/07/2018"

    hembra = FakeLLMStructurer().structure(INLINE_HEMBRA_DOC)
    assert hembra.pet.sex == "Hembra"


