"""Tests for pet breed catalog and breed validation in text_hints."""

from app.adapters.pet_breed_catalog import is_known_dog_or_cat_breed
from app.adapters.text_hints import (
    build_layout_hints,
    infer_pet_breed_from_text,
    validated_breed,
)


def test_catalog_recognizes_common_dog_and_cat_breeds() -> None:
    assert is_known_dog_or_cat_breed("Yorkshire Terrier")
    assert is_known_dog_or_cat_breed("YORKSHIRE TERRIER")
    assert is_known_dog_or_cat_breed("Labrador Retriever")
    assert is_known_dog_or_cat_breed("Labrador")
    assert is_known_dog_or_cat_breed("Golden Retriever")
    assert is_known_dog_or_cat_breed("Domestic Shorthair")
    assert is_known_dog_or_cat_breed("Persa")
    assert is_known_dog_or_cat_breed("Persian")
    assert is_known_dog_or_cat_breed("Maine Coon")


def test_catalog_rejects_non_breed_words() -> None:
    assert not is_known_dog_or_cat_breed("Summary")
    assert not is_known_dog_or_cat_breed("Grammar")
    assert not is_known_dog_or_cat_breed("punctuation")
    assert not is_known_dog_or_cat_breed("C/ ORTEGA Y GASSET 1")


def test_validated_breed_accepts_known_and_rejects_unknown() -> None:
    assert validated_breed("Domestic Shorthair") == "Domestic Shorthair"
    assert validated_breed("YORKSHIRE TERRIER") == "YORKSHIRE TERRIER"
    assert validated_breed("Summary") is None
    assert validated_breed("Informe") is None


def test_infer_pet_breed_skips_invalid_and_finds_next_candidate() -> None:
    text = """
    Breed: Summary
    Breed: Domestic Shorthair
    """
    assert infer_pet_breed_from_text(text) == "Domestic Shorthair"


def test_build_layout_hints_drops_invalid_breed_and_keeps_valid() -> None:
    text = """
    Veterinaria Central
    Raza Summary
    CANINA - YORKSHIRE TERRIER
    Historial
    """
    likely = build_layout_hints(text)["likely_fields"]
    assert likely.get("pet.breed") == "YORKSHIRE TERRIER"
