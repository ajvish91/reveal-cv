#!/usr/bin/env python3
"""
Extract text from a styled CV PDF and check ATS keyword coverage vs a tailoring run.

Compares PDF extraction to markdown source when available.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

MUST_HAVE_PASS_RATIO = 0.70


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ATS keyword and parseability check on CV PDF")
    p.add_argument("--pdf", type=Path, required=True, help="CV PDF path")
    p.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="cv_runs/<id> folder (loads 02_keyword_ranker_output.json, optional final_cv.md)",
    )
    p.add_argument("--markdown", type=Path, default=None, help="Markdown CV for comparison")
    p.add_argument("--output", type=Path, default=None, help="Write JSON report here")
    p.add_argument("--min-chars", type=int, default=1500, help="Minimum total extracted characters")
    return p.parse_args()


def extract_pdf_text(pdf_path: Path) -> tuple[str, list[str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return "\n\n".join(p for p in pages if p), pages


def load_priority_terms(run_dir: Path | None) -> list[dict]:
    if run_dir is None:
        return []
    path = run_dir / "02_keyword_ranker_output.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    terms = data.get("priority_keywords")
    if not isinstance(terms, list):
        return []
    return [t for t in terms if isinstance(t, dict) and isinstance(t.get("term"), str)]


def load_must_have_terms(run_dir: Path | None) -> list[str]:
    if run_dir is None:
        return []
    path = run_dir / "01_jd_parser_output.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    skills = data.get("must_have_skills")
    if not isinstance(skills, list):
        return []
    return [str(s).strip().lower() for s in skills if str(s).strip()]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _term_in_text(term: str, body: str) -> bool:
    """Substring match with word boundaries for short terms (avoids 'rag' in 'prague')."""
    if re.search(rf"\b{re.escape(term)}\b", body):
        return True
    if " " in term or "/" in term:
        return term in body
    return False


def term_present(term: str, text: str) -> bool:
    t = term.lower().strip()
    body = _normalize(text)
    if not t:
        return False
    if _term_in_text(t, body):
        return True
    aliases = {
        "llm": ("llms", "large language model", "large language models"),
        "production ml/ai systems": ("production ml", "production-oriented", "production ml/ai"),
        "software engineering": ("software engineer",),
        "machine learning": ("ml ", " ml,", " ml."),
        "ai engineering": ("ml/ai", "ml / ai"),
        "agentic ai frameworks": ("agentic ai",),
        "ml pipeline tooling": ("llm pipeline", "data pipeline", "pipelines"),
        "english communication": ("english (fluent)", "english fluent"),
        "cross-functional collaboration": ("cross-functional",),
        "applied nlp": (" nlp",),
        "coding agents": ("coding agent", "agentic ai"),
        "ci/cd": ("ci cd", "cicd"),
        "monitoring": ("model monitoring", "observability", "mlops"),
        "model monitoring": ("mlops", "monitoring", "observability"),
        "observability": ("monitoring", "mlops"),
        "ml pipeline tooling": ("llm pipeline", "data pipeline", "pipelines", "ml pipeline"),
        "conversational ai": ("conversational", "virtual characters", "social robots"),
        "content understanding": ("content understanding", "document processing", "classification"),
        "summarization": ("summarization", "summarize", "summaries"),
        "personalization": ("personalization", "e-commerce", "targeting"),
        "recommendations": ("recommendation", "e-commerce"),
        "embeddings": ("embedding", "vector", "representation learning"),
        "retrieval": ("retrieval", "information retrieval", "retrieved"),
        "rag": ("retrieval-augmented", "rag pipeline", "rag "),
        "search systems": ("search", "retrieval"),
        "tool-use patterns": ("tool-use", "tool use", "agentic ai"),
    }
    for alt in aliases.get(t, ()):
        if _term_in_text(alt.strip(), body) or ((" " not in alt) and alt in body):
            return True
    return False


def keyword_coverage(terms: list[dict], text: str) -> tuple[list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    for item in terms:
        term = str(item["term"]).strip()
        if term_present(term, text):
            found.append(term)
        else:
            missing.append(term)
    return found, missing


def must_have_coverage(must_have: list[str], text: str) -> tuple[list[str], list[str], float]:
    if not must_have:
        return [], [], 1.0
    found = [t for t in must_have if term_present(t, text)]
    missing = [t for t in must_have if t not in found]
    ratio = len(found) / len(must_have)
    return found, missing, ratio


def detect_format_issues(pdf_text: str, pages: list[str], markdown_text: str | None) -> list[str]:
    issues: list[str] = []

    if len(pdf_text) < 1500:
        issues.append(f"Low extracted text volume ({len(pdf_text)} chars); PDF may be image-heavy or poorly encoded.")

    if "\x7f" in pdf_text or "" in pdf_text:
        issues.append("Bullet glyphs did not extract as plain text (found control/wrong characters).")

    hyphen_bullets = sum(1 for line in pdf_text.splitlines() if line.strip().startswith("- "))
    if hyphen_bullets < 5 and (markdown_text or "").count("- ") > 5:
        issues.append("Few hyphen list lines in PDF text vs markdown lists.")

    page1 = pages[0] if pages else ""
    contact_pos = page1.upper().find("CONTACT") if page1 else -1
    # Detect two-column quirk using demo / anonymized name markers only (never real names).
    name_pos = -1
    for marker in ("ALEX RIVERA", "MITCH EVANS"):
        name_pos = page1.find(marker) if page1 else -1
        if name_pos < 0 and page1:
            name_pos = page1.upper().find(marker)
        if name_pos >= 0:
            break
    if contact_pos >= 0 and name_pos >= 0 and contact_pos < name_pos:
        issues.append(
            "Two-column layout: sidebar text appears before main header in extraction order "
            "(common ATS quirk; keywords in profile/experience usually still parse)."
        )

    if "github.com" not in pdf_text.lower() and "linkedin.com" not in pdf_text.lower():
        if markdown_text and ("github.com" in markdown_text.lower() or "linkedin.com" in markdown_text.lower()):
            issues.append(
                "Social URLs present in markdown but not in PDF text layer (hyperlink-only labels)."
            )

    if re.search(r"University of Boston\s+Postdoctoral", pdf_text, re.I):
        issues.append("Employer/title lines may parse in reversed order for some roles.")

    if "Date of birth" in (markdown_text or "") or re.search(
        r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
        pdf_text,
    ):
        # Flag DOB presence without hard-coding a personal birth date.
        if "Date of birth" in (markdown_text or "") or "Fødselsdato" in (markdown_text or ""):
            issues.append("Date of birth in PDF may trigger bias filters in some ATS.")

    return issues


def compare_markdown_keywords(md_text: str, pdf_text: str, terms: list[dict]) -> list[str]:
    notes: list[str] = []
    for item in terms[:15]:
        term = str(item["term"])
        in_md = term_present(term, md_text)
        in_pdf = term_present(term, pdf_text)
        if in_md and not in_pdf:
            notes.append(f"Keyword '{term}' in markdown but not extracted from PDF.")
    return notes


def build_report(
    pdf_path: Path,
    pdf_text: str,
    pages: list[str],
    terms: list[dict],
    must_have: list[str],
    markdown_text: str | None,
) -> dict:
    found, missing = keyword_coverage(terms, pdf_text)
    must_found, must_missing, must_ratio = must_have_coverage(must_have, pdf_text)

    md_found: list[str] = []
    md_missing: list[str] = []
    if markdown_text:
        md_found, md_missing = keyword_coverage(terms, markdown_text)

    format_warnings = detect_format_issues(pdf_text, pages, markdown_text)
    if markdown_text:
        format_warnings.extend(compare_markdown_keywords(markdown_text, pdf_text, terms))

    weighted_score = 0.0
    total_weight = 0.0
    for item in terms:
        w = float(item.get("weight") or 0.5)
        total_weight += w
        if term_present(str(item["term"]), pdf_text):
            weighted_score += w
    ats_score = round(100 * weighted_score / total_weight, 1) if total_weight else 0.0

    return {
        "pdf_path": str(pdf_path.resolve()),
        "extracted_char_count": len(pdf_text),
        "page_count": len(pages),
        "ats_score": ats_score,
        "must_have_coverage_ratio": round(must_ratio, 3),
        "must_have_found": must_found,
        "must_have_missing": must_missing,
        "found_keywords": found,
        "missing_keywords": missing,
        "markdown_found_count": len(md_found),
        "markdown_only_missing_in_pdf": [
            t for t in md_found if not term_present(t, pdf_text)
        ],
        "format_warnings": format_warnings,
        "pass": must_ratio >= MUST_HAVE_PASS_RATIO and len(pdf_text) >= 1500,
        "extracted_text_preview": pdf_text[:1200],
    }


def print_report(report: dict) -> None:
    print(f"PDF: {report['pdf_path']}")
    print(f"Pages: {report['page_count']}  |  Extracted chars: {report['extracted_char_count']}")
    print(f"ATS score (weighted keywords): {report['ats_score']}")
    print(
        f"Must-have coverage: {report['must_have_coverage_ratio']:.0%} "
        f"({len(report['must_have_found'])}/{len(report['must_have_found']) + len(report['must_have_missing'])})"
    )
    print(f"Pass: {report['pass']}")
    print()
    if report["must_have_missing"]:
        print("Must-have missing in PDF text:")
        for t in report["must_have_missing"]:
            print(f"  - {t}")
        print()
    if report["missing_keywords"][:12]:
        print("Other priority keywords missing in PDF:")
        for t in report["missing_keywords"][:12]:
            print(f"  - {t}")
        if len(report["missing_keywords"]) > 12:
            print(f"  ... and {len(report['missing_keywords']) - 12} more")
        print()
    if report["markdown_only_missing_in_pdf"]:
        print("In markdown but not PDF extraction:")
        for t in report["markdown_only_missing_in_pdf"][:10]:
            print(f"  - {t}")
        print()
    if report["format_warnings"]:
        print("Format / extraction warnings:")
        for w in report["format_warnings"]:
            print(f"  ! {w}")
        print()


def main() -> int:
    args = parse_args()
    pdf_path = args.pdf.expanduser().resolve()
    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    run_dir = args.run_dir.expanduser().resolve() if args.run_dir else None
    md_path = args.markdown
    if md_path is None and run_dir:
        candidate = run_dir / "final_cv.md"
        if candidate.is_file():
            md_path = candidate
    markdown_text = md_path.read_text(encoding="utf-8") if md_path and md_path.is_file() else None

    pdf_text, pages = extract_pdf_text(pdf_path)
    terms = load_priority_terms(run_dir)
    must_have = load_must_have_terms(run_dir)

    report = build_report(pdf_path, pdf_text, pages, terms, must_have, markdown_text)
    report["pass"] = report["pass"] and report["extracted_char_count"] >= args.min_chars

    print_report(report)

    out_path = args.output
    if out_path is None and run_dir:
        out_path = run_dir / "ats_pdf_report.json"
    if out_path:
        out_path = out_path.expanduser().resolve()
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote: {out_path}")

    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
