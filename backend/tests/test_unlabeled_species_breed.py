"""Tests for label-free species and breed inference in text_hints."""

from app.adapters.llm import FakeLLMStructurer, OllamaStructurer
from app.adapters.text_hints import (
    build_layout_hints,
    extract_unlabeled_species_breed_hints,
    infer_species_from_text,
    normalize_species_dog_cat,
    normalize_sex_male_female,
)

UNLABELED_CANINA_BREED_DOC = """
CLINICA VETERINARIA
CANINA - YORKSHIRE TERRIER
Nombre LUNA
Historial
- 01/02/20 - 10:00 -
Consulta rutina.
"""

STANDALONE_CANINO_DOC = """
Datos del paciente
Canino
Nombre TOBY
Historial
- 01/02/20 - 10:00 -
Consulta rutina.
"""

STANDALONE_CAT_DOC = """
Patient record
Cat
Name WHISKERS
History
- 01/02/20 - 10:00 -
Routine check.
"""

FELINA_BREED_SPACE_DOC = """
Veterinaria Central
Felina Persa
Nombre MIA
Historial
- 01/02/20 - 10:00 -
Revision.
"""

LABELLED_OVERRIDES_UNLABELED_DOC = """
Datos de la Mascota
Especie Felino
Canino
Raza Persa
Nombre NINA
Historial
- 01/02/20 - 10:00 -
Consulta.
"""

ADDRESS_BREED_REJECTION_DOC = """
CLINICA
Canino - C/ ORTEGA Y GASSET 1
Nombre MARLEY
Historial
- 01/02/20 - 10:00 -
Consulta.
"""


class TestNormalizeSpeciesDogCat:
    def test_maps_spanish_and_english_tokens(self) -> None:
        assert normalize_species_dog_cat("Canino") == "Dog"
        assert normalize_species_dog_cat("CANINA") == "Dog"
        assert normalize_species_dog_cat("Felino") == "Cat"
        assert normalize_species_dog_cat("Felina") == "Cat"
        assert normalize_species_dog_cat("Gato") == "Cat"
        assert normalize_species_dog_cat("Dog") == "Dog"
        assert normalize_species_dog_cat("Cat") == "Cat"

    def test_returns_none_for_empty_or_unknown(self) -> None:
        assert normalize_species_dog_cat(None) is None
        assert normalize_species_dog_cat("") is None
        assert normalize_species_dog_cat("Ave") is None


class TestNormalizeSexMaleFemale:
    def test_maps_spanish_and_english_tokens(self) -> None:
        assert normalize_sex_male_female("M") == "Male"
        assert normalize_sex_male_female("Macho") == "Male"
        assert normalize_sex_male_female("H") == "Female"
        assert normalize_sex_male_female("Hembra") == "Female"
        assert normalize_sex_male_female("Female (Spayed)") == "Female"
        assert normalize_sex_male_female("Male") == "Male"
        assert normalize_sex_male_female("Female") == "Female"

    def test_returns_none_for_empty_or_unknown(self) -> None:
        assert normalize_sex_male_female(None) is None
        assert normalize_sex_male_female("") is None
        assert normalize_sex_male_female("Unknown") is None


class TestInferSpeciesFromText:
    def test_infers_from_unlabeled_body_keywords(self) -> None:
        assert infer_species_from_text("Paciente canino labrador historial") == "Dog"
        assert infer_species_from_text("Paciente felino persa historial") == "Cat"
        assert infer_species_from_text("CANINA - YORKSHIRE TERRIER") == "Dog"

    def test_prefers_labeled_especie_over_body_noise(self) -> None:
        text = "Especie Felino\nHistorial canino labrador"
        assert infer_species_from_text(text) == "Cat"

    def test_returns_none_when_both_species_keywords_present(self) -> None:
        text = "Historial canino y felino en la misma clinica"
        assert infer_species_from_text(text) is None


class TestExtractUnlabeledSpeciesBreedHints:
    def test_canina_dash_breed_line(self) -> None:
        hints = extract_unlabeled_species_breed_hints("CANINA - YORKSHIRE TERRIER")
        assert hints["pet.species"] == "Dog"
        assert hints["pet.breed"] == "YORKSHIRE TERRIER"
        assert hints["pet.sex"] == "Female"

    def test_canino_dash_breed_line(self) -> None:
        hints = extract_unlabeled_species_breed_hints("Canino - Labrador Retriever")
        assert hints["pet.species"] == "Dog"
        assert hints["pet.breed"] == "Labrador Retriever"
        assert "pet.sex" not in hints

    def test_standalone_species_lines(self) -> None:
        dog_hints = extract_unlabeled_species_breed_hints("Dog")
        assert dog_hints["pet.species"] == "Dog"
        assert "pet.breed" not in dog_hints

        cat_hints = extract_unlabeled_species_breed_hints("Cat")
        assert cat_hints["pet.species"] == "Cat"

    def test_space_separated_species_and_breed(self) -> None:
        hints = extract_unlabeled_species_breed_hints("Felina Persa")
        assert hints["pet.species"] == "Cat"
        assert hints["pet.breed"] == "Persa"
        assert hints["pet.sex"] == "Female"

    def test_rejects_address_fragment_as_breed(self) -> None:
        hints = extract_unlabeled_species_breed_hints("Canino - C/ ORTEGA Y GASSET 1")
        assert hints["pet.species"] == "Dog"
        assert "pet.breed" not in hints


class TestBuildLayoutHintsUnlabeled:
    def test_compound_canina_breed_line(self) -> None:
        likely = build_layout_hints(UNLABELED_CANINA_BREED_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Dog"
        assert likely.get("pet.breed") == "YORKSHIRE TERRIER"
        assert likely.get("pet.sex") == "Female"
        assert likely.get("pet.name") == "LUNA"

    def test_standalone_canino_line(self) -> None:
        likely = build_layout_hints(STANDALONE_CANINO_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Dog"
        assert likely.get("pet.name") == "TOBY"

    def test_standalone_cat_line(self) -> None:
        likely = build_layout_hints(STANDALONE_CAT_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Cat"
        assert likely.get("pet.name") == "WHISKERS"

    def test_space_separated_felina_breed_in_header(self) -> None:
        likely = build_layout_hints(FELINA_BREED_SPACE_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Cat"
        assert likely.get("pet.breed") == "Persa"
        assert likely.get("pet.sex") == "Female"

    def test_labeled_especie_raza_override_unlabeled_lines(self) -> None:
        likely = build_layout_hints(LABELLED_OVERRIDES_UNLABELED_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Cat"
        assert "Persa" in (likely.get("pet.breed") or "")
        assert likely.get("pet.name") == "NINA"

    def test_address_fragment_not_captured_as_breed(self) -> None:
        likely = build_layout_hints(ADDRESS_BREED_REJECTION_DOC)["likely_fields"]
        assert likely.get("pet.species") == "Dog"
        assert likely.get("pet.breed") is None
        assert likely.get("pet.name") == "MARLEY"


class TestStructurerUnlabeledSpeciesBreed:
    def test_fake_llm_structures_unlabeled_header(self) -> None:
        record = FakeLLMStructurer().structure(UNLABELED_CANINA_BREED_DOC)
        assert record.pet.species == "Dog"
        assert "YORKSHIRE" in (record.pet.breed or "")
        assert record.pet.name == "LUNA"

    def test_ollama_heuristic_path_structures_unlabeled_header(self) -> None:
        structurer = OllamaStructurer(
            base_url="http://127.0.0.1:9",
            model="qwen2.5:7b",
            timeout_seconds=1,
            clinical_mode="hybrid",
            skip_demographics_when_hinted=True,
        )
        record = structurer.structure(UNLABELED_CANINA_BREED_DOC)
        assert record.pet.species == "Dog"
        assert "YORKSHIRE" in (record.pet.breed or "")
        assert record.pet.name == "LUNA"
