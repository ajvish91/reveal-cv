"""
Shared CV tailoring style rules for agents and run scaffolding.

See cv_generation/CV_AUTOMATION.md → “Tailoring style”.
"""
from __future__ import annotations

SKILLS_SIDEBAR_MAX = 4

# PDF layout: long Profile/Summary pushes main column to page 3+, where sidebar tail
# sections (languages/hobbies) must appear only once on the first continuation page.
PROFILE_MAX_PARAGRAPHS = 2
PROFILE_MAX_CHARS_PER_PARAGRAPH = 400
PROFILE_MAX_TOTAL_CHARS = 750

SUMMARY_MAX_BULLETS = 5
SUMMARY_MAX_CHARS_PER_BULLET = 220

PROFILE_LENGTH_HINT = (
    f"Profile: at most {PROFILE_MAX_PARAGRAPHS} short paragraphs; each under "
    f"{PROFILE_MAX_CHARS_PER_PARAGRAPH} characters (~55 words); total under "
    f"{PROFILE_MAX_TOTAL_CHARS} characters."
)

SUMMARY_LENGTH_HINT = (
    f"Academic Summary: at most {SUMMARY_MAX_BULLETS} bullets; each under "
    f"{SUMMARY_MAX_CHARS_PER_BULLET} characters."
)

SKILLS_LINE_HINT = (
    "Skills sidebar: at most four role-relevant terms from the source CV, semicolon-separated "
    "(e.g. Python; LLM fine-tuning; software engineering; PyTorch). No laundry lists; "
    "put other ATS terms in experience bullets."
)

TAILORING_CONSTRAINTS: tuple[str, ...] = (
    "Do not fabricate achievements, numbers, dates, or responsibilities.",
    "Preserve factual integrity with candidate source CV.",
    "Profile: two short plain paragraphs max; readable prose, not a keyword wall.",
    PROFILE_LENGTH_HINT,
    SUMMARY_LENGTH_HINT,
    "Place ATS keywords mainly in experience bullets and Skills, not stuffed into Profile.",
    SKILLS_LINE_HINT,
    "Supplementary application files (when required): cover_letter.md (industry), "
    "application_letter.md (academic motivation), research_proposal.md (postdoc/researcher). "
    "Use MITCH EVANS and other CV placeholders; see application_artifacts.md in the run folder. "
    "private_cv apply deanonymizes every present file.",
    "Cover letter voice: clear explanatory prose; moderate first person; four paragraphs; "
    "map role tasks to transferable skills; cloud platforms once per artifact; do not oversell or "
    "invent platform experience; tone down means moderate not remove.",
    "Inline emphasis: use **bold** sparingly in Profile and bullets (0–1 phrases per bullet); "
    "avoid bold in Contact, Skills, Languages, Education headers, or role titles.",
    "Do not use emoji, tables, columns, or icons in CV markdown.",
    "ForwardMedia / Democracy base (University of Boston postdoc): optional; see "
    "cv_generation/reference/forwardmedia_boston_context.md; include only when media, democracy, "
    "or responsible-media-AI roles warrant it.",
    "Tritium backend / MEAN stack (REST APIs, Node.js, Express, MongoDB): optional; see "
    "cv_generation/reference/tritium_backend_context.md; emphasize for full-stack, API, or "
    "MEAN-stack corporate roles.",
    "Chronology: match terminology to the role dates. Do not retroactively label pre-2023 roles with "
    "post-2023 buzzwords (e.g. agentic AI, coding agents, LLM fine-tuning) unless the source bullet "
    "already uses them. Weave JD keywords into recent, honest roles instead.",
    "Institution integrity: never swap or relabel employers or degree-granting institutions. "
    "Ph.D. and M.Sc. institutions in Education must match the source CV exactly. The Ph.D. institution "
    "must match the Ph.D. student experience employer; teaching or guest roles must name the institution "
    "from the source Teaching section, not a different degree institution.",
)

BULLET_CHRONOLOGY_HINT = (
    "Match stack and AI terminology to each role's dates. Do not apply post-2023 buzzwords "
    "(agentic AI, coding agents, LLM fine-tuning, GenAI) to pre-2023 experience unless the source "
    "bullet already uses them. Period-accurate terms for older roles: conversational AI, social "
    "robotics, reinforcement learning, NLP, multimodal perception. Place JD-only keywords in "
    "recent roles when truthful."
)

INSTITUTION_INTEGRITY_HINT = (
    "Institution integrity: keep role company headers and degree institutions exactly as in the source CV. "
    "Never swap Ph.D. and M.Sc. institutions or substitute one university for another. "
    "Ph.D. institution in Education must match the Ph.D. student experience employer. "
    "Teaching or guest-role institution names must match the source Teaching section."
)

COVER_LETTER_VOICE: tuple[str, ...] = (
    "Clear, calm, explanatory prose. Academic but readable. Full sentences that build a point step by step.",
    "Open with a compelling link between the role and what matters to the candidate; avoid generic or hype openings.",
    "Connect ideas with since, when, however, at the same time, for example. Do not use em-dashes.",
    "Avoid casual or marketing tone: rhythm, get-it-done, punchy colon lists, startup filler.",
    "First person: mix I-led sentences with work-led sentences; tone down I frequency, do not remove I entirely "
    "or rewrite the whole letter in impersonal passive voice.",
    "Length: four substantive body paragraphs plus a brief closing; trim repetition, not whole arguments.",
    "No bold in the letter body except **Re: Role title** in the heading.",
    "Show fit by mapping posting tasks to transferable skills from the CV (agents, integrations, "
    "prototyping, enablement, Python/API work). Do not write I have not used [tool].",
    "Never invent production experience with tools not in the source CV.",
    "Ph.D. arc: tie explore/test/seek-help independence to completing after supervisor left midway when relevant.",
    "Institution integrity: when citing Ph.D. or M.Sc. institutions, use the exact names from final_cv.md "
    "Education and matching experience role headers; never swap Arkansas/Texas or other anonymized placeholders.",
    "Cloud (Azure, AWS): once in CV (one dated experience bullet) and once in cover letter; earlier production "
    "deployments only, not a headline skill; can pick up new platform tooling; do not oversell in Profile/Skills.",
    "When user asks to tone down a trait, moderate it; do not delete the underlying point.",
    "Location, language, work permit when the posting cares.",
)

BULLET_TAILOR_EMPHASIS_HINT = (
    "Optional inline markdown emphasis: **bold** for one high-signal phrase per bullet "
    "(e.g. a stack term or outcome the role cares about). Keep Profile mostly unbolded. "
    "Never bold entire sentences."
)

ATS_EMPHASIS_HINT = (
    "Markdown **bold** and *italic* in Profile or bullets are allowed for PDF rendering; "
    "do not flag them as ATS format errors if the text remains plain and parseable."
)

# Norwegian B1 localization (post-tailoring pass; English remains canonical).
SECTION_LABELS_NO: dict[str, str] = {
    "Name": "Navn",
    "Role": "Stilling",
    "Profile": "Profil",
    "Date of birth": "Fødselsdato",
    "Contact": "Kontakt",
    "Skills": "Ferdigheter",
    "Languages": "Språk",
    "Experience": "Erfaring",
    "Education": "Utdanning",
    "Selected Publications": "Utvalgte publikasjoner",
    "Hobbies": "Hobbyer",
    "Summary": "Sammendrag",
    "Research experience": "Forskningserfaring",
    "Teaching and supervision": "Undervisning og veiledning",
    "Research and publications": "Forskning og publikasjoner",
}

SIDEBAR_LABELS_NO: dict[str, str] = {
    "CONTACT": "KONTAKT",
    "SKILLS": "FERDIGHETER",
    "LANGUAGES": "SPRÅK",
    "HOBBIES": "HOBBYER",
    "PROFILE": "PROFIL",
    "EXPERIENCE": "ERFARING",
    "EDUCATION": "UTDANNING",
    "SELECTED PUBLICATIONS": "UTVALGTE PUBLIKASJONER",
}

MAIN_LABELS_NO: dict[str, str] = {
    "PROFILE": "PROFIL",
    "SUMMARY": "SAMMENDRAG",
    "TEACHING AND SUPERVISION": "UNDERVISNING OG VEILEDNING",
    "RESEARCH EXPERIENCE": "FORSNINGSERFARING",
    "RESEARCH AND PUBLICATIONS": "FORSKNING OG PUBLIKASJONER",
    "WORK EXPERIENCE": "ARBEIDSERFARING",
    "EDUCATION": "UTDANNING",
    "SELECTED PUBLICATIONS": "UTVALGTE PUBLIKASJONER",
}

NORWEGIAN_B1_CV_VOICE: tuple[str, ...] = (
    "Write polished CEFR B1 Norwegian: grammatically correct, but plain vocabulary and short-to-medium sentences.",
    "Profile: two short paragraphs; readable prose, not a keyword wall; same facts as the English source.",
    "Experience bullets: one main idea per bullet; weave role terms naturally; optional **bold** on one stack term.",
    "Prefer high-frequency words (jobb, erfaring, lage, hjelpe, viktig, arbeide med, sammen med).",
    "Keep technical terms as used in Norwegian tech CVs: Python, LLM, Azure, AWS, Docker, CI/CD, MLOps, PyTorch.",
    "Use connectors sparingly in CV bullets; in Profile you may use for eksempel, i tillegg, dessuten.",
    "Do not translate employer names, degree titles, publication titles, URLs, emails, or phone numbers.",
    "Translate section headers to Norwegian (see SECTION_LABELS_NO). H1: # Bransje-CV for industry, # Akademisk CV for academic.",
    "Translate contact labels (E-post, Telefon, Sted, Arbeidstillatelse); translate work permit value to Gyldig norsk arbeidstillatelse.",
    "Translate ## Role / ## Stilling job title to natural Norwegian (e.g. Senior AI Platform Engineer -> Senior AI-plattformingeniør).",
    "Translate experience role lines (### headers and role title lines); keep employer names as-is.",
    "Use Norwegian dates: 15. mars 1992; sep. 2025 – mar. 2026; nå for Present.",
    "Translate hobby bullets to simple Norwegian (e.g. Skiing -> Ski, Backpacking -> Fotturer).",
    "Languages line: use Norsk (B1, lærer fortsatt) when the source says B2 studying unless told otherwise.",
    "Never invent achievements, tools, dates, or employers. Preserve bullet count and every ### experience role.",
    "Avoid bureaucratic C1 phrasing (i den forbindelse, det viser seg at, henviser til).",
)

def _truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """Trim to max_chars, preferring a word boundary and a closing period."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    # Reserve one character when we may append a sentence-ending period.
    budget = max(max_chars - 1, 1)
    cut = cleaned[:budget]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip(".,;:")
    if not cut:
        return cleaned[:max_chars]
    if cut.endswith("."):
        return cut[:max_chars]
    periodized = f"{cut}."
    return periodized if len(periodized) <= max_chars else cut[:max_chars]


def normalize_profile_paragraphs(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    """
    Enforce Profile length for PDF layout. Returns (trimmed paragraphs, warnings).
    """
    warnings: list[str] = []
    cleaned = [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()]
    if len(cleaned) > PROFILE_MAX_PARAGRAPHS:
        warnings.append(
            f"Profile had {len(cleaned)} paragraphs; kept first {PROFILE_MAX_PARAGRAPHS}."
        )
        cleaned = cleaned[:PROFILE_MAX_PARAGRAPHS]

    trimmed: list[str] = []
    total = 0
    for para in cleaned:
        limited = _truncate_at_word_boundary(para, PROFILE_MAX_CHARS_PER_PARAGRAPH)
        if len(limited) < len(para):
            warnings.append(
                f"Profile paragraph trimmed from {len(para)} to {len(limited)} characters."
            )
        remaining = PROFILE_MAX_TOTAL_CHARS - total
        if remaining <= 0:
            warnings.append("Profile total character budget reached; dropped extra paragraphs.")
            break
        if len(limited) > remaining:
            limited = _truncate_at_word_boundary(limited, remaining)
            warnings.append(
                f"Profile total trimmed to {PROFILE_MAX_TOTAL_CHARS} characters."
            )
        trimmed.append(limited)
        total += len(limited)
        if total >= PROFILE_MAX_TOTAL_CHARS:
            break
    return trimmed, warnings


def normalize_summary_bullets(bullets: list[str]) -> tuple[list[str], list[str]]:
    """Enforce academic Summary bullet count and length."""
    warnings: list[str] = []
    cleaned = [b.strip() for b in bullets if isinstance(b, str) and b.strip()]
    if len(cleaned) > SUMMARY_MAX_BULLETS:
        warnings.append(
            f"Summary had {len(cleaned)} bullets; kept first {SUMMARY_MAX_BULLETS}."
        )
        cleaned = cleaned[:SUMMARY_MAX_BULLETS]

    trimmed: list[str] = []
    for bullet in cleaned:
        limited = _truncate_at_word_boundary(bullet, SUMMARY_MAX_CHARS_PER_BULLET)
        if len(limited) < len(bullet):
            warnings.append(
                f"Summary bullet trimmed from {len(bullet)} to {len(limited)} characters."
            )
        trimmed.append(limited)
    return trimmed, warnings


NORWEGIAN_COVER_LETTER_BODY_MIN_WORDS = 250
NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS = 350
NORWEGIAN_COVER_LETTER_MAX_BODY_PARAGRAPHS = 4

NORWEGIAN_COVER_LETTER_LENGTH_HINT = (
    f"Body length: {NORWEGIAN_COVER_LETTER_BODY_MIN_WORDS}–{NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS} "
    f"Norwegian words (excluding header and signature); at most "
    f"{NORWEGIAN_COVER_LETTER_MAX_BODY_PARAGRAPHS} short body paragraphs plus brief closing."
)

NORWEGIAN_B1_COVER_LETTER_VOICE: tuple[str, ...] = (
    "Polished CEFR B1 Norwegian: plain words, correct grammar, short sentences (aim for 12–18 words).",
    "Adapt COVER_LETTER_VOICE for Norwegian: calm explanatory prose; no em-dashes; no marketing filler "
    "or punchy colon lists.",
    "Prefer high-frequency words: jobber, bygger, liker, kan, vil, har, lærer, samarbeider, bidrar, hjelper.",
    "Avoid bureaucratic C1 phrasing: i den forbindelse, det viser seg at, omfattet, vedvarende, "
    "produksjonsklare, henviser til, inkluderte også.",
    "Open with a simple link between the role and what matters; optional Kjære rekrutteringsteam after the heading.",
    "Connect ideas with siden, når, men, for eksempel, dessuten — at most one connector per sentence.",
    "Mix jeg-led sentences with work-led sentences; moderate jeg frequency.",
    NORWEGIAN_COVER_LETTER_LENGTH_HINT,
    "One main idea per paragraph; split long English sentences into two shorter Norwegian sentences.",
    "Required: one honest sentence on personality and team fit (calm collaboration, learning from colleagues, "
    "clear communication in cross-functional teams) — no hype.",
    "No bold except **Ang: Role title** in the heading (translate Re: to Ang:).",
    "Map posting tasks to transferable skills from the CV. Do not write jeg har ikke brukt [verktøy].",
    "Never invent production experience with tools not in the source CV.",
    "Cloud (Azure, AWS): mention once; earlier production context, not headline specialty.",
    "Mention work permit and Norwegian learning once when relevant.",
    "Closing: short and polite (e.g. Takk for at dere vurderer søknaden min).",
)
