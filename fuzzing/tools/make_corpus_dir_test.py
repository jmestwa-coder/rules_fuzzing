# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Unit tests for make_corpus_dir.py."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def resolve_script_path():
    candidates = [Path(__file__).with_name("make_corpus_dir.py")]
    test_workspace = os.environ.get("TEST_WORKSPACE")
    manifest_lookup_path = "fuzzing/tools/make_corpus_dir.py"
    if test_workspace:
        test_srcdir = os.environ.get("TEST_SRCDIR")
        if test_srcdir:
            candidates.append(
                Path(test_srcdir) / test_workspace / "fuzzing" / "tools" /
                "make_corpus_dir.py")
        runfiles_dir = os.environ.get("RUNFILES_DIR")
        if runfiles_dir:
            candidates.append(
                Path(runfiles_dir) / test_workspace / "fuzzing" / "tools" /
                "make_corpus_dir.py")
        manifest_lookup_path = (
            f"{test_workspace}/fuzzing/tools/make_corpus_dir.py")

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    manifest_file = os.environ.get("RUNFILES_MANIFEST_FILE")
    if manifest_file:
        try:
            workspace_match = None
            main_match = None
            with open(manifest_file, "r", encoding="utf-8") as manifest:
                for line in manifest:
                    entry = line.rstrip("\n")
                    if not entry:
                        continue
                    logical_path, separator, real_path = entry.partition(" ")
                    if not separator:
                        continue
                    normalized_path = logical_path.replace("\\", "/")
                    if not normalized_path.endswith("fuzzing/tools/make_corpus_dir.py"):
                        continue
                    candidate = Path(real_path)
                    if not candidate.is_file():
                        continue
                    if test_workspace and normalized_path.startswith(f"{test_workspace}/"):
                        workspace_match = candidate
                        break
                    if normalized_path.startswith("_main/") and not main_match:
                        main_match = candidate
            if workspace_match:
                return workspace_match
            if main_match:
                return main_match
        except OSError:
            pass

    raise FileNotFoundError("could not resolve make_corpus_dir.py in test runfiles")


SCRIPT_PATH = resolve_script_path()


class MakeCorpusDirTest(unittest.TestCase):

    def run_tool(self, args, cwd):
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH)] + args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_copies_nested_corpus_directory(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "corpus"
            (corpus / "nested").mkdir(parents=True)
            (corpus / "a.txt").write_text("A", encoding="utf-8")
            (corpus / "nested" / "b.txt").write_text("B", encoding="utf-8")
            output_dir = tmp / "out"

            result = self.run_tool(
                ["--corpus_list=corpus", "--output_dir=out"], cwd=tmp)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            copied_files = [path for path in output_dir.iterdir() if path.is_file()]
            self.assertEqual(len(copied_files), 2)
            copied_contents = sorted(path.read_text(encoding="utf-8")
                                     for path in copied_files)
            self.assertEqual(copied_contents, ["A", "B"])

    def test_copies_absolute_corpus_file(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus_file = tmp / "corpus-input.txt"
            corpus_file.write_text("payload", encoding="utf-8")
            output_dir = tmp / "out"

            result = self.run_tool(
                [f"--corpus_list={corpus_file}", f"--output_dir={output_dir}"],
                cwd=tmp,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            copied_files = [path for path in output_dir.iterdir() if path.is_file()]
            self.assertEqual(len(copied_files), 1)
            self.assertEqual(copied_files[0].read_text(encoding="utf-8"), "payload")

    def test_distinguishes_dot_prefix_from_plain_relative_path(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus_file = tmp / "a.txt"
            corpus_file.write_text("payload", encoding="utf-8")
            output_dir = tmp / "out"

            result = self.run_tool(
                ["--corpus_list=./a.txt,a.txt", "--output_dir=out"],
                cwd=tmp,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            copied_files = [path for path in output_dir.iterdir() if path.is_file()]
            self.assertEqual(len(copied_files), 2)

    def test_distinguishes_parent_navigation_from_plain_relative_path(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "dir").mkdir()
            corpus_file = tmp / "a.txt"
            corpus_file.write_text("payload", encoding="utf-8")
            output_dir = tmp / "out"

            result = self.run_tool(
                ["--corpus_list=dir/../a.txt,a.txt", "--output_dir=out"],
                cwd=tmp,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            copied_files = [path for path in output_dir.iterdir() if path.is_file()]
            self.assertEqual(len(copied_files), 2)

    def test_distinguishes_dot_prefix_from_literal_dot_filename(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "a.txt").write_text("from-a", encoding="utf-8")
            (tmp / "dot-a.txt").write_text("from-dot-a", encoding="utf-8")
            output_dir = tmp / "out"

            result = self.run_tool(
                ["--corpus_list=./a.txt,dot-a.txt", "--output_dir=out"],
                cwd=tmp,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            copied_files = [path for path in output_dir.iterdir() if path.is_file()]
            self.assertEqual(len(copied_files), 2)
            copied_contents = sorted(path.read_text(encoding="utf-8")
                                     for path in copied_files)
            self.assertEqual(copied_contents, ["from-a", "from-dot-a"])


if __name__ == "__main__":
    unittest.main()
