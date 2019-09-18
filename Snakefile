"""Example Snakefile. This should be replaced by corpus specifik snakefiles later on."""

source_dir = "../testkorpus/original/xml"
annotation_dir = "../testkorpus/annotations"

input_files = [f[1][0] for f in snakemake.utils.listfiles("%s/{file}.xml" % source_dir)]

existing_structural_elements = ["text"]

paragraph_chunk = "text"
paragraph_segmenter = "blanklines"

sentence_chunk = "paragraph"
sentence_segmenter = "punkt_sentence"

token_chunk = "sentence"
token_segmenter = "better_word"
tokenizer_config = "./models/bettertokenizer.sv"


include: "snakefiles/utils.snake"
include: "snakefiles/xmlparser.snake"
include: "snakefiles/segment.snake"
