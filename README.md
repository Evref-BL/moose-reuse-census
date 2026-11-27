# moose-reuse-census

Measures how Fame metamodels reuse each other in [Moose](https://modularmoose.org).
Point it at a list of Moose projects, and it loads each one into a Moose image, finds its
metamodels, and counts what each one takes from the others:

- **inheritance**: a class whose superclass belongs to another metamodel;
- **trait use**: a class or trait using a trait of another metamodel;
- **property extension**: a property the metamodel adds to an entity of another metamodel.

It reports the occurrences and the distinct targets of each kind, per metamodel and per pair
of metamodels, and draws the reuse relationships as a graph.

## Requirements

- Python 3.8 or newer. The scripts use only its standard library.
- Internet access on the first run, to download the Moose images and, if needed, a Pharo VM.
  No Pharo installation is needed. A local one is used when found.
- Graphviz `dot`, optional, to render the diagrams as PDF. The DOT sources are written anyway.

## Usage

```sh
python3 -m census run studies/2026-metamodel-reuse
```

`run` measures every target of the study, then builds the report. To measure only some
targets, add `--only ID ...`. To rebuild the report from the data already measured:

```sh
python3 -m census report studies/2026-metamodel-reuse
```

Images and VMs are kept in `.cache`, one image per recipe, so a target whose recipe did not
change reuses its image on the next run. `--cache DIR` puts them elsewhere.

The VM is taken from `PHARO_<version>_VM`, then `~/Documents/Pharo/vms`, then `Pharo` on the
PATH, and is otherwise downloaded. `PHARO_<version>_IMAGE` measures in an image of your own
instead of a downloaded one.

## Studies

A study is a folder. Only `targets.tsv` is required.

| File | Content |
|---|---|
| `targets.tsv` | One target per line: an id, a Moose version (10 to 13), and a one-line Smalltalk recipe that loads the project. |
| `*.st` | Recipe parts shared by several targets. A recipe starting with `@file.st` includes that file first. |
| `names.tsv` | `package`, `name`: the name shown for a Fame package when the default rule does not fit. The rule drops a trailing `-Entities`, `-Traits` or `-Model`. |
| `entity-packages.tsv` | `package`, `holder`: a Fame package whose classes and traits the generator put in another package. |
| `labels.tsv` | `id`, `label`: the name of a target in the diagrams. |
| `tables.py` | Optional. Its `build(study)` runs after the report, to make the study's own tables from the `Census` class of `census/report.py`. |

A recipe loads the project with Metacello and should pin every version, so the study can be
measured again. By default the metamodels measured are the model classes the recipe loaded.
A recipe can choose them instead:

```smalltalk
Smalltalk globals at: #FameRemoteEntityAnalysisModels put: #(FamixJavaModel).
```

The metamodels these depend on are measured too, so every reuse target is in the data.

## Output

Everything goes to the study's `output` folder.

| Path | Content |
|---|---|
| `raw/moose-<version>-<id>.csv` | The records of one target, as the analyzer wrote them. |
| `data/aggregate/` | The records of all targets, one file per kind of record. |
| `data/derived/metamodels.csv` | One row per metamodel at the latest Moose version measuring it: its entities, and the occurrences and distinct targets of each kind of reuse. |
| `data/derived/package-reuse-relationships.csv` | The reuse between each pair of metamodels. |
| `data/derived/trait-users.csv` | Every trait of every reused metamodel, with the metamodels using it directly. |
| `data/derived/node-behaviors.csv` | The classes and traits each Fame package declares. |
| `diagrams/` | The reuse relationships, for all metamodels at once and per target. |

Trait uses exclude the plumbing every generated metamodel gets: `TEntityCreator` and the
`Moose-Query` traits. Inheritance from the Moose platform base (`MooseEntity`, `MooseModel`)
is not counted either.

## Layout

- `analyzer/`: the Pharo side. `run-target.st` loads a recipe in an image and calls
  `measure.st`, which writes the records of each metamodel.
- `census/`: the Python side, running the targets and building the report.
- `studies/`: one folder per study.
- `tests/`: `python3 -m unittest discover -s tests -t .`
