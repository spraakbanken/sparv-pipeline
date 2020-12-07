"""Main Sparv package."""
from sparv.core.registry import annotator, exporter, importer, installer, modelbuilder, wizard
from sparv.util.classes import (AllDocuments, Annotation, AnnotationAllDocs, AnnotationCommonData, AnnotationData,
                                AnnotationDataAllDocs, Binary, BinaryDir, Config, Corpus, Document, Export,
                                ExportAnnotations, ExportInput, Headers, Language, Model, ModelOutput, Output,
                                OutputAllDocs, OutputCommonData, OutputData, OutputDataAllDocs, Source,
                                SourceAnnotations, SourceStructure, SourceStructureParser, Text, Wildcard)

__version__ = "4.0.0"

# Only expose classes and functions that are meant to be used in modules
__all__ = [
    "annotator",
    "exporter",
    "importer",
    "installer",
    "modelbuilder",
    "wizard",
    "AllDocuments",
    "Annotation",
    "AnnotationAllDocs",
    "AnnotationCommonData",
    "AnnotationData",
    "AnnotationDataAllDocs",
    "Binary",
    "BinaryDir",
    "Config",
    "Corpus",
    "Document",
    "Export",
    "ExportAnnotations",
    "ExportInput",
    "Headers",
    "Language",
    "Model",
    "ModelOutput",
    "Output",
    "OutputAllDocs",
    "OutputCommonData",
    "OutputData",
    "OutputDataAllDocs",
    "Source",
    "SourceAnnotations",
    "SourceStructure",
    "SourceStructureParser",
    "Text",
    "Wildcard"
]
