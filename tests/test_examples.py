import tempfile
import unittest
from pathlib import Path

from library.classes import BuilderInput
from main import EXAMPLES_DIRECTORY, list_example_filenames


class ExampleFilesTests(unittest.TestCase):
    def test_list_example_filenames_returns_sorted_json_files(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            directory = Path(temp_directory)
            (directory / "philippines_example.json").write_text(
                "{}", encoding="utf-8"
            )
            (directory / "notes.txt").write_text(
                "not an example", encoding="utf-8"
            )
            (directory / "indonesia_example.json").write_text(
                "{}", encoding="utf-8"
            )
            (directory / "peru_example.json").write_text("{}", encoding="utf-8")

            self.assertEqual(
                list_example_filenames(directory),
                [
                    "indonesia_example.json",
                    "peru_example.json",
                    "philippines_example.json",
                ],
            )

    def test_all_example_files_are_valid_builder_inputs(self):
        filenames = list_example_filenames(EXAMPLES_DIRECTORY)

        self.assertTrue(filenames)
        for filename in filenames:
            with self.subTest(filename=filename):
                BuilderInput.model_validate_json(
                    (EXAMPLES_DIRECTORY / filename).read_text(encoding="utf-8")
                )


if __name__ == "__main__":
    unittest.main()
