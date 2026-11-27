# 2026-metamodel-reuse

The census of the paper *Metamodel Reuse: A Decade of Industrial Validation*:
43 metamodels maintained in Moose, measured in Moose 11, 12 and 13.

```sh
python3 -m census run studies/2026-metamodel-reuse
```

`tables.py` writes the paper's tables to `output/tables`:

| File | Paper |
|---|---|
| `remote-entity-summary.tex` | Table 1, the metamodels of the corpus and their reuse. Its rows, groups and labels come from `table-layout.tsv`. |
| `reusable-traits.tex` | Table 2, the FamixT traits of `trait-descriptions.tsv`. |
| `famixt-traits.tex`, `fastt-traits.tex` | Tables A1 and A2, every trait of FamixT and FASTT. |

Notes on the corpus:

- A metamodel measured under several Moose versions is one row, taken at its latest version.
- Project versions are pinned in `targets.tsv`. The Moose 13 image is the continuous release,
  so a new download may change what it ships.
- Pins differ where a project needs an older dependency, so a shared package can report
  different sizes. The Fortran targets pin FAST at `5bb618a6`, whose `FAST-Core-Model` has
  29 traits, against 35 at the `32eed64d` the others use.
- Famix-Angular declares `Famix-Angular-Entities`, which stays empty, while its classes and
  traits are generated into `FamixAngular`. `entity-packages.tsv` counts them from there.
- Famix-Angular and Carrefour-TypeScript, measured in Moose 12, reuse `FamixTypeScript`,
  the former name of `Famix-TypeScript-Entities`. The report warns that they do not declare
  that package. The warning is expected.
- In the paper, Table 1 counts the classes and traits each metamodel declares itself, and its
  subtotals count a target shared by several metamodels of a group once.
