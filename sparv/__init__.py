"""Main Sparv package."""
from sparv.core import config
from sparv.core.registry import annotator, custom_annotator, exporter, importer, installer, modelbuilder
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, ModelOutput, Output, Source)

__version__ = "4.0.dev0"

__all__ = [
    "annotator",
    "custom_annotator",
    "exporter",
    "importer",
    "installer",
    "modelbuilder",
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
    "ModelOutput",
    "Output",
    "Source",
]
