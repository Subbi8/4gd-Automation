# classifier.py — Line-by-line explanation

This document explains each line and logical block in `classifier.py`. Use this to present to reviewers or to teach others how the classifier and extractor work.

---

## Purpose (one-line)
`classifier.py` implements a deterministic classifier for files using filename heuristics and content extraction (text-based rules). It supports multiple file types: `.txt`, `.md`, `.pdf`, `.docx`, `.pptx`, `.xlsx`/`.xls`.

---

## File header and imports

```python
import os
import re
from pathlib import Path
from typing import Optional
```

- `import os` — standard library module for OS-level interactions (kept for compatibility; not directly used in all functions).
- `import re` — regular expressions used for normalization of text and filenames.
- `from pathlib import Path` — `Path` is a convenient object-oriented file path utility used across the script for portability.
- `from typing import Optional` — used to annotate function return types where `None` is a valid return value.

---

## Keyword mapping configuration

```python
KEYWORDS = {
    "University Docs": [
        "semester", "academic year", "credits", "course code",
        "roll number", "student name", "department", "university",
        "registrar", "faculty", "dean",
        "enrollment", "registration", "approved", "submitted",
        "internship approval", "student id", "application",
        "issued by", "official", "signature", "seal"
    ],
    "Technical Work": [
        "endpoint", "api", "pipeline", "build", "deployment",
        "server", "yaml", "json", "config", "docker", "kubernetes",
        "automate", "monitor", "logging", "debug", "ci/cd",
        "infrastructure", "version", "changelog",
        "developer", "engineer", "technical documentation",
        "readme", "implementation"
    ],
    "Capstone Work": [
        "abstract", "introduction", "methodology", "results",
        "evaluation", "discussion", "conclusion", "references",
        "proposal", "milestone", "phase", "final submission",
        "capstone project", "design", "implementation",
        "slides", "presentation", "data collection",
        "experiment", "analysis"
    ]
}
```

- `KEYWORDS` is a dictionary mapping category names to lists of indicative phrases and words. These are used for simple, deterministic scoring of filenames and extracted content.
- The keywords are intentionally broad and include multi-word phrases (e.g., `"capstone project"`) and single words (e.g., `"api"`) to improve matching coverage.

---

```python
EXT_CONTENT_READERS = {}
```

- A placeholder dictionary for future extension where specific content readers for filetypes might be registered. Not used by the current code but useful for refactor/extension.

---

## Normalization helper

```python
def _text_normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower())
```

- `_text_normalize` lowercases input text and replaces any sequence of non-alphanumeric characters with a single space.
- This normalization makes keyword matching robust to punctuation, casing, and varied spacing.

---

## Content extraction function

```python
def read_text_from_file(path: Path) -> str:
    """Return extracted text for supported extensions."""
    text = ""
    ext = path.suffix.lower()
    try:
        if ext == ".txt" or ext == ".md":
            text = path.read_text(encoding="utf-8", errors="ignore")
        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(path))
                parts = []
                for p in reader.pages:
                    try:
                        parts.append(p.extract_text() or "")
                    except Exception:
                        continue
                text = "\n".join(parts)
            except Exception:
                text = ""
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                text = ""
        elif ext == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation(str(path))
                slides = []
                for slide in prs.slides:
                    for shp in slide.shapes:
                        if hasattr(shp, "text"):
                            slides.append(shp.text)
                text = "\n".join(slides)
            except Exception:
                text = ""
        elif ext in (".xlsx", ".xls"):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
                parts = []
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        for cell in row:
                            if cell is None:
                                continue
                            parts.append(str(cell))
                text = "\n".join(parts)
            except Exception:
                text = ""
        else:
            text = ""
    except Exception:
        text = ""
    return text
```

Line-by-line explanation:
- Declare `read_text_from_file(path: Path) -> str` which accepts a `Path` object and returns the extracted text (empty string on failure).
- `ext = path.suffix.lower()` extracts the extension for branching.
- For `.txt` and `.md`: reads the file as text using UTF-8 and ignores invalid characters.
- For `.pdf`: uses `PyPDF2.PdfReader` and iterates pages, calling `extract_text()` and safely concatenating per-page results. Failures are caught and result in empty text.
- For `.docx`: uses `python-docx` to gather paragraph texts.
- For `.pptx`: uses `python-pptx` to iterate slide shapes and collect any `text` attribute present.
- For `.xlsx` / `.xls`: uses `openpyxl` in read-only mode, iterates worksheets and rows, and collects non-empty cells, converting them to strings.
- In all branches, exceptions are swallowed to ensure the extractor never raises and always returns a string (robustness).

Notes & caveats:
- Scanned PDFs (images) will not yield text via `PyPDF2`; later we may add an OCR step (Tesseract) for that case.
- Excel `.xls` legacy files may not be supported by `openpyxl`; for `.xls` a fallback like `xlrd` would be needed.

---

## Classification by text

```python
def classify_by_text(text: str) -> Optional[str]:
    s = _text_normalize(text)
    scores = {cat: 0 for cat in KEYWORDS}
    for cat, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in s:
                scores[cat] += 1
    best_cat = max(scores, key=lambda k: scores[k])
    if scores[best_cat] == 0:
        return None
    return best_cat
```

- Normalizes text and computes a simple score per category: count of keyword matches.
- Returns the category with the highest score, or `None` if no keywords matched.
- Ties are resolved deterministically by `max` (it will pick the first maximal key according to dictionary order, which is fine for our deterministic needs but can be changed if desired).

---

## classify_file — main entrypoint

```python
def classify_file(path: str) -> str:
    """Classify a single file path into one of the categories. Default fallback is 'Technical Work'"""
    p = Path(path)
    name_text = _text_normalize(p.stem + " " + p.name)
    # 1) filename
    for cat, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in name_text:
                return cat
    # 2) content
    content = read_text_from_file(p)
    if content:
        cat = classify_by_text(content)
        if cat:
            return cat
    # 3) fallback heuristic: file extensions
    ext = p.suffix.lower()
    if ext in (".md", ".txt", ".docx"):
        return "Technical Work"
    if ext in (".pdf", ".doc"):
        # ambiguous, assume University unless 'capstone' appears
        if "capstone" in name_text:
            return "Capstone Work"
        return "University Docs"
    # final fallback
    return "Technical Work"
```

- `classify_file` is the primary function called by automation scripts.
- Steps:
  1. Compose `name_text` from the file's stem (filename without extension) and name, then normalize it.
  2. Try **filename-based classification**: if any keyword appears in the normalized name, return that category immediately — fast and reliable when filenames are meaningful.
  3. If filename does not yield a result, **extract content** and run `classify_by_text` to classify by content.
  4. If still undecided, the classifier does **not** use file-extension heuristics; it deterministically falls back to `Technical Work`.

---

## CLI utility

```python
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python classifier.py <file_path>")
        sys.exit(1)
    print(classify_file(sys.argv[1]))
```

- Allows quick testing from the command line: `python classifier.py path/to/file` prints the detected category.

---

## Presentation tips for the panel
- Explain the deterministic-first design: filename > content > heuristic > fallback. This design guarantees repeatability and transparent reasoning for the required 5-run accuracy target.
- Mention where it’s safe to extend: add OCR for scanned PDFs, use embeddings/LLMs for ambiguous cases (with a review queue), or add unit tests for new extractors.

---

If you want, I can produce a short single-slide markdown summary or add per-function unit tests to the repository. Let me know which you prefer.