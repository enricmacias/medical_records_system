# Problem

Veterinarians need to review pet medical records that arrive in inconsistent PDF formats from different clinics, languages, and templates. Manually reading and re-entering this information is slow and error-prone.

## Goal

Provide a Lean MVP that lets a veterinarian:

1. Upload a pet medical record as a **PDF**
2. Automatically extract the document text
3. Structure the most relevant clinical information into a **standardized JSON** shape (heuristics ± local LLM)
4. Review structured data in a clear web UI (read-only by default) and **edit** when needed

## Non-goals (this exercise)

- Diagnosing or giving medical advice
- Replacing a full practice-management system
- Supporting every document format on day one

## Success for this exercise

Demonstrate sound architecture, incremental delivery, maintainable code, and a solid foundation for future improvements — not a complete commercial product.
