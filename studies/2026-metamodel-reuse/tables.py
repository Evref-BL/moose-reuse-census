"""The LaTeX tables of the paper, built from the census of this study.

- `remote-entity-summary.tex`: Table 1, one row per metamodel of `table-layout.tsv`.
- `reusable-traits.tex`: Table 2, the FamixT traits of `trait-descriptions.tsv`.
- `famixt-traits.tex`, `fastt-traits.tex`: Tables A1 and A2, every trait of FamixT and FASTT.
"""
import csv

from census.report import KINDS, PLUMBING_TRAITS, Census


def tex(value):
    return value.replace("_", r"\_").replace("&", r"\&")


def summary_table(census, layout, path):
    """One row per listed metamodel, in file order, with a subtotal after each group.

    Subtotals and the total add up the occurrences, but take the union of the distinct targets:
    a trait reused by several metamodels of a group is one distinct trait."""
    metamodels = census.metamodels()
    listed = {entry["metamodel"] for entry in layout}
    unknown = sorted(listed - metamodels.keys())
    if unknown:
        raise SystemExit(f"table-layout.tsv lists unmeasured metamodels: {', '.join(unknown)}")
    # A metamodel that reuses something but is not in the layout would silently miss the table.
    unlisted = sorted(name for name, metamodel in metamodels.items()
                      if name not in listed and any(total for total, _ in metamodel.reuse))
    if unlisted:
        print(f"warning: metamodels with reuse missing from table-layout.tsv: {', '.join(unlisted)}")

    def row(label, entities, counts, style=""):
        """A table row. Each reuse kind takes two columns, both left empty when there is none."""
        wrap = (lambda text: f"\\{style}{{{text}}}") if style else str
        cells = [wrap(entities)]
        for total, distinct in counts:
            cells += [wrap(total), wrap(f"({len(distinct)})")] if total else ["", ""]
        return " & ".join([wrap(label), *cells])

    def add(into, counts):
        for index, (total, distinct) in enumerate(counts):
            into[index] = into[index][0] + total, into[index][1] | distinct

    with path.open("w") as stream:
        stream.write("\\begin{tabular}{lrr@{ }lr@{ }lr@{ }l}\n\\toprule\n")
        stream.write(" & Entities & \\multicolumn{2}{c}{Inherit.} & \\multicolumn{2}{c}{Trait uses}"
                     " & \\multicolumn{2}{c}{Exten.} \\\\\n")
        stream.write("\\Mm & & \\multicolumn{2}{c}{(uniq)} & \\multicolumn{2}{c}{(uniq)}"
                     " & \\multicolumn{2}{c}{(uniq)} \\\\\n\\midrule\n")
        grand_entities, grand = 0, [(0, set()) for _ in KINDS]
        group_entities, group = 0, [(0, set()) for _ in KINDS]
        for index, entry in enumerate(layout):
            metamodel = metamodels[entry["metamodel"]]
            stream.write(row(tex(entry.get("label") or entry["metamodel"]), metamodel.declared, metamodel.reuse) + " \\\\\n")
            group_entities += metamodel.declared
            grand_entities += metamodel.declared
            add(group, metamodel.reuse)
            add(grand, metamodel.reuse)
            if index + 1 == len(layout) or layout[index + 1]["group"] != entry["group"]:
                stream.write("\\cmidrule(l){2-8}\n")
                stream.write(row(f"Subtotal {tex(entry['group'])}", group_entities, group, "textit"))
                stream.write(" \\\\[1ex]\n\n" if index + 1 < len(layout) else " \\\\\n")
                group_entities, group = 0, [(0, set()) for _ in KINDS]
        stream.write("\\midrule\n" + row("Total", grand_entities, grand, "textbf") + " \\\\\n")
        stream.write("\\bottomrule\n\\end{tabular}\n")


def described_traits_table(users, descriptions, path):
    """The described traits, most reused first, ties keeping the order of the file."""
    missing = [name for name, _ in descriptions if not users.get(name)]
    if missing:
        print(f"warning: described traits with no measured reuse: {', '.join(missing)}")
    rows = sorted(descriptions, key=lambda pair: -len(users.get(pair[0], ())))
    with path.open("w") as stream:
        stream.write("\\begin{tabular}{llr}\n\\toprule\n")
        stream.write("Trait & What it models & Reuses \\\\\n\\midrule\n")
        for name, description in rows:
            stream.write(f"\\ct{{{tex(name)}}} & {tex(description)} & {len(users.get(name, ()))} \\\\\n")
        stream.write("\\bottomrule\n\\end{tabular}\n")


def all_traits_table(names, users, path, columns=3):
    """Every trait in alphabetical order, filled column by column. Plumbing gets no count."""
    height = -(-len(names) // columns)
    with path.open("w") as stream:
        stream.write("\\begin{tabular}{@{}" + "lr@{\\hspace{1em}}" * (columns - 1) + "lr@{}}\n\\toprule\n")
        stream.write(" & ".join(["Trait & \\#"] * columns) + " \\\\\n\\midrule\n")
        for index in range(height):
            cells = []
            for column in range(columns):
                position = column * height + index
                if position < len(names):
                    name = names[position]
                    count = "--" if name in PLUMBING_TRAITS else len(users.get(name, ()))
                    cells += [f"\\ct{{{tex(name)}}}", str(count)]
                else:
                    cells += ["", ""]
            stream.write(" & ".join(cells) + " \\\\\n")
        stream.write("\\bottomrule\n\\end{tabular}\n")


def build(study):
    census = Census(study)
    tables = study.output / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    with (study.root / "table-layout.tsv").open(newline="") as stream:
        layout = list(csv.DictReader(stream, delimiter="\t"))
    summary_table(census, layout, tables / "remote-entity-summary.tex")

    with (study.root / "trait-descriptions.tsv").open() as stream:
        descriptions = [line.rstrip("\n").split("\t", 1) for line in stream if not line.startswith("trait\t")]
    described_traits_table(census.trait_users("Famix-Traits"), descriptions, tables / "reusable-traits.tex")

    for package, filename in (("Famix-Traits", "famixt-traits.tex"), ("FAST-Core-Model", "fastt-traits.tex")):
        names = census.traits_of(package)
        users = census.trait_users(package)
        unlisted = sorted(set(users) - set(names))
        if unlisted:
            print(f"warning: reused {package} traits missing from its latest image: {', '.join(unlisted)}")
        all_traits_table(names, users, tables / filename)
