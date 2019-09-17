"""Example Snakefile. This should be replaced by corpus specifik snakefiles later on."""

source_dir = "../testkorpus/original/xml"
annotation_dir = "../testkorpus/annotations"

input_files = [f[1][0] for f in snakemake.utils.listfiles("%s/{file}.xml" % source_dir)]


include: "snakefiles/parse_xml.snake"
include: "snakefiles/segment_paragraphs.snake"
