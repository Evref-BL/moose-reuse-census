import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from census import run
from census.report import Census
from census.study import Study


def study_in(directory, targets="example\t13\tFirst step.\n"):
    root = Path(directory)
    (root / "targets.tsv").write_text(targets)
    return Study(root, cache=root / "cache")


class ImageOwnershipTest(unittest.TestCase):
    def test_only_runner_managed_images_are_marked_disposable(self):
        with tempfile.TemporaryDirectory() as directory:
            study = study_in(directory)
            target = run.Target("casino", "11", Path(directory) / "recipe.st")
            marker = Path(directory) / "marker"
            for override, expected in (("", "true"), ("/user/image.image", "false")):
                with self.subTest(override=override), patch.dict(os.environ, {"PHARO_11_IMAGE": override}):
                    invocation, _, _ = run.invocation(study, target, marker, Path(directory))
                    self.assertIn(f"#FameRemoteEntityAnalysisManagedImage put: {expected}", invocation.read_text())


class RecipeIncludesTest(unittest.TestCase):
    def test_include_is_expanded_into_recipe_and_cache_key(self):
        with tempfile.TemporaryDirectory() as directory:
            study = study_in(directory, "example\t13\t@foundation.st Second step.\n")
            (Path(directory) / "foundation.st").write_text("First step.\n")
            target = run.targets(study, Path(directory))[0]
            self.assertEqual(target.recipe.read_text(), "First step.\nSecond step.\n")
            (Path(directory) / "foundation.st").write_text("Changed step.\n")
            self.assertEqual(run.targets(study, Path(directory))[0].recipe.read_text(), "Changed step.\nSecond step.\n")

    def test_include_must_stay_in_the_study_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            study = study_in(directory, "example\t13\t@../outside.st Step.\n")
            with self.assertRaises(ValueError):
                run.targets(study, Path(directory))


class ModelNameTest(unittest.TestCase):
    def test_default_rule_and_study_names(self):
        with tempfile.TemporaryDirectory() as directory:
            study = study_in(directory)
            (Path(directory) / "names.tsv").write_text("package\tname\nSQL-Model\tFamix-SQL\n")
            census = Census.__new__(Census)
            census.names = study.settings("names.tsv")
            self.assertEqual(census.model_name("Famix-Java-Entities"), "Famix-Java")
            self.assertEqual(census.model_name("Casino-Model-Layout"), "Casino-Layout")
            self.assertEqual(census.model_name("SQL-Model"), "Famix-SQL")


if __name__ == "__main__":
    unittest.main()
