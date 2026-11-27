"""Load each target of a study into a Moose image and measure its metamodels.

Each target is one line of the study's `targets.tsv`: an id, a Moose version, and a
Smalltalk recipe that loads the project. Images are cached per recipe, so an unchanged
target reuses its image on the next run. VM lookup is `PHARO_<version>_VM`, the user's
`Documents/Pharo/vms` folder, the PATH, then a VM downloaded into the cache.
"""
import csv
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .study import REPOSITORY


ANALYZER = REPOSITORY / "analyzer" / "measure.st"
TARGET_RUNNER = REPOSITORY / "analyzer" / "run-target.st"

IMAGE_URLS = {
    "10": "https://github.com/moosetechnology/Moose/releases/download/v10.x.x/Moose10-stable-Pharo64-10.zip",
    "11": "https://github.com/moosetechnology/Moose/releases/download/v11.x.x/Moose11-stable-Pharo64-11.zip",
    "12": "https://github.com/moosetechnology/Moose/releases/download/v12.0.0/Moose12-stable-Pharo64-12.zip",
    "13": "https://github.com/moosetechnology/Moose/releases/download/continuous/Moose13-development-Pharo64-13.zip",
}
CSV_HEADER = [
    "record", "modelClass", "declaredPackage", "declaredSubmetamodelPackages", "metric", "value",
    "localEntity", "localPackage", "remoteEntity", "remotePackage", "property", "type", "typePackage",
]
# The aggregate files the report reads, each holding the raw records of some kinds. The
# others (remoteProperty, error) stay in the raw reports only.
RECORD_SETS = {
    "metrics": {"metric"},
    "package-behaviors": {"packageBehavior"},
    "package-traits": {"packageTrait"},
    "family-uses": {"remoteTraitUse", "remoteInheritance"},
    "relationship-extensions": {"remotePropertyExtension"},
}


@dataclass(frozen=True)
class Target:
    name: str
    version: str
    recipe: Path

    @property
    def source(self):
        return f"moose-{self.version}-{self.name}"


def quote_smalltalk(value):
    return "'" + str(value).replace("'", "''") + "'"


def platform_directory():
    system = platform.system()
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    names = {"Darwin": "Darwin", "Linux": "Linux", "Windows": "Windows"}
    if system not in names:
        raise RuntimeError(f"Unsupported platform: {system} ({machine})")
    return f"{names[system]}-{architecture}"


def executable_names():
    return ("Pharo.exe", "pharo.exe") if platform.system() == "Windows" else ("Pharo", "pharo")


def executable_under(directory, make_executable=False):
    if not directory.exists():
        return None
    for name in executable_names():
        for candidate in directory.rglob(name):
            if make_executable and platform.system() != "Windows":
                candidate.chmod(candidate.stat().st_mode | 0o100)
            if candidate.is_file() and (platform.system() == "Windows" or os.access(candidate, os.X_OK)):
                return candidate
    return None


def user_vm(version):
    """Use an explicit override first, then the conventional user VM folder."""
    override = os.environ.get(f"PHARO_{version}_VM")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file() and (platform.system() == "Windows" or os.access(candidate, os.X_OK)):
            return candidate
        raise RuntimeError(f"PHARO_{version}_VM is not executable: {candidate}")

    vms = Path.home() / "Documents" / "Pharo" / "vms"
    for directory in sorted(vms.glob(f"{int(version) * 10}-*")):
        if found := executable_under(directory):
            return found
    for command in ("Pharo", "pharo"):
        if found := shutil.which(command):
            return Path(found)
    return None


def cached_vm(cache, version):
    return executable_under(cache / "vms" / platform_directory() / version)


def download_vm(cache, version):
    """Cache the stable Spur VM for this OS and CPU when no local VM is usable."""
    directory = cache / "vms" / platform_directory() / version
    archive = directory / "stable10.zip"
    directory.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        url = f"https://files.pharo.org/vm/pharo-spur64/{platform_directory()}/stable10.zip"
        print(f"Downloading Pharo VM for Moose {version}: {url}", flush=True)
        urllib.request.urlretrieve(url, archive)
    with zipfile.ZipFile(archive) as source:
        source.extractall(directory)
    vm = executable_under(directory, make_executable=True)
    if vm is None:
        raise RuntimeError(f"The downloaded VM archive has no executable: {archive}")
    return vm


def vm_for(cache, version):
    return user_vm(version) or cached_vm(cache, version) or download_vm(cache, version)


def download(url, destination):
    if not destination.exists():
        print(f"Downloading Moose image: {url}", flush=True)
        urllib.request.urlretrieve(url, destination)


def image_for(cache, target):
    """Return the recipe-keyed image, resetting unsaved images before a first load."""
    recipe_hash = hashlib.sha256(target.recipe.read_bytes()).hexdigest()
    directory = cache / f"moose-{target.version}-{target.name}-{recipe_hash}"
    marker = directory / ".recipe-loaded"
    override = os.environ.get(f"PHARO_{target.version}_IMAGE")
    if override:
        return Path(override).expanduser(), marker

    archive = directory / "image.zip"
    image = next(directory.rglob("*.image"), None) if directory.exists() else None
    if image is None:
        try:
            url = IMAGE_URLS[target.version]
        except KeyError as error:
            raise RuntimeError(f"No Moose image source for version {target.version}") from error
        directory.mkdir(parents=True, exist_ok=True)
        download(url, archive)
        with zipfile.ZipFile(archive) as source:
            source.extractall(directory)

    if not marker.exists():
        with zipfile.ZipFile(archive) as source:
            source.extractall(directory)
        for name in ("iceberg", "package-cache"):
            for path in directory.glob(f"**/pharo-local/{name}"):
                shutil.rmtree(path)

    image = next(directory.rglob("*.image"), None)
    if image is None:
        raise RuntimeError(f"Downloaded Moose {target.version} archive has no image: {archive}")
    return image, marker


def write_failure(output, message):
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(CSV_HEADER)
        writer.writerow(["error", "", "", "", "exception", message, "", "", "", "", "", "", ""])


def invocation(study, target, marker, temporary):
    output = study.raw / f"{target.source}.csv"
    reuse = marker.exists()
    values = ["--reuse", "--output", str(output), "--analyzer", str(ANALYZER)] if reuse else [
        "--recipe", str(target.recipe), "--output", str(output), "--analyzer", str(ANALYZER),
    ]
    text = "Smalltalk globals at: #FameRemoteEntityAnalysisInvocation put: { "
    text += ". ".join(quote_smalltalk(value) for value in values)
    text += " }.\n"
    # Only disposable, freshly extracted images can discard loader changes.
    managed = not os.environ.get(f"PHARO_{target.version}_IMAGE")
    text += f"Smalltalk globals at: #FameRemoteEntityAnalysisManagedImage put: {str(managed).lower()}.\n"
    text += quote_smalltalk(TARGET_RUNNER) + " asFileReference fileIn.\n"
    path = temporary / f"{target.version}-{target.name}-run.st"
    path.write_text(text)
    return path, output, reuse


def has_failure(output):
    if not output.exists() or output.stat().st_size == 0:
        return True
    with output.open(newline="") as stream:
        return any(row and row[0] == "error" for row in csv.reader(stream))


def run_target(study, target, vm, temporary):
    try:
        image, marker = image_for(study.cache, target)
        runner, output, reuse = invocation(study, target, marker, temporary)
        print(f"{'Reusing' if reuse else 'Loading'} Moose {target.version} image for {target.name}", flush=True)
        before = image.stat().st_mtime_ns
        subprocess.run([str(vm), "--headless", str(image), "st", "--quit", str(runner)], timeout=900, check=True)
        # Keep Pharo's detailed exception row; only synthesize a generic error
        # when the VM exited without writing any report at all.
        if has_failure(output):
            print(f"Failed {target.source}: see {output}", file=sys.stderr, flush=True)
            return False
        if not reuse and image.stat().st_mtime_ns == before:
            raise RuntimeError("Pharo command did not save the image")
        if not reuse:
            marker.touch()
        return True
    except Exception as error:
        write_failure(study.raw / f"{target.source}.csv", str(error))
        print(f"Failed {target.source}: {error}", file=sys.stderr, flush=True)
        return False


def targets(study, temporary):
    """The study's targets, each recipe written to a file in `temporary`.

    A recipe may start with `@file.st`, which includes that file of the study folder
    before the rest of the line. The included text is part of the image cache key."""
    result = []
    with study.targets_file.open(newline="") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            name, version, recipe = row
            if recipe.startswith("@"):
                include, _, recipe = recipe.partition(" ")
                filename = include[1:]
                if not filename or Path(filename).name != filename:
                    raise ValueError(f"Invalid recipe include: {include}")
                recipe = (study.root / filename).read_text().rstrip() + "\n" + recipe
            path = temporary / f"{version}-{name}.st"
            path.write_text(recipe + "\n")
            result.append(Target(name, version, path))
    return result


def aggregate(study, measured):
    """Gather the raw reports of the measured targets into one file per record kind."""
    study.aggregate.mkdir(parents=True, exist_ok=True)
    rows_by_source = []
    for target in measured:
        with (study.raw / f"{target.source}.csv").open(newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            rows_by_source.append((target.source, header, list(reader)))

    for name, wanted in RECORD_SETS.items():
        with (study.aggregate / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["source", *rows_by_source[0][1]])
            for source, _, rows in rows_by_source:
                writer.writerows([source, *row] for row in rows if row and row[0] in wanted)


def run(study, only=(), jobs=4):
    """Measure the study's targets, or only those named, then aggregate every report.

    Returns False when a target failed. Its report then holds an `error` row."""
    study.cache.mkdir(parents=True, exist_ok=True)
    study.raw.mkdir(parents=True, exist_ok=True)
    # Invocation files are only a bridge between Python and Pharo; never retain them as output.
    with tempfile.TemporaryDirectory(prefix="analysis-", dir=study.cache) as temporary_name:
        temporary = Path(temporary_name)
        configured = targets(study, temporary)
        unknown = set(only) - {target.name for target in configured}
        if unknown:
            raise SystemExit(f"Unknown targets: {', '.join(sorted(unknown))}")
        selected = [target for target in configured if not only or target.name in only]
        for target in selected:
            (study.raw / f"{target.source}.csv").unlink(missing_ok=True)
        vms = {version: vm_for(study.cache, version) for version in sorted({target.version for target in selected})}
        # Each Pharo image is a full VM. A small pool remains parallel without
        # exhausting memory and silently losing reports on ordinary machines.
        failed = False
        with ThreadPoolExecutor(max_workers=max(1, min(jobs, len(selected)))) as pool:
            futures = [pool.submit(run_target, study, target, vms[target.version], temporary) for target in selected]
            for future in as_completed(futures):
                failed = not future.result() or failed
        aggregate(study, [target for target in configured if (study.raw / f"{target.source}.csv").exists()])
    return not failed
