"""
Biomedical entity extraction.
Strategy:
  1. Dictionary-based lookup (fast, high precision)
  2. spaCy NER (en_core_sci_sm if available, else en_core_web_sm)
  3. Pattern matching with regex
"""
import re
import json
import logging
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "dictionaries"


class Entity(NamedTuple):
    text: str
    label: str          # MICROBE | METABOLITE
    entity_type: str    # bacteria | fungi | virus | fatty_acid | amino_acid | etc.
    start: int
    end: int
    source: str         # dict | ner | pattern


# ---------------------------------------------------------------------------
# Dictionary loading
# ---------------------------------------------------------------------------

def _load_json_list(path: Path) -> list[str]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def _build_pattern(terms: list[str]) -> re.Pattern:
    escaped = sorted([re.escape(t) for t in terms], key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE) if escaped else re.compile(r"(?!)")


class EntityDictionaries:
    """Loaded once at startup, used for fast dictionary matching."""

    def __init__(self):
        self.microbes: dict[str, str] = {}   # name -> type (bacteria/fungi/virus)
        self.metabolites: dict[str, str] = {} # name -> class
        self._microbe_pattern: re.Pattern | None = None
        self._metabolite_pattern: re.Pattern | None = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        # Load from dictionaries directory
        bacteria = _load_json_list(DATA_DIR / "bacteria.json")
        fungi = _load_json_list(DATA_DIR / "fungi.json")
        viruses = _load_json_list(DATA_DIR / "viruses.json")
        metabolites_list = _load_json_list(DATA_DIR / "metabolites.json")
        metabolite_classes = json.loads((DATA_DIR / "metabolite_classes.json").read_text()) \
            if (DATA_DIR / "metabolite_classes.json").exists() else {}

        for name in bacteria:
            self.microbes[name.lower()] = "bacteria"
        for name in fungi:
            self.microbes[name.lower()] = "fungi"
        for name in viruses:
            self.microbes[name.lower()] = "virus"

        for name in metabolites_list:
            cls = metabolite_classes.get(name.lower(), "metabolite")
            self.metabolites[name.lower()] = cls

        all_microbes = bacteria + fungi + viruses
        self._microbe_pattern = _build_pattern(all_microbes)
        self._metabolite_pattern = _build_pattern(metabolites_list)
        self._loaded = True
        logger.info(
            f"Entity dictionaries loaded: {len(self.microbes)} microbes, "
            f"{len(self.metabolites)} metabolites"
        )

    def match_microbes(self, text: str) -> list[tuple[str, int, int, str]]:
        if not self._loaded:
            self.load()
        results = []
        for m in self._microbe_pattern.finditer(text):
            name = m.group()
            etype = self.microbes.get(name.lower(), "microbe")
            results.append((name, m.start(), m.end(), etype))
        return results

    def match_metabolites(self, text: str) -> list[tuple[str, int, int, str]]:
        if not self._loaded:
            self.load()
        results = []
        for m in self._metabolite_pattern.finditer(text):
            name = m.group()
            etype = self.metabolites.get(name.lower(), "metabolite")
            results.append((name, m.start(), m.end(), etype))
        return results


_dictionaries = EntityDictionaries()


# ---------------------------------------------------------------------------
# spaCy NER
# ---------------------------------------------------------------------------

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        try:
            _nlp = spacy.load("en_core_sci_sm")
            logger.info("Loaded en_core_sci_sm (scispaCy)")
        except OSError:
            _nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded en_core_web_sm (fallback)")
    except Exception as e:
        logger.warning(f"spaCy unavailable: {e}")
        _nlp = None
    return _nlp


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Genera accepted for binomial names that are not in the dictionaries. The
# legacy pattern accepted ANY "Capitalized lowercase" pair, so sentence starts
# like "The production" or "Gut bacteria" became microbes.
EXTRA_GENERA = {
    "Acinetobacter", "Alistipes", "Bacillus", "Bilophila", "Butyricimonas", "Christensenella",
    "Citrobacter", "Collinsella", "Corynebacterium", "Cutibacterium", "Desulfovibrio", "Dialister",
    "Dorea", "Eggerthella", "Enterobacter", "Erysipelatoclostridium", "Hungatella", "Intestinimonas",
    "Lacticaseibacillus", "Lactiplantibacillus", "Lactococcus", "Leuconostoc", "Ligilactobacillus",
    "Limosilactobacillus", "Megasphaera", "Morganella", "Odoribacter", "Oscillibacter", "Paenibacillus",
    "Parabacteroides", "Pediococcus", "Propionibacterium", "Proteus", "Shigella", "Sutterella",
    "Veillonella", "Weissella", "Yersinia", "Collinsella", "Lactobacillus", "Clostridium",
}
NON_EPITHETS = {
    "species", "spp", "strain", "strains", "abundance", "growth", "infection", "levels", "cells",
    "colonization", "supplementation", "treatment", "isolates", "genes", "spores", "and", "the",
    "was", "were", "has", "have", "with", "from", "that", "this",
}


def _known_genera() -> set[str]:
    _dictionaries.load()
    genera = {name.split()[0] for name in _dictionaries.microbes if " " in name}
    return {g.capitalize() for g in genera} | EXTRA_GENERA


def extract_entities(text: str, strict: bool = True) -> list[Entity]:
    """Extract microbe and metabolite entities from text.

    strict=True (default) accepts out-of-dictionary binomials only when the genus
    is a known microbial genus. strict=False reproduces the legacy behavior.
    """
    if not text:
        return []

    entities: list[Entity] = []
    seen_spans: set[tuple[int, int]] = set()

    def _add(ent: Entity):
        span = (ent.start, ent.end)
        if span not in seen_spans:
            seen_spans.add(span)
            entities.append(ent)

    # 1. Dictionary-based
    _dictionaries.load()
    for name, start, end, etype in _dictionaries.match_microbes(text):
        _add(Entity(name, "MICROBE", etype, start, end, "dict"))
    for name, start, end, etype in _dictionaries.match_metabolites(text):
        _add(Entity(name, "METABOLITE", etype, start, end, "dict"))

    # 2. spaCy NER (adds chemical/organism entities not in dictionaries)
    nlp = _get_nlp()
    if nlp:
        doc = nlp(text[:10000])  # truncate for performance
        for ent in doc.ents:
            span = (ent.start_char, ent.end_char)
            if span in seen_spans:
                continue
            label_map = {
                "ORGANISM": ("MICROBE", "microbe"),
                "TAXON": ("MICROBE", "microbe"),
                "BACTERIA": ("MICROBE", "bacteria"),
                "CHEMICAL": ("METABOLITE", "chemical"),
                "CHEBI": ("METABOLITE", "metabolite"),
                "SIMPLE_CHEMICAL": ("METABOLITE", "chemical"),
            }
            if ent.label_ in label_map:
                label, etype = label_map[ent.label_]
                _add(Entity(ent.text, label, etype, ent.start_char, ent.end_char, "ner"))

    # 3. Pattern matching for common microbe name patterns not in dictionaries
    # Match binomial species names like "Lactobacillus acidophilus"
    species_pattern = re.compile(
        r"\b([A-Z][a-z]+(?:aceae|ales|ota|ia)?)\s+([a-z]{3,})\b"
    )
    genera = _known_genera() if strict else None
    taken = [(e.start, e.end) for e in entities]
    for m in species_pattern.finditer(text):
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        if strict:
            genus, epithet = m.group(1), m.group(2)
            if genus not in genera or epithet in NON_EPITHETS:
                continue
            if any(s < span[1] and span[0] < e for s, e in taken):  # overlaps a dictionary hit
                continue
        seen_spans.add(span)
        entities.append(Entity(m.group(), "MICROBE", "bacteria", m.start(), m.end(), "pattern"))

    return sorted(entities, key=lambda e: e.start)


def get_microbes(text: str) -> list[Entity]:
    return [e for e in extract_entities(text) if e.label == "MICROBE"]


def get_metabolites(text: str) -> list[Entity]:
    return [e for e in extract_entities(text) if e.label == "METABOLITE"]
