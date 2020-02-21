"""
Example Snakefile. This should be replaced by corpus specifik snakefiles later on.

Run with e.g. `snakemake vrt`
"""
# Import default configuration
import os
include: os.path.join(os.getenv('SPARV_PIPELINE_PATH'), "config.snake")

# Copus location
corpus_dir = "../testkorpus"
source_dir = os.path.join(corpus_dir, "original", "xml")
# TODO: move these somewhere else?
annotation_dir = os.path.join(corpus_dir, "annotations")
export_dir = os.path.join(corpus_dir, "export.original")

# Info about input and resulting annotations
positional_annotations = ["word", "pos", "msd"]
# Format: (input_elem:attribute, output_elem:attribute)
existing_structural_elements = [("text", "text"), ("text:author", "text.author")]
structural_annotations = ["sentence", "sentence.id", "paragraph", "text", "text.author"]

# Import rule files
# TODO: Build a mechanism that figures out automatically what files to import
include: "snakefiles/utils.snake"
include: "snakefiles/number.snake"
include: "snakefiles/xmlparser.snake"
include: "snakefiles/segment.snake"
include: "snakefiles/hunpos.snake"
include: "snakefiles/cwb.snake"
