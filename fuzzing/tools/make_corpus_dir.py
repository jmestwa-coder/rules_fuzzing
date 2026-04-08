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
"""
Copies and renames a set of corpus files into a given directory.
"""

from absl import app
from absl import flags
from sys import stderr
import glob
import os
import shutil

FLAGS = flags.FLAGS

flags.DEFINE_list("corpus_list", [],
                  "Each element in the list stands for a corpus file")

flags.DEFINE_string("corpus_list_file", None,
                    "An optional file that lists corpus paths by lines")

flags.DEFINE_string("output_dir", None, "The path of the output directory")

flags.mark_flag_as_required("output_dir")

def flatten_corpus_path(corpus):
    prefix = ""
    if corpus.startswith("./") or (os.sep == "\\" and corpus.startswith(".\\")):
        prefix = "dot-"
        corpus = corpus[2:]

    if os.sep == "\\":
        corpus = corpus.replace("/", "\\")

    drive, tail = os.path.splitdrive(corpus)

    parts = [part for part in tail.split(os.sep) if part]
    flattened = "-".join(parts)

    if drive:
        drive_part = drive.rstrip(":\\/").replace("\\", "-").replace("/", "-")
        flattened = drive_part + ("-" + flattened if flattened else "")
    elif tail.startswith(os.sep):
        flattened = "-" + flattened

    return prefix + flattened

def expand_corpus_to_file_list(corpus, file_list):
    if not os.path.exists(corpus):
        raise FileNotFoundError("file " + corpus + " doesn't exist")
    if os.path.isdir(corpus):
        # The first element in glob("dir/**") is "dir/", which needs to be excluded
        for expanded_path in glob.glob(os.path.join(corpus, "**"), recursive=True)[1:]:
            if os.path.isfile(expanded_path):
                file_list.append(expanded_path)
    else:
        file_list.append(corpus)

def main(argv):
    if not os.path.exists(FLAGS.output_dir):
        os.makedirs(FLAGS.output_dir)

    expanded_file_list = []
    for corpus in FLAGS.corpus_list:
        expand_corpus_to_file_list(corpus, expanded_file_list)
    if FLAGS.corpus_list_file:
        with open(FLAGS.corpus_list_file) as corpus_list_file:
            for corpus_line in corpus_list_file:
                expand_corpus_to_file_list(
                    corpus_line.rstrip("\n"), expanded_file_list)

    if expanded_file_list:
        max_flattened_length = 200
        flattened_names = {}
        flattened_name_counts = {}
        needs_suffix = set()

        for corpus in expanded_file_list:
            flattened = flatten_corpus_path(corpus)
            flattened_names[corpus] = flattened
            flattened_key = flattened.lower() if os.name == "nt" else flattened
            flattened_name_counts[flattened_key] = (
                flattened_name_counts.get(flattened_key, 0) + 1)
            if len(flattened) > max_flattened_length:
                needs_suffix.add(corpus)

        for corpus in expanded_file_list:
            flattened = flattened_names[corpus]
            flattened_key = flattened.lower() if os.name == "nt" else flattened
            if flattened_name_counts[flattened_key] > 1:
                needs_suffix.add(corpus)

        suffix_map = {}
        if needs_suffix:
            suffix_width = len(str(len(needs_suffix)))
            for index, corpus in enumerate(sorted(needs_suffix), start=1):
                suffix_map[corpus] = f"{index:0{suffix_width}d}"

        final_name_map = {}
        final_name_counts = {}
        for corpus in expanded_file_list:
            flattened = flattened_names[corpus]
            suffix = suffix_map.get(corpus)
            if suffix:
                prefix_budget = max_flattened_length - len(suffix) - 2
                flattened = flattened[:max(1, prefix_budget)] + "--" + suffix
            final_name_map[corpus] = flattened
            flattened_key = flattened.lower() if os.name == "nt" else flattened
            final_name_counts[flattened_key] = (
                final_name_counts.get(flattened_key, 0) + 1)

        if any(count > 1 for count in final_name_counts.values()):
            unique_corpora = sorted(set(expanded_file_list))
            alias_width = len(str(len(unique_corpora)))
            alias_map = {
                corpus: f"entry-{index:0{alias_width}d}"
                for index, corpus in enumerate(unique_corpora, start=1)
            }
            for corpus in expanded_file_list:
                final_name_map[corpus] = alias_map[corpus]

        for corpus in expanded_file_list:
            dest = os.path.join(FLAGS.output_dir, final_name_map[corpus])
            # Whatever the separator we choose, there is an chance that
            # the dest name conflicts with another file
            if os.path.exists(dest):
                print("ERROR: file " + dest + " existed.", file=stderr)
                return -1
            shutil.copy(corpus, dest)
    else:
        open(os.path.join(FLAGS.output_dir, "empty_test"), "a").close()
    return 0


if __name__ == '__main__':
    app.run(main)
