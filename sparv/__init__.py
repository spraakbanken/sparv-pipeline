"""Main Sparv package."""
from sparv.core import config
from sparv.core.registry import annotator
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                Language, Model, Output, Source, XMLExportFiles)

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
    "Language",
    "Model",
    "Output",
    "Source",
    "XMLExportFiles"
]
