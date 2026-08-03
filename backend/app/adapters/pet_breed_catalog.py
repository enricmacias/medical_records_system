"""Known dog and cat breed names for heuristic validation."""

from __future__ import annotations

import re
import unicodedata

_DOG_BREED_NAMES: tuple[str, ...] = (
    "affenpinscher",
    "afghan hound",
    "airedale terrier",
    "akita",
    "alaskan malamute",
    "american bulldog",
    "american pit bull terrier",
    "american staffordshire terrier",
    "australian cattle dog",
    "australian shepherd",
    "basenji",
    "basset hound",
    "beagle",
    "bearded collie",
    "belgian malinois",
    "belgian shepherd",
    "bernese mountain dog",
    "bichon frise",
    "border collie",
    "border terrier",
    "boxer",
    "boston terrier",
    "bull terrier",
    "bulldog",
    "bullmastiff",
    "cairn terrier",
    "cane corso",
    "cavalier king charles spaniel",
    "chihuahua",
    "chow chow",
    "cocker spaniel",
    "collie",
    "corgi",
    "dachshund",
    "dalmatian",
    "doberman",
    "doberman pinscher",
    "english bulldog",
    "english setter",
    "english springer spaniel",
    "flat coated retriever",
    "fox terrier",
    "french bulldog",
    "german shepherd",
    "german shorthaired pointer",
    "golden retriever",
    "great dane",
    "great pyrenees",
    "greyhound",
    "galgo",
    "havanese",
    "husky",
    "siberian husky",
    "irish setter",
    "irish wolfhound",
    "jack russell terrier",
    "jack russell",
    "labrador retriever",
    "labrador",
    "lhasa apso",
    "maltese",
    "mastiff",
    "miniature pinscher",
    "miniature schnauzer",
    "newfoundland",
    "norfolk terrier",
    "norwich terrier",
    "old english sheepdog",
    "papillon",
    "pastor aleman",
    "pekingese",
    "pit bull",
    "pitbull",
    "pointer",
    "pomeranian",
    "poodle",
    "pug",
    "rat terrier",
    "rhodesian ridgeback",
    "rottweiler",
    "saint bernard",
    "samoyed",
    "schnauzer",
    "scottish terrier",
    "shar pei",
    "shiba inu",
    "shih tzu",
    "soft coated wheaten terrier",
    "spitz",
    "staffordshire bull terrier",
    "toy poodle",
    "vizsla",
    "weimaraner",
    "west highland white terrier",
    "westie",
    "whippet",
    "wire fox terrier",
    "yorkshire terrier",
    "yorkie",
)

_CAT_BREED_NAMES: tuple[str, ...] = (
    "abyssinian",
    "american bobtail",
    "american curl",
    "american shorthair",
    "american wirehair",
    "angora",
    "balinese",
    "bengal",
    "birman",
    "bombay",
    "british shorthair",
    "burmese",
    "chartreux",
    "cornish rex",
    "devon rex",
    "domestic longhair",
    "domestic shorthair",
    "egyptian mau",
    "exotic shorthair",
    "himalayan",
    "javanese",
    "korat",
    "laperm",
    "maine coon",
    "manx",
    "norwegian forest cat",
    "ocicat",
    "oriental",
    "oriental shorthair",
    "persa",
    "persian",
    "ragdoll",
    "russian blue",
    "azul ruso",
    "scottish fold",
    "selkirk rex",
    "siames",
    "siamese",
    "siamés",
    "siberian",
    "singapura",
    "snowshoe",
    "somali",
    "sphynx",
    "tonkinese",
    "turkish angora",
    "turkish van",
)


def _normalize_breed_key(value: str) -> str:
    text = value.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^\w\s'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_ALL_BREED_KEYS: frozenset[str] = frozenset(
    _normalize_breed_key(name) for name in (*_DOG_BREED_NAMES, *_CAT_BREED_NAMES)
)


def is_known_dog_or_cat_breed(value: str) -> bool:
    """True when value matches a recognized dog or cat breed name."""
    key = _normalize_breed_key(value)
    if not key or len(key) < 2:
        return False
    if key in _ALL_BREED_KEYS:
        return True
    for known in _ALL_BREED_KEYS:
        if known.startswith(key + " "):
            return True
        if key.startswith(known + " "):
            return True
    return False
