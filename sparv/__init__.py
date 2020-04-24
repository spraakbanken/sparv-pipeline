"""Main Sparv package."""
from sparv.core import config
from sparv.core.registry import annotator, exporter, importer, installer
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, Output, Source)

__version__ = "4.0.dev0"

__all__ = [
    "annotator",
    "exporter",
    "importer",
    "installer",
    "config",
    "AllDocuments",
    "Annotation",
    "Binary",
    "Config",
    "Corpus",
    "Document",
    "Export",
    "ExportAnnotations",
    "ExportInput",
    "Language",
    "Model",
    "Output",
    "Source",
]
