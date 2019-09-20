"""Example Snakefile. This should be replaced by corpus specifik snakefiles later on."""

source_dir = "../testkorpus/original/xml"
annotation_dir = "../testkorpus/annotations"

input_files = [f[1][0] for f in snakemake.utils.listfiles("%s/{file}.xml" % source_dir)]

existing_structural_elements = [("text", "text")]

paragraph_chunk = "text"
paragraph_segmenter = "blanklines"

sentence_chunk = "paragraph"
sentence_segmenter = "punkt_sentence"

token_chunk = "sentence"
token_segmenter = "better_word"


sparv_model_dir = "./models"


include: "snakefiles/utils.snake"
include: "snakefiles/xmlparser.snake"
include: "snakefiles/segment.snake"
include: "snakefiles/hunpos.snake"
include: "snakefiles/cwb.snake"
