"""
This script contains tools for bi-directional synchronisation
of the Lean formalisation data with this repository's.

The "downward" direction takes the data from a local checkout of this script
and generates a file 1000.yaml containing all relevant information about Lean
formalisations: that file is used in Lean's mathlib library.

The "upward" direction reads the file 1000.yaml from mathlib
(passed in as a local file), compares the data about Lean formalisations
with the one in this repository and adds/overwrites this (and only this) data.

This script depends on the details of the file 1000.yaml in mathlib,
so should evolve with any changes there.
"""


import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, NamedTuple, Optional
from datetime import datetime
import yaml

class ProofAssistant(Enum):
    Isabelle = auto()
    HolLight = auto()
    Coq = auto()
    Lean = auto()
    Metamath = auto()
    Mizar = auto()


# The different formalisation statusses: just the statement or also the proof.
class FormalizationStatus(Enum):
    # The statement of a result was formalized (but not its proof yet).
    Statement = auto()
    # The full proof of a result was formalized.
    FullProof = auto()

    @staticmethod
    def from_str(input: str):
        return {
            "formalized": FormalizationStatus.FullProof,
            "statement": FormalizationStatus.Statement,
        }[input]


# In what library does the formalization appear?
class Library(Enum):
    # The standard library ("S")
    StandardLibrary = auto()
    # The main/biggest mathematical library ("L").
    # (afp, hol light outside standard library, mathcomp, mathlib, mml, set.mm, respectively.)
    MainLibrary = auto()
    # External to the main or standard library (e.g., a dedicated repository) ("X")
    External = auto()

    @staticmethod
    def from_str(input: str):
        return {
            "S": Library.StandardLibrary,
            "L": Library.MainLibrary,
            "X": Library.External,
        }[input]


# "Raw" version of a formalisation entry: not typed yet.
@dataclass
class FormalizationEntryRaw:
    status: str
    library: str
    url: str
    authors: Optional[List[str]] = None
    date: Optional[datetime] = None
    comment: Optional[str] = None


class FormalisationEntry(NamedTuple):
    status: FormalizationStatus
    library: Library
    # A URL pointing to the formalization
    url: str
    authors: Optional[List[str]]
    # Format `YYYY-MM-DD`, `YYYY-MM` or `YYYY` in the source file.
    date: Optional[datetime]
    comment: Optional[str]


# Parse a typed version of a formalisation entry from its raw version.
# XXX: this assumes all entries are well-typed, for now
def parse_formalization_entry(entry: FormalizationEntryRaw) -> FormalisationEntry:
    return FormalisationEntry(
        FormalizationStatus.from_str(entry.status),
        Library.from_str(entry.library),
        entry.url, entry.authors, entry.date, entry.comment
    )


# "Raw" version of a theorem entry: not typed yet.
@dataclass
class TheoremEntryRaw:
    wikidata: str
    msc_classification: str
    wikipedia_links: List[str]
    id_suffix: Optional[str] = None
    isabelle: Optional[List[FormalizationEntryRaw]] = None
    hol_light: Optional[List[FormalizationEntryRaw]] = None
    coq: Optional[List[FormalizationEntryRaw]] = None
    lean: Optional[List[FormalizationEntryRaw]] = None
    metamath: Optional[List[FormalizationEntryRaw]] = None
    mizar: Optional[List[FormalizationEntryRaw]] = None


# Information about a theorem entry: taken from the specification at
# https://github.com/1000-plus/1000-plus.github.io/blob/main/README.md#file-format.
class TheoremEntry(NamedTuple):
    # Wikidata identifier for this theorem (or concept related to the theorem).
    # Valid identifiers start with the latter Q followed by a number.
    wikidata: str
    # disambiguates an entry when two theorems have the same wikidata identifier.
    # X means an extra theorem on a Wikipedia page (e.g. a generalization or special case),
    # A/B/... means different theorems on one Wikipedia page that doesn't have a "main" theorem.
    id_suffix: Optional[str]
    # Our best guess of the MSC-classification. (Should be a two-digit string; not validated.)
    msc_classification: str
    # The exact link to a wikipedia page: format [[Page name]] or [[Wiki-link|Displayed name]].
    wikipedia_links: List[str]
    # Entries about formalizations in any of the supported proof assistants.
    # Several formalization entries for one assistant are allowed.
    formalisations: dict[ProofAssistant, List[FormalisationEntry]]


# Check if a string is a valid wikidata identifier of the kind we want,
# i.e. a letter Q followed by a number.
# Print an error if not.
def is_valid_wikidata(input: str) -> bool:
    if not input.startswith("Q"):
        print(f"error: invalid wikidata identifier {input}; must start with a letter 'Q'")
        return False
    try:
        parsed = int(input.removeprefix("Q"))
        return True
    except ValueError:
        print("invalid input: {input} must be the letter 'Q', followed by a number")
        return False


# Return a human-ready theorem title, as well as a `TheoremEntry` with the underlying data.
# Return `None` if `contents` does not describe a valid theorem entry.
def _parse_theorem_entry(contents: List[str]) -> TheoremEntry | None:
    assert contents[0].rstrip() == "---"
    assert contents[-1].rstrip() == "---"
    # For optics, we check that all entry files start with the theorem name as comment.
    # We parse the actual title from the wikipedia data below: this yields virtually the same results.
    assert contents[1].startswith("# ") or contents[1].startswith("## ")
    raw_data = yaml.safe_load("".join(contents[1:-1]))
    raw_thm = TheoremEntryRaw(**raw_data)
    if not is_valid_wikidata(raw_thm.wikidata):
        return None

    passthrough = {
        ProofAssistant.Isabelle: raw_thm.isabelle,
        ProofAssistant.HolLight: raw_thm.hol_light,
        ProofAssistant.Coq: raw_thm.coq,
        ProofAssistant.Metamath: raw_thm.metamath,
        ProofAssistant.Mizar: raw_thm.mizar,
        ProofAssistant.Lean: raw_thm.lean,
    }
    formalisations = {}
    for (pa, raw) in passthrough.items():
        if raw:
            entries: List[FormalisationEntry] = [parse_formalization_entry(entry) for entry in raw]
            if None in entries:
                return None
            formalisations[pa] = entries
        else:
            formalisations[pa] = []
    res = TheoremEntry(
        raw_thm.wikidata, raw_thm.id_suffix, raw_thm.msc_classification, raw_thm.wikipedia_links,
        formalisations
    )
    return res


def _parse_title_inner(wiki_links: List[str]) -> str:
    # FIXME: what's the best way to deal with multiple links here?
    # For now, let's match the webpage and just show the first link's target.
    # if len(entry.wikipedia_links) > 1:
    #     print(f"attention: found several wikipedia links for a theorem: {entry.wikipedia_links}")
    # Handle wikipedia links [[Big theorem]]s also.
    (title, _, suf) = wiki_links[0].removeprefix("[[").partition("]]")
    if suf == "s":
        title += "s"
    if "|" in title:
        title = title.partition("|")[2]
    return title

def _parse_title(entry: TheoremEntry) -> str:
    return _parse_title_inner(entry.wikipedia_links)


def _write_entry(entry: TheoremEntry) -> str:
    inner = {"title": _parse_title(entry)}
    form = entry.formalisations[ProofAssistant.Lean]
    if form:
        # If there are several formalisations, we prioritise mathlib and stdlib
        # formalisations over external projects.
        # If there are still several, we pick the first in the theorem file.
        stdlib_formalisations = [f for f in form if f.library == Library.StandardLibrary]
        mathlib_formalisations = [f for f in form if f.library == Library.MainLibrary]
        if stdlib_formalisations:
            first = stdlib_formalisations[0]
            # if first.identifiers is not None:
            #     if len(first.identifiers) == 1:
            #         inner["decl"] = first.identifiers[0]
            #     else:
            #         inner["decls"] = first.identifiers
        elif mathlib_formalisations:
            first = mathlib_formalisations[0]
            # if first.identifiers is not None:
            #     if len(first.identifiers) == 1:
            #         inner["decl"] = first.identifiers[0]
            #     else:
            #         inner["decls"] = first.identifiers
        else:
            first = form[0]
            assert first.library == Library.External  # internal consistency check
            inner["url"] = first.url
            # We consciously write out the identifiers of the external theorems,
            # so they can be added upstream. Since we use a different key from the 'main library'
            # case, tooling can distinguish these just fine.
            # inner["identifiers"] = first.identifiers
        if first.authors:
            # XXX: this is inconsistent with 100.yaml
            # the former uses 'author' always; the 1000+ theorems project always uses 'authors'
            inner["author"] = " and ".join(first.authors)
        # Add additional metadata, so no information is lost in the generated yaml file.
        if first.date:
            inner['date'] = first.date
        if first.comment:
            inner['comment'] = first.comment
    key = entry.wikidata + (entry.id_suffix or "")
    res = {key: inner}
    return yaml.dump(res, sort_keys=False, allow_unicode=True)


def regenerate_from_upstream() -> None:
    # Determine the list of theorem entry files.
    theorem_entry_files = []
    with os.scandir('_thm') as entries:
        theorem_entry_files = [entry.name for entry in entries if entry.is_file()]
    # Parse each entry file into a theorem entry.
    theorems: List[TheoremEntry] = []
    for file in theorem_entry_files:
        with open(os.path.join('_thm', file), "r") as f:
            entry = _parse_theorem_entry(f.readlines())
            if entry:
                theorems.append(entry)
    # Sort alphabetically according to wikidata ID.
    # FUTURE: also use MSC classification?
    # Write out a new yaml file for this, again.
    with open("generated-1000.yaml", "w") as f:
        f.write("\n".join([_write_entry(thm) for thm in sorted(theorems, key=lambda t: t.wikidata)]))


# todo: update this!
def regenerate_upstream_from_yaml(dest_dir: str) -> None:
    with open(os.path.join("docs", "1000.yaml"), "r") as f:
        data_1000_yaml = yaml.safe_load(f)
    for id_with_suffix, entry in data_1000_yaml.items():
        has_formalisation = "decl" in entry or "decls" in entry or "identifiers" in entry
        # For each downstream declaration, read in the "upstream" yaml file and compare with the
        # downstream result.
        with open(os.path.join(dest_dir, f"{id_with_suffix}.md"), 'r') as f:
            contents = f.readlines()
            upstream_data = yaml.safe_load("".join(contents[1:-1]))
            upstream_lean_entry = _parse_theorem_entry(contents)
        original_lean = []
        if upstream_lean_entry:
            original_lean = upstream_lean_entry.formalisations[ProofAssistant.Lean]

        if original_lean and not has_formalisation:
            print(f"update: Lean formalisation of {id_with_suffix} is noted upstream, but not downstream!")
        elif original_lean and has_formalisation:
            # FUTURE: compare the formalisation entries; not done right now
            pass
        elif has_formalisation and not original_lean:
            print(f"update: found a new formalisation of {id_with_suffix} in 1000.yaml, "
              "trying to update upstream file now")
            # Augment the original file with information about the Lean formalisation.
            decl = [entry.get("decl")] or entry.get("decls")
            inner = {"status": "formalized"}
            if decl:
                # XXX: we assume no items came from the standard library...
                inner["library"] = "M"
                # We link an URL that "auto-fixes" itself: have doc-gen search for the declaration.
                # As we know it exists, that will work fine :-)
                inner["identifiers"] = decl
                decl = f"https://leanprover-community.github.io/mathlib4_docs/find/?pattern={decl[0]}#doc"
            else:
                inner["library"] = "X"
                inner["url"] = entry["url"]
                inner["identifiers"] = entry["identifiers"]
            if "author" in entry:
                inner["authors"] = entry["author"].split(" and ")
            if "date" in entry:
                inner["date"] = entry["date"]
            upstream_data["lean"] = [inner]
            # Human-readable theorem title from the upstream file.
            # We're not preserving (for now) if this was a section or sub-section.
            # XXX: the generated formatting is not exactly the same, because yaml.dump...
            # `ruamel` seems to be better here... for now, we decide to not care
            title = _parse_title_inner(upstream_data["wikipedia_links"])
            with open(os.path.join(dest_dir, f"{id_with_suffix}.md"), 'w') as f:
                yamls = yaml.dump(upstream_data, indent=2, sort_keys=False)
                f.write(f"---\n# {title}\n\n{yamls}\n---")


if __name__ == "__main__":
    import sys

    regenerate_from_upstream()
    # regenerate_upstream_from_yaml("../1000-plus.github.io/_thm")