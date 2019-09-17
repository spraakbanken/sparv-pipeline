"""Example Snakefiles. This should be replaced by corpus specifik snakefiles later on."""

import os

source_dir = "../testkorpus/original/xml"
annotation_dir = "../testkorpus/annotations"

input_files = [val for sublist in [[os.path.relpath(os.path.join(i[0], j.rsplit(".", 1)[0]), source_dir) for j in i[2]] for i in os.walk(source_dir)] for val in sublist]


include: "snakefiles/parse_xml.snake"
include: "snakefiles/segment_paragraphs.snake"
