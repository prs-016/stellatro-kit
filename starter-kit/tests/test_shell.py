import importlib.util
import unittest
from pathlib import Path


SHELL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "shell.py"
SPEC = importlib.util.spec_from_file_location("starter_shell", SHELL_PATH)
shell = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(shell)


class TestShellParsing(unittest.TestCase):
    def test_parse_draft_choice_accepts_valid_index(self):
        self.assertEqual(shell.parse_draft_choice(" 2 ", 5), 2)

    def test_parse_draft_choice_rejects_blank_input(self):
        with self.assertRaisesRegex(shell.ShellInputError, "No joker index entered"):
            shell.parse_draft_choice("   ", 5)

    def test_parse_draft_choice_rejects_out_of_range_index(self):
        with self.assertRaisesRegex(shell.ShellInputError, "between 0 and 4"):
            shell.parse_draft_choice("5", 5)

    def test_parse_play_indices_accepts_exactly_five_unique_indices(self):
        self.assertEqual(shell.parse_play_indices("0, 2,4,6,8", 10), [0, 2, 4, 6, 8])

    def test_parse_play_indices_rejects_blank_input(self):
        with self.assertRaisesRegex(shell.ShellInputError, "No card indices entered"):
            shell.parse_play_indices("   ", 10)

    def test_parse_play_indices_rejects_empty_slot(self):
        with self.assertRaisesRegex(shell.ShellInputError, "empty card slot"):
            shell.parse_play_indices("0,1,,3,4", 10)

    def test_parse_play_indices_rejects_non_numeric_values(self):
        with self.assertRaisesRegex(shell.ShellInputError, "whole numbers"):
            shell.parse_play_indices("0,1,two,3,4", 10)

    def test_parse_play_indices_rejects_wrong_number_of_cards(self):
        with self.assertRaisesRegex(shell.ShellInputError, "exactly 5 cards"):
            shell.parse_play_indices("0,1,2,3", 10)

    def test_parse_play_indices_rejects_duplicates(self):
        with self.assertRaisesRegex(shell.ShellInputError, "Duplicate"):
            shell.parse_play_indices("0,1,1,3,4", 10)

    def test_parse_play_indices_rejects_out_of_range_values(self):
        with self.assertRaisesRegex(shell.ShellInputError, "between 0 and 9"):
            shell.parse_play_indices("0,1,2,3,10", 10)


if __name__ == "__main__":
    unittest.main()
