"""Main Sparv package."""
from sparv.core import config
from sparv.core.registry import annotator
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, Output, Source)

__version__ = "4.0.dev0"

__all__ = [
    "annotator",
    "config",
    "AllDocuments",
    "Annotation",
    "Binary",
    "Corpus",
    "Config",
    "Document",
    "Export",
    "ExportAnnotations",
    "ExportInput",
    "Language",
    "Model",
    "Output",
    "Source"
]
