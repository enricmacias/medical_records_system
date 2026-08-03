"""Integration tests for demographic validation, resolution, and LLM fallbacks."""

from app.adapters.llm import FakeLLMStructurer, OllamaStructurer
from app.adapters.text_hints import (
    apply_global_demographic_inference,
    build_layout_hints,
    resolve_breed,
    resolve_pet_name,
    validated_breed,
    validated_pet_name,
)
from app.domain.extraction_models import ExtractionClinicalInfo, ExtractionRecord, VisitInfo
from app.domain.models import MetaInfo, OwnerInfo, PetInfo


def _record(
    *,
    pet: PetInfo | None = None,
    owner: OwnerInfo | None = None,
    visit: VisitInfo | None = None,
    meta: MetaInfo | None = None,
) -> ExtractionRecord:
    return ExtractionRecord(
        pet=pet or PetInfo(),
        owner=owner or OwnerInfo(),
        visit=visit or VisitInfo(),
        clinical=ExtractionClinicalInfo(),
        meta=meta or MetaInfo(),
    )


class TestResolvePetNameAndBreed:
    def test_resolve_pet_name_prefers_valid_record_name(self) -> None:
        assert resolve_pet_name("MARLEY", "LUNA") == "MARLEY"
        assert resolve_pet_name("MARLEY", None) == "MARLEY"

    def test_resolve_pet_name_falls_back_to_valid_hint(self) -> None:
        assert resolve_pet_name("Summary", "MARLEY") == "MARLEY"
        assert resolve_pet_name("Grammar", "TOBY") == "TOBY"

    def test_resolve_pet_name_returns_none_when_both_invalid(self) -> None:
        assert resolve_pet_name("Summary", "Grammar") is None
        assert resolve_pet_name(None, "Informe") is None

    def test_resolve_breed_prefers_valid_record_breed(self) -> None:
        assert resolve_breed("Golden Retriever", "Labrador") == "Golden Retriever"

    def test_resolve_breed_falls_back_to_valid_hint(self) -> None:
        assert resolve_breed("Summary", "Labrador Retriever") == "Labrador Retriever"
        assert resolve_breed("Grammar", "Persa") == "Persa"

    def test_resolve_breed_returns_none_when_both_invalid(self) -> None:
        assert resolve_breed("Summary", "Informe") is None


class TestValidatedDemographics:
    def test_validated_pet_name_accepts_plausible_proper_names(self) -> None:
        assert validated_pet_name("MARLEY") == "MARLEY"
        assert validated_pet_name("Luna") == "Luna"
        assert validated_pet_name("Buddy") == "Buddy"
        assert validated_pet_name("ALYA") == "ALYA"

    def test_validated_breed_requires_catalog_match(self) -> None:
        assert validated_breed("Labrador Retriever") == "Labrador Retriever"
        assert validated_breed("Persa") == "Persa"
        assert validated_breed("Random Mix") is None


class TestApplyGlobalDemographicInference:
    def test_replaces_invalid_stored_name_with_next_valid_candidate(self) -> None:
        hints: dict = {"likely_fields": {"pet.name": "Summary"}}
        head = "Nombre LUNA\nHistorial"
        apply_global_demographic_inference(hints, head)
        assert hints["likely_fields"]["pet.name"] == "LUNA"

    def test_replaces_invalid_stored_breed_with_next_valid_candidate(self) -> None:
        hints: dict = {"likely_fields": {"pet.breed": "Summary"}}
        head = "Breed: Golden Retriever\nHistorial"
        apply_global_demographic_inference(hints, head)
        assert hints["likely_fields"]["pet.breed"] == "Golden Retriever"

    def test_normalizes_sex_to_canonical_values(self) -> None:
        hints: dict = {"likely_fields": {"pet.sex": "Hembra"}}
        apply_global_demographic_inference(hints, "Historial")
        assert hints["likely_fields"]["pet.sex"] == "Female"

        hints_male: dict = {"likely_fields": {"pet.sex": "Macho"}}
        apply_global_demographic_inference(hints_male, "Historial")
        assert hints_male["likely_fields"]["pet.sex"] == "Male"


class TestOllamaStructurerFallbacks:
    def test_demographics_fallbacks_replace_invalid_llm_name_with_hint(self) -> None:
        record = _record(pet=PetInfo(name="Summary", species="Dog"))
        hints = {"likely_fields": {"pet.name": "MARLEY"}}
        result = OllamaStructurer._apply_demographics_fallbacks(record, hints)
        assert result.pet.name == "MARLEY"

    def test_demographics_fallbacks_replace_invalid_llm_breed_with_hint(self) -> None:
        record = _record(pet=PetInfo(breed="Summary"))
        hints = {"likely_fields": {"pet.breed": "Golden Retriever"}}
        result = OllamaStructurer._apply_demographics_fallbacks(record, hints)
        assert result.pet.breed == "Golden Retriever"

    def test_demographics_fallbacks_clear_invalid_name_when_no_valid_hint(self) -> None:
        record = _record(pet=PetInfo(name="Summary"))
        hints = {"likely_fields": {"pet.name": "Grammar"}}
        result = OllamaStructurer._apply_demographics_fallbacks(record, hints)
        assert result.pet.name is None

    def test_apply_fallbacks_normalizes_sex_on_record(self) -> None:
        record = _record(pet=PetInfo(sex="H"))
        result = OllamaStructurer._apply_fallbacks(record, {"likely_fields": {}})
        assert result.pet.sex == "Female"

    def test_apply_fallbacks_normalizes_sex_from_hints(self) -> None:
        record = _record(pet=PetInfo(sex=None))
        hints = {"likely_fields": {"pet.sex": "Macho"}}
        result = OllamaStructurer._apply_fallbacks(record, hints)
        assert result.pet.sex == "Male"

    def test_hints_sufficient_requires_valid_pet_name(self) -> None:
        assert not OllamaStructurer._hints_sufficient(
            {"likely_fields": {"pet.name": "Summary"}}
        )
        assert OllamaStructurer._hints_sufficient({"likely_fields": {"pet.name": "MARLEY"}})


class TestFakeLLMWithValidation:
    def test_structures_unlabeled_header_with_validated_demographics(self) -> None:
        text = """
        CLINICA VETERINARIA
        CANINA - YORKSHIRE TERRIER
        Nombre LUNA
        Hembra Estado: FERTIL Peso:0
        Historial
        - 01/02/20 - 10:00 -
        Consulta rutina.
        """
        record = FakeLLMStructurer().structure(text)
        assert record.pet.name == "LUNA"
        assert record.pet.species == "Dog"
        assert "YORKSHIRE" in (record.pet.breed or "")
        assert record.pet.sex == "Female"

    def test_build_layout_end_to_end_docx_style_row(self) -> None:
        text = (
            "Breed: | Domestic Shorthair | Sex | Female (Spayed)\n"
            "Pet: Buddy | Species: Feline\n"
            "Owner: Jane Doe"
        )
        likely = build_layout_hints(text)["likely_fields"]
        assert likely.get("pet.name") == "Buddy"
        assert likely.get("pet.breed") == "Domestic Shorthair"
        assert likely.get("pet.sex") == "Female"
        assert likely.get("pet.species") == "Cat"
