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

Usage: run
  python3 sync_mathlib_data.py --downstream
to regenerate a 1000-theorems-data.yaml file, and
  python3 sync_mathlib_data.py --upstream <input_file.yaml>
to update the contents of this repository from the file input_file.yaml.
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
    def tryFrom_str(input: str):
        return {
            "formalized": FormalizationStatus.FullProof,
            "statement": FormalizationStatus.Statement,
        }.get(input)
    @staticmethod
    def as_str(entry) -> str:
        return {
            FormalizationStatus.FullProof: "formalized",
            FormalizationStatus.Statement: "statement",
        }[entry]


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
    def tryFrom_str(input: str):
        return {
            "S": Library.StandardLibrary,
            "L": Library.MainLibrary,
            "X": Library.External,
        }.get(input)
    @staticmethod
    def as_str(entry) -> str:
        return {
            Library.StandardLibrary: "S",
            Library.MainLibrary: "L",
            Library.External: "X"
        }[entry]


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
def parse_formalization_entry(entry: FormalizationEntryRaw) -> FormalisationEntry | None:
    status = FormalizationStatus.tryFrom_str(entry['status'])
    library = Library.tryFrom_str(entry['library'])
    if status is None or library is None:
        return None
    return FormalisationEntry(
        status, library, entry['url'], entry.get('authors'), entry.get('date'), entry.get('comment'),
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


# Write a theorem entry for a downstream file.
def _write_entry_for_downstream(entry: TheoremEntry) -> str:
    inner = {"title": _parse_title(entry)}
    key = entry.wikidata + (entry.id_suffix or "")
    form = entry.formalisations[ProofAssistant.Lean]
    if form:
        # We process the data fields in README order, for prettier output.
        # If there are several formalisations, we prioritise mathlib and stdlib
        # formalisations over external projects.
        # If there are still several, we pick the first in the theorem file.
        if len(form) > 1:
            print(f"warning: there are several formalisations for theorem {key}, skipping all but the first one")
        stdlib_formalisations = [f for f in form if f.library == Library.StandardLibrary]
        mathlib_formalisations = [f for f in form if f.library == Library.MainLibrary]
        if stdlib_formalisations:
            first = stdlib_formalisations[0]
            # The same comment about declaration names applies.
            if first.status == FormalizationStatus.FullProof:
                inner["url"] = first.url
        elif mathlib_formalisations:
            first = mathlib_formalisations[0]
            # URLs specified are of the form https://leanprover-community.github.io/1000.html#Q11518.
            # We cannot easily parse the declaration from that, so omit it.
            # (Could one add a comment like "# decl: cannot be inserted automatically" instead?)

            # Future: one could try to hackily parse the code at
            # https://leanprover-community.github.io/1000.html#Q11518;
            # a "docs" link points to a URL like
            # https://leanprover-community.github.io/mathlib4_docs/Mathlib/Geometry/Euclidean/Angle/Unoriented/RightAngle.html#EuclideanGeometry.dist_sq_eq_dist_sq_add_dist_sq_iff_angle_eq_pi_div_two,
            # in which "EuclideanGeometry.dist_sq_eq_dist_sq_add_dist_sq_iff_angle_eq_pi_div_two"
            # (the part after a #) is the declaration name.
            # For several declarations, one would parse all declaration names.
        else:
            first = form[0]
            assert first.library == Library.External  # internal consistency check
            # We don't mentional external formalisations of just the statement in mathlib's file.
            if first.status == FormalizationStatus.FullProof:
                inner["url"] = first.url
        if first.authors:
            # NB: this is different from the 100 theorems project
            # 100 theorems names the field 'author'; this project uses 'authors'
            inner["authors"] = " and ".join(first.authors)
        # Add additional metadata, so no information is lost in the generated yaml file.
        if first.date:
            inner['date'] = first.date
        if first.comment:
            inner['comment'] = first.comment
    return yaml.dump({key: inner}, sort_keys=False, allow_unicode=True)


# Generate a file 1000.yaml from this repository's _thm folder.
def generate_downstream_file() -> None:
    # Determine the list of theorem entry files.
    theorem_entry_files = []
    with os.scandir('_thm') as entries:
        theorem_entry_files = [entry.name for entry in entries if entry.is_file()]
    # Parse each entry file into a theorem entry.
    theorems: List[TheoremEntry] = []
    for file in theorem_entry_files:
        with open(os.path.join('_thm', file), "r") as f:
            entry = _parse_theorem_entry(f.readlines())
            if entry is None:
                print(f"warning: file _thm/{file} contains invalid input, ignoring", file=sys.stderr)
                continue
            theorems.append(entry)
    # Sort alphabetically according to wikidata ID.
    # FUTURE: also use MSC classification?
    # Write out a new yaml file for this, again.
    with open("generated-1000.yaml", "w") as f:
        f.write("\n".join([_write_entry_for_downstream(thm) for thm in sorted(theorems, key=lambda t: t.wikidata)]))
    print("Careful: the generated file does not contain declaration names. "
        "Be careful with manually merging the updated file!")


# Update this repository's data about Lean formalisations with the contents
# in a yaml file |input_file|.
def update_data_from_downstream_yaml(input_file: str) -> None:
    with open(input_file, "r") as f:
        downstream_yaml_data = yaml.safe_load(f)
    # TODO: update this function!

    # We go over each entry of the yaml file: each corresponds to one file in _thm.
    for id_with_suffix, entry in downstream_yaml_data.items():
        # Newly created entry, based on the downstream entries.
        new_entry = {}
        # This means the statement (and only the statement) is formalised, within mathlib.
        (status, library) = (None, None)
        new_entry_typed = None
        if "statement" in entry:
            (status, library) = (FormalizationStatus.Statement, Library.MainLibrary)
            new_entry["status"] = "statement"
            new_entry["library"] = "L"
        # This means the full proof is formalised within mathlib.
        # mathlib validates that at most one of has_statement and has_formalisation holds.
        elif "decl" in entry or "decls" in entry:
            (status, library) = (FormalizationStatus.FullProof, Library.MainLibrary)
            new_entry["status"] = "formalized"
            new_entry["library"] = "L"
        # A URL field means an external formalisation exists.
        elif "url" in entry:
            (status, library) = (FormalizationStatus.FullProof, Library.External)
            new_entry["status"] = "formalized"
            new_entry["library"] = "X"
        if new_entry:
            new_entry["url"] = f"https://leanprover-community.github.io/1000.html#{id_with_suffix}"
        # Pass through any author, date information or comments.
        if "authors" in entry:
            new_entry["authors"] = entry["authors"]
        if "date" in entry:
            new_entry["date"] = entry["date"]
        if "comment" in entry:
            new_entry["comment"] = entry["comment"]
        authors = entry.get("authors")
        if authors:
            authors = authors.split(" and ")
        if status:
            new_entry_typed = FormalisationEntry(status, library, entry.get("url"), authors, entry.get("date"), entry.get("comment"))

        # Read the _thm data file and compare data on Lean formalisations.
        upstream_entry = None
        with open(os.path.join("_thm", f"{id_with_suffix}.md"), 'r') as f:
            contents = f.readlines()
            # The full contents of the upstream markdown file: we preserve anything
            # which is not the Lean formalisation.
            upstream_data = yaml.safe_load("".join(contents[1:-1]))
            upstream_lean_entry = _parse_theorem_entry(contents)
        upstream_entry = upstream_lean_entry.formalisations[ProofAssistant.Lean]

        overwrite = False
        if new_entry_typed and (not upstream_entry):
            print(f"update: found a new Lean formalisation of {id_with_suffix} in 1000.yaml, "
              "trying to update upstream file now")
            overwrite = True
        elif (new_entry_typed is None) and upstream_entry:
            print(f"update: Lean formalisation of {id_with_suffix} is noted upstream, but not downstream!")
        elif new_entry_typed and upstream_entry:
            if len(upstream_entry) > 1:
                print(f"theorem {id_with_suffix} has one Lean formalization downstream, but {len(upstream_entry)} upstream!")
                print("skipping data updates: please do so manually")
            else:
                # print(f"comparing formalisations for theorem {id_with_suffix}...")
                if new_entry_typed != upstream_entry[0]:
                    def compare(downstream, upstream, field: str) -> None:
                        if downstream != upstream:
                            print(f"entries differ in field {field}: downstream declaration has value\n  {downstream}\n while upstream has\n  {upstream}")
                    print("formalizations entries are different!")
                    compare(new_entry_typed.status, upstream_entry[0].status, "status")
                    compare(new_entry_typed.library, upstream_entry[0].library, "library")
                    compare(new_entry_typed.url, upstream_entry[0].url, "URL")
                    compare(new_entry_typed.authors, upstream_entry[0].authors, "authors")
                    compare(new_entry_typed.date, upstream_entry[0].date, "date")
                    compare(new_entry_typed.comment, upstream_entry[0].comment, "comment")
                    print(f"overwriting file _thms/{id_with_suffix}.md with downstream data")
                    overwrite = True
                else:
                    print(f"info: formalizations for theorem {id_with_suffix} have the same data")

        if overwrite:
            inner = {
                "status": FormalizationStatus.as_str(new_entry_typed.status),
                "library": Library.as_str(new_entry_typed.library),
                # We conciously choose such URLs not containing declaration names,
                # as these are more stable.
                "url": f"https://leanprover-community.github.io/1000.html#{id_with_suffix}",
            }
            if new_entry_typed.authors:
                inner["authors"] = new_entry_typed.authors
            if new_entry_typed.date:
                inner["date"] = new_entry_typed.date
            if new_entry_typed.comment:
                inner["comment"] = new_entry_typed.comment
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
    if len(sys.argv) < 2:
        print("Please specify what you want to do: pass the --downstream option to regenerate a file 1000.yaml or "
            "pass --upstream <filename.yaml> to update the theorem data files in this repository "
            "from a downstream .yaml file.", file=sys.stderr)
        sys.exit(1)
    match sys.argv[1]:
        case "--downstream":
            generate_downstream_file()
        case "--upstream":
            if len(sys.argv) == 2:
                print("error: please specify the input file to read from: "
                    "usage: python3 sync_mathlib_data.py --upstream <filename.yaml>", file=sys.stderr)
                sys.exit(1)
            update_data_from_downstream_yaml(sys.argv[2])
        case unexpected:
            print(f"Unexpected argument '{unexpected}': usage is\n  python3 sync_mathlib_data.py --downstream\n"
            "to regenerate a downstream file 1000.yaml or\n  python3 sync_mathlib_data.py --upstream <inputfile.yaml>\n"
            "to update the theorem data files in this repository from a downstream .yaml file.", file=sys.stderr)
            sys.exit(1)