# 1000 Plus Theorems

The spiritual successor of Freek's list of [100 theorems](https://www.cs.ru.nl/~freek/100/).
Now with more than 1000 theorems!

The entries of this list are extracted from Wikipedia's [List of Theorems](https://en.wikipedia.org/wiki/List_of_theorems).
We do not accept entries that are not part of that list.
We will (semiregularly) update the list to match the Wikipedia list. Please do not vandalize Wikipedia to try to add nonsensical entries to the list.

## Contributing

We welcome contributions! Please open a PR with additions or corrections!

## File format

The files should start and end with a row containing exactly `---` and should contain Yaml records with the fields described below.
For an example of a file with a formalization entry, see [Q208416.md](_thm/Q208416.md).

* `wikidata`: Wikidata identifier for this theorem (or concept related to the theorem). Valid identifiers start with the latter Q followed by a number.
* `id_suffix` (optional): disambiguates an entry when two theorems have the same wikidata identifier. `X` means an extra theorem on a Wikipedia page (e.g. a generalization or special case), `A`/`B`/... means different theorems on one Wikipedia page that doesn't have a "main" theorem.
* `msc_classification`: Our best guess of the [MSC-classification](https://msc2020.org/) of this theorem. Please PR a better suggestion!
* `wikipedia_links`: list of exact wikipedia links to the relevant page(s). Each link has the format `[[Page name]]` or `[[Wikilink|Displayed name]]`.
* Then zero or more entries for the formalizations in any of the supported proof assistants (`isabelle`, `hol_light`, `rocq` (formerly `coq`), `lean`, `metamath`, `mizar`). Several formalization entries for one assistant are allowed.

For each formalization in each proof assistant, we record the following information

* `status`: `formalized` (the proof is formalized), `statement` (just the statement is)
* `library`: in what library does the formalization appear
  - "S": standard library
  - "L": main (biggest) mathematical library (afp, hol light outside standard library, mathcomp, mathlib, mml, set.mm)
  - "X": external to the main or standard library (e.g. a dedicated repository)
* `url`: a URL pointing to the formalization
* `authors`:  list of authors of the formalisation; optional
* `date`:  (optional). Format: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`
* `comment`: (optional)

