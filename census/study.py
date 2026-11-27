"""Where a study keeps its inputs and outputs."""
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parent.parent


class Study:
    """A folder holding `targets.tsv`, its optional settings, and an `output` folder.

    Optional settings, all tab-separated with a header line:
    - `names.tsv` (package, name): the name shown for a Fame package, when the
      default rule (drop `-Entities`, `-Traits` or `-Model`) does not fit.
    - `entity-packages.tsv` (package, holder): a declared Fame package whose classes
      and traits the generator put in another package.
    - `labels.tsv` (id, label): the name of a target in the diagrams.
    """

    def __init__(self, root, cache=None):
        self.root = Path(root).resolve()
        if not (self.root / "targets.tsv").is_file():
            raise SystemExit(f"Not a study folder, it has no targets.tsv: {self.root}")
        self.cache = Path(cache).resolve() if cache else REPOSITORY / ".cache"

    @property
    def targets_file(self):
        return self.root / "targets.tsv"

    @property
    def output(self):
        return self.root / "output"

    @property
    def raw(self):
        return self.output / "raw"

    @property
    def aggregate(self):
        return self.output / "data" / "aggregate"

    @property
    def derived(self):
        return self.output / "data" / "derived"

    @property
    def diagrams(self):
        return self.output / "diagrams"

    def settings(self, name):
        """The rows of an optional two-column settings file, as a dictionary."""
        path = self.root / name
        if not path.is_file():
            return {}
        with path.open() as stream:
            rows = [line.rstrip("\n").split("\t", 1) for line in stream if line.strip()]
        return dict(row for row in rows[1:] if len(row) == 2)
