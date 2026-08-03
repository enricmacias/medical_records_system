"""Tests for global demographic inference fallbacks in text_hints."""

from app.adapters.text_hints import (
    HEADER_SCAN_LINES,
    apply_global_demographic_inference,
    build_layout_hints,
    infer_pet_breed_from_text,
    infer_pet_name_from_text,
    infer_pet_sex_from_text,
    infer_owner_email_from_text,
    infer_owner_phone_from_text,
    validated_pet_name,
)


DOCX_TABLE_HEADER = """
Sunshine Vet Clinic
Visit date: 2024-06-10

Breed: | Domestic Shorthair | Sex | Female (Spayed)
Pet: Buddy | Species: Feline
Owner: Jane Doe
Phone: +1-555-0100
Email: jane@example.com
Address: 123 Main St, Madrid
"""


def test_header_scan_lines_is_100() -> None:
    assert HEADER_SCAN_LINES == 100


def test_infer_breed_and_sex_from_pipe_table_row() -> None:
    text = "Breed: | Domestic Shorthair | Sex | Female (Spayed)"
    assert infer_pet_breed_from_text(text) == "Domestic Shorthair"
    assert infer_pet_sex_from_text(text) == "Female"


def test_infer_owner_contact_from_labeled_lines() -> None:
    text = "Phone: +1-555-0100\nEmail: jane@example.com"
    assert infer_owner_phone_from_text(text) == "+1-555-0100"
    assert infer_owner_email_from_text(text) == "jane@example.com"


def test_apply_global_demographic_inference_fills_missing_fields() -> None:
    hints: dict = {"likely_fields": {"pet.species": "Cat"}}
    apply_global_demographic_inference(hints, DOCX_TABLE_HEADER)
    likely = hints["likely_fields"]
    assert likely["pet.species"] == "Cat"
    assert likely["pet.breed"] == "Domestic Shorthair"
    assert likely["pet.sex"] == "Female"
    assert likely["pet.name"] == "Buddy"
    assert likely["owner.name"] == "Jane Doe"
    assert likely["owner.phone"] == "+1-555-0100"
    assert likely["owner.email"] == "jane@example.com"
    assert "Madrid" in likely["owner.address"]


def test_build_layout_hints_uses_global_inference() -> None:
    hints = build_layout_hints(DOCX_TABLE_HEADER)
    likely = hints["likely_fields"]
    assert likely.get("pet.breed") == "Domestic Shorthair"
    assert likely.get("pet.sex") == "Female"
    assert likely.get("owner.email") == "jane@example.com"


def test_infer_pet_name_after_label_without_colon() -> None:
    assert infer_pet_name_from_text("Patient Max\nHistorial") == "Max"
    assert infer_pet_name_from_text("Paciente MARLEY\nHistorial") == "MARLEY"
    assert infer_pet_name_from_text("Pet Buddy species cat") == "Buddy"
    assert infer_pet_name_from_text("Mascota LUNA\nConsulta") == "LUNA"


def test_infer_pet_name_rejects_label_followed_by_non_name() -> None:
    assert infer_pet_name_from_text("Patient record\nMARLEY") == "MARLEY"
    assert infer_pet_name_from_text("Datos del paciente\nTOBY") == "TOBY"


def test_infer_pet_name_from_standalone_caps_line() -> None:
    text = """
    CLINICA VETERINARIA
    MARLEY
    Canino - Labrador
    Historial
    """
    assert infer_pet_name_from_text(text) == "MARLEY"


def test_infer_pet_name_from_caps_on_nombre_line() -> None:
    assert infer_pet_name_from_text("Nombre LUNA\nHistorial") == "LUNA"
    assert infer_pet_name_from_text("Name WHISKERS\nHistory") == "WHISKERS"


def test_rejects_non_proper_name_words() -> None:
    assert validated_pet_name("Summary") is None
    assert validated_pet_name("Grammar") is None
    assert validated_pet_name("punctuation") is None
    assert validated_pet_name("Resumen") is None
    assert infer_pet_name_from_text("Nombre Summary\nMARLEY") == "MARLEY"
    assert infer_pet_name_from_text("Pet Grammar\nLUNA") == "LUNA"
    assert infer_pet_name_from_text("Paciente Informe\nTOBY") == "TOBY"


def test_build_layout_hints_drops_invalid_pet_name_and_finds_next() -> None:
    text = """
    Veterinaria Central
    Nombre Summary
    MARLEY
    Canino - Labrador
  Historial
    """
    likely = build_layout_hints(text)["likely_fields"]
    assert likely.get("pet.name") == "MARLEY"
