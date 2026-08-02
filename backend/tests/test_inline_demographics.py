"""Unit tests for inline compound demographic parsing in text_hints."""

from app.adapters.llm import FakeLLMStructurer, OllamaStructurer
from app.adapters.text_hints import (
    _apply_pet_name_hint,
    _sanitize_compound_pet_name,
    _split_name_and_nacimiento,
    build_layout_hints,
    extract_inline_demographic_hints,
)

COMPOUND_DASH = "ALYA - Nacimiento: 05/07/2018"
COMPOUND_NOMBRE_LINE = "Nombre ALYA - Nacimiento: 05/07/2018"
COMPOUND_MIXED_CASE = "Alya - Nacimiento: 05/07/2018"
COMPOUND_ENGLISH_NAME_LABEL = "Name Alya - Nacimiento: 05/07/2018"

INLINE_ALYA_DOC = f"""
CLINICA VETERINARIA
{COMPOUND_DASH}
Historial de visitas
- 01/02/20 - 10:00 -
Consulta rutina.
"""

INLINE_NOMBRE_DOC = f"""
Datos del paciente
{COMPOUND_NOMBRE_LINE}
Historial
- 01/02/20 - 10:00 -
Consulta rutina.
"""

INLINE_HEMBRA_DOC = """
Hembra Estado: FERTIL Peso:0
Historial
- 01/02/20 - 10:00 -
Revision general.
"""

INLINE_MIXED_CASE_DOC = f"""
Paciente
{COMPOUND_MIXED_CASE}
Historial
- 01/02/20 - 10:00 -
Consulta rutina.
"""

INLINE_ENGLISH_NAME_DOC = f"""
Patient record
{COMPOUND_ENGLISH_NAME_LABEL}
History
- 01/02/20 - 10:00 -
Routine check.
"""

class TestSplitNameAndNacimiento:
    def test_splits_dash_nacimiento_pattern(self) -> None:
        name, dob = _split_name_and_nacimiento(COMPOUND_DASH)
        assert name == "ALYA"
        assert dob == "05/07/2018"

    def test_splits_mixed_case_name(self) -> None:
        name, dob = _split_name_and_nacimiento(COMPOUND_MIXED_CASE)
        assert name == "Alya"
        assert dob == "05/07/2018"

    def test_returns_plain_name_when_no_nacimiento_suffix(self) -> None:
        name, dob = _split_name_and_nacimiento("MARLEY")
        assert name == "MARLEY"
        assert dob is None

    def test_handles_empty_string(self) -> None:
        name, dob = _split_name_and_nacimiento("")
        assert name is None
        assert dob is None


class TestApplyPetNameHint:
    def test_splits_compound_value_into_name_and_dob(self) -> None:
        likely: dict[str, str] = {}
        _apply_pet_name_hint(likely, COMPOUND_DASH)
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"

    def test_does_not_overwrite_existing_dob(self) -> None:
        likely = {"pet.date_of_birth": "01/01/20"}
        _apply_pet_name_hint(likely, COMPOUND_DASH)
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "01/01/20"


class TestSanitizeCompoundPetName:
    def test_repairs_compound_name_embedded_in_pet_name(self) -> None:
        likely = {
            "pet.name": COMPOUND_DASH,
            "pet.date_of_birth": "",
        }
        _sanitize_compound_pet_name(likely)
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"

    def test_no_op_when_name_is_already_clean(self) -> None:
        likely = {"pet.name": "ALYA", "pet.date_of_birth": "05/07/2018"}
        _sanitize_compound_pet_name(likely)
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"


class TestExtractInlineDemographicHints:
    def test_inline_dash_nacimiento_line(self) -> None:
        hints = extract_inline_demographic_hints(INLINE_ALYA_DOC)
        assert hints["pet.name"] == "ALYA"
        assert hints["pet.date_of_birth"] == "05/07/2018"

    def test_inline_mixed_case_dash_nacimiento(self) -> None:
        hints = extract_inline_demographic_hints(INLINE_MIXED_CASE_DOC)
        assert hints["pet.name"] == "Alya"
        assert hints["pet.date_of_birth"] == "05/07/2018"


class TestBuildLayoutHintsCompoundLines:
    def test_dash_nacimiento_line(self) -> None:
        likely = build_layout_hints(INLINE_ALYA_DOC)["likely_fields"]
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"
        assert "Nacimiento" not in likely["pet.name"]

    def test_nombre_prefix_compound_line(self) -> None:
        likely = build_layout_hints(INLINE_NOMBRE_DOC)["likely_fields"]
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"
        assert "Nacimiento" not in likely["pet.name"]

    def test_english_name_label_compound_line(self) -> None:
        likely = build_layout_hints(INLINE_ENGLISH_NAME_DOC)["likely_fields"]
        assert likely["pet.name"] == "Alya"
        assert likely["pet.date_of_birth"] == "05/07/2018"

    def test_inline_hints_override_wrong_compound_name_from_generic_parser(self) -> None:
        """Simulate generic 'Nombre' capturing the full line, then layout repair."""
        likely: dict[str, str] = {"pet.name": COMPOUND_DASH}
        _sanitize_compound_pet_name(likely)
        inline = extract_inline_demographic_hints(INLINE_ALYA_DOC)
        for key, value in inline.items():
            likely[key] = value
        _sanitize_compound_pet_name(likely)
        assert likely["pet.name"] == "ALYA"
        assert likely["pet.date_of_birth"] == "05/07/2018"


class TestStructurerCompoundDemographics:
    def test_fake_llm_splits_compound_nombre_line(self) -> None:
        record = FakeLLMStructurer().structure(INLINE_NOMBRE_DOC)
        assert record.pet.name == "ALYA"
        assert record.pet.date_of_birth == "05/07/2018"
        assert "Nacimiento" not in (record.pet.name or "")

    def test_ollama_heuristic_path_splits_compound_nombre_line(self) -> None:
        structurer = OllamaStructurer(
            base_url="http://127.0.0.1:9",
            model="qwen2.5:7b",
            timeout_seconds=1,
            clinical_mode="hybrid",
            skip_demographics_when_hinted=True,
        )
        record = structurer.structure(INLINE_NOMBRE_DOC)
        assert record.pet.name == "ALYA"
        assert record.pet.date_of_birth == "05/07/2018"
        assert "Nacimiento" not in (record.pet.name or "")
