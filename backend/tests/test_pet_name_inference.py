"""Tests for ranked pet-name inference and format heuristics in text_hints."""

from app.adapters.llm import FakeLLMStructurer
from app.adapters.text_hints import (
    build_layout_hints,
    infer_pet_name_from_text,
    validated_pet_name,
)


class TestPetNameRanking:
    """Candidate scoring (idea C): pick best source, not first valid match."""

    def test_prefers_colon_pet_label_over_earlier_caps_token(self) -> None:
        text = """
        CLINICA VETERINARIA MARLEY
        Canino - Labrador
        Pet: LUNA
        Historial
        """
        assert infer_pet_name_from_text(text) == "LUNA"

    def test_prefers_nombre_prefix_over_standalone_caps(self) -> None:
        text = """
        VETERINARIA CENTRAL
        TOBY
        Species: Canine
        Nombre MARLEY
        Historial
        """
        assert infer_pet_name_from_text(text) == "MARLEY"

    def test_deprioritizes_owner_first_token_for_weak_caps_match(self) -> None:
        text = """
        Owner: MARLEY Smith
        LUNA
        Canino - Labrador
        Historial
        """
        assert infer_pet_name_from_text(text) == "LUNA"

    def test_boosts_repeated_name_mentions(self) -> None:
        text = """
        VETERINARIA CENTRAL
        TOBY
        Consulta de TOBY
        Pet: MARLEY
        Historial
        MARLEY acude por revisión.
        """
        assert infer_pet_name_from_text(text) == "MARLEY"

    def test_quoted_label_beats_standalone_quoted_line(self) -> None:
        text = '"Max"\nPet: "Buddy"\nHistorial'
        assert infer_pet_name_from_text(text) == "Buddy"


class TestPetNameFormatHeuristics:
    """Case and format detection (idea D)."""

    def test_title_case_line_near_demographics(self) -> None:
        text = """
        Clinica Veterinaria
        Species: Canine
        Luna
        Breed: Labrador
        Historial
        """
        assert infer_pet_name_from_text(text) == "Luna"

    def test_ignores_title_case_line_without_demographic_context(self) -> None:
        text = "Clinica Central\nLuna\nHistorial clinico"
        assert infer_pet_name_from_text(text) is None

    def test_mixed_case_colon_labels(self) -> None:
        assert infer_pet_name_from_text("Name: Luna\nHistorial") == "Luna"
        assert infer_pet_name_from_text("Pet: Buddy\nSpecies: Dog") == "Buddy"

    def test_mixed_case_nombre_prefix(self) -> None:
        assert infer_pet_name_from_text("Nombre Luna\nHistorial") == "Luna"
        assert infer_pet_name_from_text("Name Max\nHistory") == "Max"

    def test_quoted_label_colon_and_phrase(self) -> None:
        assert infer_pet_name_from_text('Pet: "Whiskers"\nHistorial') == "Whiskers"
        assert infer_pet_name_from_text('Nombre: "Luna"\nHistorial') == "Luna"
        assert infer_pet_name_from_text("Se llama 'Luna'\nFelino - Persa") == "Luna"
        assert infer_pet_name_from_text('Known as "Max"\nCanino - Labrador') == "Max"

    def test_standalone_quoted_line_near_demographics(self) -> None:
        text = '"Max"\nCanino - Labrador\nHistorial'
        assert infer_pet_name_from_text(text) == "Max"


class TestPetNameValidationAndLayout:
    """Validation gates and build_layout_hints integration."""

    def test_rejects_non_proper_name_words(self) -> None:
        assert validated_pet_name("Summary") is None
        assert validated_pet_name("Grammar") is None
        assert validated_pet_name("punctuation") is None
        assert validated_pet_name("Resumen") is None

    def test_skips_invalid_label_value_and_finds_next_candidate(self) -> None:
        assert infer_pet_name_from_text("Nombre Summary\nMARLEY") == "MARLEY"
        assert infer_pet_name_from_text("Pet Grammar\nLUNA") == "LUNA"
        assert infer_pet_name_from_text("Paciente Informe\nTOBY") == "TOBY"

    def test_label_without_colon(self) -> None:
        assert infer_pet_name_from_text("Patient Max\nHistorial") == "Max"
        assert infer_pet_name_from_text("Paciente MARLEY\nHistorial") == "MARLEY"
        assert infer_pet_name_from_text("Pet Buddy species cat") == "Buddy"
        assert infer_pet_name_from_text("Mascota LUNA\nConsulta") == "LUNA"

    def test_rejects_label_followed_by_non_name(self) -> None:
        assert infer_pet_name_from_text("Patient record\nMARLEY") == "MARLEY"
        assert infer_pet_name_from_text("Datos del paciente\nTOBY") == "TOBY"

    def test_standalone_caps_line(self) -> None:
        text = """
        CLINICA VETERINARIA
        MARLEY
        Canino - Labrador
        Historial
        """
        assert infer_pet_name_from_text(text) == "MARLEY"

    def test_caps_on_nombre_line(self) -> None:
        assert infer_pet_name_from_text("Nombre LUNA\nHistorial") == "LUNA"
        assert infer_pet_name_from_text("Name WHISKERS\nHistory") == "WHISKERS"

    def test_build_layout_drops_invalid_pet_name_and_finds_next(self) -> None:
        text = """
        Veterinaria Central
        Nombre Summary
        MARLEY
        Canino - Labrador
        Historial
        """
        likely = build_layout_hints(text)["likely_fields"]
        assert likely.get("pet.name") == "MARLEY"

    def test_build_layout_splits_mixed_case_nombre_owner_line(self) -> None:
        text = """
        Clinica Central
        Nombre Luna Beatriz Abarca
        Felino - Persa
        Historial
        """
        likely = build_layout_hints(text)["likely_fields"]
        assert likely.get("pet.name") == "Luna"
        assert likely.get("owner.name") == "Beatriz Abarca"

    def test_build_layout_title_case_pet_name_end_to_end(self) -> None:
        text = """
        Clinica Veterinaria
        Species: Canine
        Luna
        Breed: Labrador Retriever
        Sex: Female
        Historial
        """
        likely = build_layout_hints(text)["likely_fields"]
        assert likely.get("pet.name") == "Luna"
        assert likely.get("pet.species") == "Dog"
        assert likely.get("pet.breed") == "Labrador Retriever"

    def test_fake_llm_uses_title_case_pet_name_from_hints(self) -> None:
        text = """
        Clinica Veterinaria
        Species: Canine
        Luna
        Breed: Labrador Retriever
        Sex: Female
        Historial
        Consulta rutina.
        """
        record = FakeLLMStructurer().structure(text)
        assert record.pet.name == "Luna"
        assert record.pet.species == "Dog"
        assert record.pet.breed == "Labrador Retriever"
