"""Command line: `python3 -m census run STUDY` or `python3 -m census report STUDY`."""
import argparse
import importlib.util
import sys

from . import report
from .run import run
from .study import Study


def study_hook(study):
    """Run the study's own `tables.py`, if it has one, after the generic report."""
    path = study.root / "tables.py"
    if not path.is_file():
        return
    spec = importlib.util.spec_from_file_location("study_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(study)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="census", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="measure the targets, then build the report")
    run_parser.add_argument("study", help="the study folder, holding targets.tsv")
    run_parser.add_argument("--only", nargs="+", default=(), metavar="ID", help="measure only these targets")
    run_parser.add_argument("--jobs", type=int, default=4, help="images run at once (default 4)")
    run_parser.add_argument("--cache", help="where images and VMs are kept (default: .cache in this repository)")
    report_parser = commands.add_parser("report", help="build the report from the data already measured")
    report_parser.add_argument("study", help="the study folder, holding targets.tsv")
    arguments = parser.parse_args(argv)

    study = Study(arguments.study, getattr(arguments, "cache", None))
    succeeded = True
    if arguments.command == "run":
        succeeded = run(study, set(arguments.only), arguments.jobs)
    report.build(study)
    study_hook(study)
    return 0 if succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
