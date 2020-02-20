"""
Example Snakefile. This should be replaced by corpus specifik snakefiles later on.

Run with e.g. `snakemake vrt`
"""

# Import default values
include: "snakefiles/defaults.snake"

# Copus location
source_dir = "../testkorpus/original/xml"
annotation_dir = "../testkorpus/annotations"

# Info about input and resulting annotations
positional_annotations = ["word", "pos", "msd"]

existing_structural_elements = [("text", "text")]
structural_annotations = ["sentence", "paragraph", "text"]


sparv_model_dir = "./models"  # TODO: move this to defaults.snake! Use environment variable?

# Import rule files
# TODO: Build a mechanism that figures out automatically what files to import
include: "snakefiles/utils.snake"
include: "snakefiles/xmlparser.snake"
include: "snakefiles/segment.snake"
include: "snakefiles/hunpos.snake"
include: "snakefiles/cwb.snake"
