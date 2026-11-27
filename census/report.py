"""Derive the census from a study's aggregate files: CSV data and reuse diagrams.

The `Census` class holds the computed quantities, so a study can build its own tables
from them, as `studies/2026-metamodel-reuse/tables.py` does for its paper.
"""
import csv
import html
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass


# Every metamodel that reuses another gets TEntityCreator on its generated model class, and the
# Moose-Query traits come with the query engine. Both land on a metamodel whatever it does with
# the reused concepts, so neither says anything about specialization.
PLUMBING_TRAITS = {"TEntityCreator"}
PLUMBING_PACKAGES = {"Moose-Query"}

# The three kinds of reuse: the metric counting it and the raw record listing it.
KINDS = (("remoteInheritances", "remoteInheritance"),
         ("remoteTraitUsages", "remoteTraitUse"),
         ("remotePropertyExtensions", "remotePropertyExtension"))
KIND_NAMES = {
    "remoteTraitUse": "traits",
    "remoteInheritance": "inherits",
    "remotePropertyExtension": "extensions",
}


def is_plumbing(remote_package, remote_entity):
    return remote_entity in PLUMBING_TRAITS or remote_package in PLUMBING_PACKAGES


def moose_version(source):
    return source.split("-", 2)[1]


def project_id(source):
    return source.split("-", 2)[2]


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


@dataclass
class Metamodel:
    """One metamodel at the latest Moose version that measured it."""
    name: str
    model: str
    package: str
    source: str
    entities: int
    traits: int
    # Per kind, in KINDS order: the number of occurrences and the set of distinct targets.
    reuse: list

    @property
    def declared(self):
        """Classes and traits the metamodel declares itself."""
        return self.entities + self.traits

    def count(self, kind):
        return self.reuse[[record for _, record in KINDS].index(kind)]


class Census:
    def __init__(self, study):
        self.study = study
        self.names = study.settings("names.tsv")
        entity_packages = study.settings("entity-packages.tsv")
        aggregate = study.aggregate
        metric_rows = read_rows(aggregate / "metrics.csv")
        behavior_rows = read_rows(aggregate / "package-behaviors.csv")
        self.reuse_rows = read_rows(aggregate / "family-uses.csv") + read_rows(aggregate / "relationship-extensions.csv")
        if not metric_rows:
            raise SystemExit(f"No aggregate data in {aggregate}: run the study first")

        self.metrics = defaultdict(dict)
        for row in metric_rows:
            self.metrics[row["source"], row["modelClass"], row["declaredPackage"]][row["metric"]] = row["value"]

        self.behaviors_by_source = defaultdict(dict)
        for row in behavior_rows:
            self.behaviors_by_source[row["source"], row["declaredPackage"]][row["metric"]] = int(row["value"])
        for (source, package) in list(self.behaviors_by_source):
            holder = entity_packages.get(package)
            if holder and (source, holder) in self.behaviors_by_source:
                self.behaviors_by_source[source, package] = dict(self.behaviors_by_source[source, holder])

        # The latest image measuring each package.
        self.latest_behaviors = {}
        for (source, package), behavior in self.behaviors_by_source.items():
            candidate = int(moose_version(source)), source
            if package not in self.latest_behaviors or candidate > self.latest_behaviors[package][0]:
                self.latest_behaviors[package] = candidate, {
                    "entities": behavior.get("entities", 0),
                    "traits": behavior.get("traits", 0),
                }

        self.edges = Counter()
        self.distinct_trait_uses = defaultdict(set)
        self.reusing_behaviors = defaultdict(set)
        self.distinct_remote_parents = defaultdict(set)
        self.extended_remote_entities = defaultdict(set)
        # The same three quantities per metamodel rather than per package pair, so a table can
        # report occurrences and distinct targets side by side.
        self.distinct_by_package = {record: defaultdict(set) for _, record in KINDS}
        self.undeclared_remotes = Counter()
        self.specialized_packages = defaultdict(set)
        # Trait uses excluding plumbing: what the metamodel actually reuses.
        self.specializing_uses = Counter()
        self.extended_packages = defaultdict(set)
        for row in self.reuse_rows:
            source, local, remote, kind = row["source"], row["declaredPackage"], row["remotePackage"], row["record"]
            self.edges[(source, local, remote, kind)] += 1
            if not (kind == "remoteTraitUse" and is_plumbing(remote, row["remoteEntity"])):
                self.distinct_by_package[kind][source, local].add((remote, row["remoteEntity"]))
            declared = set(filter(None, (row.get("declaredSubmetamodelPackages") or "").split("|")))
            if declared and remote and remote not in declared:
                self.undeclared_remotes[(source, local, remote, kind)] += 1
            if kind == "remoteTraitUse":
                self.distinct_trait_uses[source, local, remote].add(row["remoteEntity"])
                self.reusing_behaviors[source, local, remote].add(row["localEntity"])
                if not is_plumbing(remote, row["remoteEntity"]):
                    self.specialized_packages[source, local].add(remote)
                    self.specializing_uses[source, local] += 1
            elif kind == "remoteInheritance":
                self.distinct_remote_parents[source, local, remote].add(row["remoteEntity"])
                self.specialized_packages[source, local].add(remote)
            elif kind == "remotePropertyExtension":
                self.extended_remote_entities[source, local, remote].add(row["remoteEntity"])
                self.extended_packages[source, local].add(remote)

        # The latest source of each model class, among those that reuse something.
        self.latest_source = {}
        for row in self.reuse_rows:
            candidate = int(moose_version(row["source"])), row["source"]
            if row["modelClass"] not in self.latest_source or candidate > self.latest_source[row["modelClass"]]:
                self.latest_source[row["modelClass"]] = candidate

        self.package_traits = defaultdict(set)
        for row in read_rows(aggregate / "package-traits.csv"):
            self.package_traits[row["source"], row["declaredPackage"]].add(row["localEntity"])

    def model_name(self, package):
        """A concise metamodel name for a Fame package."""
        if package in self.names:
            return self.names[package]
        for suffix in ("-Entities", "-Traits", "-Model"):
            if package.endswith(suffix):
                package = package[: -len(suffix)]
                break
        return package.replace("-Model-", "-")

    def behavior(self, package, source=None):
        """Classes and traits a package declares, in a given source or at its latest one."""
        if source and (source, package) in self.behaviors_by_source:
            return self.behaviors_by_source[source, package]
        return self.latest_behaviors.get(package, (None, {"entities": 0, "traits": 0}))[1]

    def metamodels(self):
        """Every measured metamodel at its latest Moose version, keyed by name.

        Keyed on the model class rather than the package: a metamodel keeps its model class
        across Moose versions, while its Fame package may be renamed."""
        latest = {}
        for (source, model, package), values in sorted(self.metrics.items()):
            candidate = int(moose_version(source)), source
            if model not in latest or candidate > latest[model][0]:
                latest[model] = candidate, package, values
        result = {}
        for model, ((_, source), package, values) in latest.items():
            behavior = self.latest_behaviors[package][1]
            reuse = [((self.specializing_uses[source, package] if record == "remoteTraitUse"
                       else int(values.get(metric, 0) or 0)),
                      self.distinct_by_package[record][source, package])
                     for metric, record in KINDS]
            name = self.model_name(package)
            result[name] = Metamodel(name, model, package, source, behavior["entities"], behavior["traits"], reuse)
        return result

    def trait_users(self, remote_package):
        """For each trait of a package, the metamodels that use it directly, at their latest version."""
        users = defaultdict(set)
        for row in self.reuse_rows:
            if row["record"] != "remoteTraitUse" or row["remotePackage"] != remote_package:
                continue
            if self.latest_source[row["modelClass"]][1] != row["source"]:
                continue
            users[row["remoteEntity"]].add(self.model_name(row["declaredPackage"]))
        return users

    def traits_of(self, package):
        """Every trait of a package, at the latest image that measured it."""
        (_, source), behavior = self.latest_behaviors[package]
        names = sorted(self.package_traits.get((source, package), ()), key=str.lower)
        if len(names) != behavior["traits"]:
            print(f"warning: {package} lists {len(names)} traits in {source}, expected {behavior['traits']}")
        return names


def dot_quote(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_dot(path, lines, layout="dot"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    if shutil.which(layout):
        pdf = path.parent.parent / "pdf" / path.with_suffix(".pdf").name
        pdf.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([layout, "-Tpdf", str(path), "-o", str(pdf)], check=True)


def latest_package_edges(edges):
    """Keep one latest observed relationship for each package pair and mechanism."""
    selected = {}
    for (source, local, remote, kind), count in edges.items():
        key = local, remote, kind
        candidate = int(moose_version(source)), count, source
        if key not in selected or candidate > selected[key]:
            selected[key] = candidate
    return selected


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def build(study):
    """Write the derived CSV files and the reuse diagrams of a study."""
    census = Census(study)
    labels = study.settings("labels.tsv")

    write_csv(study.derived / "node-behaviors.csv", [{
        "package": package,
        "modelName": census.model_name(package),
        "entities": behavior["entities"],
        "traits": behavior["traits"],
        "source": candidate[1],
        "mooseVersion": candidate[0],
    } for package, (candidate, behavior) in sorted(census.latest_behaviors.items())])

    metamodel_rows = []
    for metamodel in sorted(census.metamodels().values(), key=lambda each: each.name.lower()):
        (inherits, parents), (uses, traits), (extensions, extended) = metamodel.reuse
        metamodel_rows.append({
            "metamodel": metamodel.name,
            "modelClass": metamodel.model,
            "package": metamodel.package,
            "source": metamodel.source,
            "mooseVersion": moose_version(metamodel.source),
            "entities": metamodel.declared,
            "inheritances": inherits,
            "distinctParents": len(parents),
            "traitUses": uses,
            "distinctTraits": len(traits),
            "extensions": extensions,
            "distinctExtended": len(extended),
            "specializes": "yes" if inherits or uses else "no",
            "extends": "yes" if extensions else "no",
        })
    write_csv(study.derived / "metamodels.csv", metamodel_rows)

    # Every trait of every reused package, with the metamodels using it directly.
    trait_rows = []
    for package in sorted({row["remotePackage"] for row in census.reuse_rows if row["record"] == "remoteTraitUse"}):
        if package not in census.latest_behaviors:
            continue
        users = census.trait_users(package)
        for trait in census.traits_of(package):
            trait_rows.append({
                "package": package,
                "trait": trait,
                "plumbing": "yes" if is_plumbing(package, trait) else "no",
                "users": len(users.get(trait, ())),
                "usedBy": ";".join(sorted(users.get(trait, ()))),
            })
    if trait_rows:
        write_csv(study.derived / "trait-users.csv", trait_rows)

    def node_label(package, behavior=None):
        name = census.model_name(package)
        if behavior is None:
            return f'label="{dot_quote(name)}"'
        return (
            f'label=<<FONT POINT-SIZE="12">{html.escape(name)}</FONT>'
            f'<BR/><FONT POINT-SIZE="11">entities: {behavior["entities"]}</FONT>'
            f'<BR/><FONT POINT-SIZE="11">traits: {behavior["traits"]}</FONT>>'
        )

    def edge_label(kinds, sources, local, remote):
        labels_ = []
        for kind, count in sorted(kinds.items()):
            source = sources[kind]
            if kind == "remoteTraitUse":
                labels_.append(f"uses: {count}, traits: {len(census.distinct_trait_uses[source, local, remote])}")
            elif kind == "remoteInheritance":
                labels_.append(f"inherits: {count}, parents: {len(census.distinct_remote_parents[source, local, remote])}")
            elif kind == "remotePropertyExtension":
                labels_.append(f"extensions: {count}, targets: {len(census.extended_remote_entities[source, local, remote])}")
        return "; ".join(labels_)

    # One cluster per target, each showing the reuse its image measured.
    grouped = defaultdict(Counter)
    for (source, local, remote, kind), count in census.edges.items():
        grouped[(source, local, remote)][kind] = count
    project_dot = [
        "digraph reuse_by_project {",
        "  rankdir=LR;",
        "  graph [compound=true, splines=polyline];",
        "  node [shape=box];",
    ]
    project_nodes = defaultdict(dict)
    for source, local, remote in grouped:
        project_nodes[source][f"{source}-{local}"] = local
        project_nodes[source][f"{source}-{remote}"] = remote
    for index, (source, node_labels) in enumerate(sorted(project_nodes.items())):
        label = labels.get(project_id(source), project_id(source))
        project_dot.extend((
            f"  subgraph cluster_project_{index} {{",
            f'    label="{dot_quote(label)} (Moose {moose_version(source)})";',
            '    style="rounded";',
            *(f'    "{dot_quote(node_id)}" [{node_label(package, census.behavior(package, source))}];'
              for node_id, package in sorted(node_labels.items())),
            "  }",
        ))
    for (source, local, remote), kinds in sorted(grouped.items()):
        label = edge_label(kinds, {kind: source for kind in kinds}, local, remote)
        project_dot.append(
            f'  "{dot_quote(source)}-{dot_quote(local)}" -> "{dot_quote(source)}-{dot_quote(remote)}" '
            f'[label="{dot_quote(label)}"];'
        )
    project_dot.append("}")
    write_dot(study.diagrams / "dot" / "reuse-relationships-by-project.dot", project_dot)

    # All packages in one graph, each relationship taken from the latest image measuring it.
    package_edges = latest_package_edges(census.edges)
    package_rows = []
    package_dot = [
        "digraph reuse {",
        "  rankdir=LR;",
        "  graph [splines=polyline];",
        "  node [shape=box];",
    ]
    package_grouped = defaultdict(dict)
    for (local, remote, kind), (_, count, _) in package_edges.items():
        package_grouped[local, remote][kind] = count
    package_nodes = set()
    for (local, remote), kinds in sorted(package_grouped.items()):
        package_nodes.update((local, remote))
        sources = {kind: package_edges[local, remote, kind][2] for kind in kinds}
        label = edge_label(kinds, sources, local, remote)
        package_dot.append(f'  "{dot_quote(local)}" -> "{dot_quote(remote)}" [label="{dot_quote(label)}"];')
        for kind, count in kinds.items():
            source = package_edges[local, remote, kind][2]
            package_rows.append({
                "localPackage": local,
                "remotePackage": remote,
                "mechanism": KIND_NAMES[kind],
                "uses": count,
                "distinctRemoteTraits": len(census.distinct_trait_uses[source, local, remote]) if kind == "remoteTraitUse" else "",
                "reusingBehaviors": len(census.reusing_behaviors[source, local, remote]) if kind == "remoteTraitUse" else "",
                "distinctRemoteParents": len(census.distinct_remote_parents[source, local, remote]) if kind == "remoteInheritance" else "",
                "extendedRemoteEntities": len(census.extended_remote_entities[source, local, remote]) if kind == "remotePropertyExtension" else "",
                "selectedSource": source,
                "mooseVersion": moose_version(source),
            })
    for package in sorted(package_nodes):
        package_dot.append(f'  "{dot_quote(package)}" [{node_label(package, census.behavior(package))}];')
    package_dot.append("}")
    write_dot(study.diagrams / "dot" / "reuse-relationships.dot", package_dot)
    write_csv(study.derived / "package-reuse-relationships.csv",
              sorted(package_rows, key=lambda row: tuple(row.values())))

    # A reuse row pointing at a package the metamodel does not declare as a submetamodel means
    # either a gap in the declarations or a renamed package. Report rather than silently drop it.
    if census.undeclared_remotes:
        print("warning: %d reuse rows target a package that is not a declared submetamodel:"
              % sum(census.undeclared_remotes.values()))
        for (source, local, remote, kind), count in sorted(census.undeclared_remotes.items()):
            print("  %s: %s -> %s (%s) x%d" % (source, local, remote, kind, count))
    return census
