"""Main Sparv package."""
from sparv.core import config
from sparv.core.registry import annotator, exporter, importer, installer, modelbuilder
from sparv.util.classes import (AllDocuments, Annotation, AnnotationAllDocs, AnnotationData, AnnotationDataAllDocs,
                                AnnotationCommonData, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, ModelOutput, Output, OutputAllDocs, OutputData,
                                OutputDataAllDocs, OutputCommonData, Source, Text)

__version__ = "4.0.dev0"

__all__ = [
    "annotator",
    "config",
    "exporter",
    "importer",
    "installer",
    "modelbuilder",
    "AllDocuments",
    "Annotation",
    "AnnotationDataAllDocs",
    "AnnotationCommonData",
    "AnnotationAllDocs",
    "AnnotationData",
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
    "OutputData",
    "OutputCommonData",
    "OutputAllDocs",
    "OutputDataAllDocs",
    "Source",
    "Text"
]
