# Sparv Classes
Sparv classes are used to represent common data types within Sparv such as annotations and models. They are used for
type hints and default arguments within the signatures of decorated functions. Sparv uses these classes to figure out
what inputs and outputs a function has, which is essential for building dependencies between annotations. Sparv classes
also provide useful methods such as methods for reading and writing annotations. Using these, an annotator can read and
write annotation files without the need to know anything about Sparv's internal data format. Below is a list with all
the available Sparv classes, their arguments, properties, and public methods.


## AllDocuments
An instance of this class holds a list with the names of all source documents. It is typically used by exporter
functions that combine annotations from all source documents.


## Annotation
An instance of this class represents a regular annotation tied to one document. This class is used when an annotation is
needed as input for a function, e.g. `Annotation("<token:word>")`.

**Arguments:**

- `name`: The name of the annotation.
- `doc`: The name of the document.

**Properties:**

- `has_attribute`: Return True if the annotation has an attribute.
- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation).

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists()`: Return True if annotation file exists.
- `read(allow_newlines: bool = False)`: Yield each line from the annotation.
- `get_children(child: BaseAnnotation, orphan_alert=False, preserve_parent_annotation_order=False)`: Return two lists.
    The first one is a list with n (= total number of parents) elements where every element is a list of indices in the
    child annotation. The second one is a list of orphans, i.e. containing indices in the child annotation that have no
    parent. Both parents and children are sorted according to their position in the source document, unless
    preserve_parent_annotation_order is set to True, in which case the parents keep the order from the parent
    annotation.
- `get_parents(parent: BaseAnnotation, orphan_alert: bool = False)`: Return a list with n (= total number of children)
  elements where every element is an index in the parent annotation. Return None when no parent is found.
- `read_parents_and_children(parent, child)`: Read parent and child annotations. Reorder them according to span
  position, but keep original index information.
- `read_attributes(annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]], with_annotation_name: bool =
  False, allow_newlines: bool = False)`: Yield tuples of multiple attributes on the same annotation.
- `read_spans(decimals=False, with_annotation_name=False)`: Yield the spans of the annotation.
- `create_empty_attribute()`: Return a list filled with None of the same size as this annotation.


## AnnotationAllDocs
Regular annotation but the document must be specified for all actions. Use as input to an annotator function to require
the specificed annotation for every document in the corpus.

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation)

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `read(doc: str)`: Yield each line from the annotation.
- `read_spans(doc: str, decimals=False, with_annotation_name=False)`: Yield the spans of the annotation.
- `create_empty_attribute(doc: str)`: Return a list filled with None of the same size as this annotation.
- `exists(doc: str)`: Return True if annotation file exists.


## AnnotationCommonData
Like [`AnnotationData`](#annotationdata), an instance of this class represents an annotation with arbitrary data, but
`AnnotationCommonData` is used for data that applies to the whole corpus (i.e. data that is not specific to one source
document).

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation)

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `read()`: Read arbitrary corpus level string data from annotation file.


## AnnotationData
This class represents an annotation holding arbitrary data, i.e. data that is not tied to spans in the corpus text.

**Arguments:**

- `name`: The name of the annotation.
- `doc`: The name of the document.

**Properties:**

- `has_attribute`: Return True if the annotation has an attribute.
- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation).

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists()`: Return True if annotation file exists.
- `read(doc: Optional[str] = None)`: Read arbitrary string data from annotation file.


## AnnotationDataAllDocs
Like [`AnnotationData`](#annotationdata), this class is used for annotations holding arbitrary data but the document
must be specified for all actions. Use as input to an annotator to require the specificed annotation for every document
in the corpus.

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation)

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists()`: Return True if annotation file exists.
- `read(doc: Optional[str] = None)`: Read arbitrary string data from annotation file.


## Binary
An instance of this class holds a path to a binary executable. This may be a path relative to the `bin` path inside the
Sparv data directory. This class is often used to define a prerequisite for an annotator function.

**Arguments:**

- default argument: Path to binary executable.


## BinaryDir
An instance of this class holds the path to a directory containing executable binaries. This may be a path relative to
the `bin` path inside the Sparv data directory.

**Arguments:**

- default argument: Path to directory containing executable binaries.


## Config
An instance of this class holds a configuration key name and its default value.

**Arguments:**

- `name`: The name of the configuration key.
- `default`: An optional default value of the configuration key.
- `description`: An obligatory description.


## Corpus
An instance of this class holds the name (ID) of the corpus.


## Document
An instance of this class holds the name of a source document.


## Export
An instance of this class represents an export file. This class is used to define an output of an exporter function.

**Arguments:**

- `name`: The export directory and filename pattern (e.g. `"xml_pretty/[xml_export.filename]"`).
- `absolute_path`: Set to `True` if the path is absolute. Default: `False`


## ExportAnnotations
List of annotations to be included in the export. This list is defined in the corpus configuration.

**Arguments:**

- `config_name`: The config variable pointing out what annotations to include.
- `is_input`: If set to `False` the annotations won't be added to the rule's input. Default: `True`


## ExportInput
Export directory and filename pattern, used as input. Use this class if you need export files as input in another
function.

**Arguments:**

- `val`: The export directory and filename pattern (e.g. `"xml_pretty/[xml_export.filename]"`).
- `all_docs`: Set to `True` to get the export for all source documents. Default: `False`
- `absolute_path`: Set to `True` if the path is absolute. Default: `False`


## Headers
List of header annotation names for a given document.

**Arguments:**

- default argument: The name of the document.

**Methods:**

- `read()`: Read the headers file and return a list of header annotation names.
- `write(header_annotations: List[str])`: Write headers file.
- `exists()`: Return True if headers file exists for this document.


## Language
In instance of this class holds information about the luanguage of the corpus. This information is retrieved from the
corpus configuration and is specified as ISO 639-3 code.


## Model
An instance of this class holds a path to a model file relative to the Sparv model directory. This class is typically
used as input to annotator functions.

**Arguments**:
- `name`: The name of the annotation.

**Properties:**:
- `path`: The path to the model file as a `pathlib.Path` object.

**Methods:**:
- `write(data)`: Write arbitrary string data to models directory.
- `read()`: Read arbitrary string data from file in models directory.
- `write_pickle(data, protocol=-1)`: Dump `data` to pickle file in models directory.
- `read_pickle()`: Read pickled data from file in models directory.
- `download(url: str)`: Download file from `url` and save to modeldir.
- `unzip()`: Unzip zip file inside modeldir.
- `ungzip(out: str)`: Unzip gzip file inside modeldir.
- `remove(raise_errors: bool = False)`: Remove model file from disk. If `raise_errors` is set to `True` an error will be
  raised if the file cannot be removed (e.g. if it does not exist).


## ModelOutput
This class is very similar to [`Model`](#model) but it is used as output of a modelbuilder.

**Arguments**:
- `name`: The name of the annotation.
- `description`: An optional description.

**Properties:**:
- `path`: The path to the model file as a `pathlib.Path` object.

**Methods:**:
- `write(data)`: Write arbitrary string data to models directory.
- `read()`: Read arbitrary string data from file in models directory.
- `write_pickle(data, protocol=-1)`: Dump `data` to pickle file in models directory.
- `read_pickle()`: Read pickled data from file in models directory.
- `download(url: str)`: Download file from `url` and save to modeldir.
- `unzip()`: Unzip zip file inside modeldir.
- `ungzip(out: str)`: Unzip gzip file inside modeldir.
- `remove(raise_errors: bool = False)`: Remove model file from disk. If `raise_errors` is set to `True` an error will be
  raised if the file cannot be removed (e.g. if it does not exist).


## Output
Regular annotation or attribute used as output (e.g. of an annotator function).

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.
- `doc`: The name of the document.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(values, append: bool = False, allow_newlines: bool = False, doc: Optional[str] = None)`: Write an annotation to
  file. Existing annotation will be overwritten. 'values' should be a list of values.
- `exists()`: Return True if annotation file exists.


## OutputAllDocs
Similar to [`Output`](#output) this class represents a regular annotation or attribute used as output, but the document
must be specified for all actions.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(values, doc: str, append: bool = False, allow_newlines: bool = False)`: Write an annotation to file. Existing
  annotation will be overwritten. 'values' should be a list of values.
- `exists(doc: str)`: Return True if annotation file exists.


## OutputCommonData
Similar to [`OutputData`](#outputdata) but for a data annotation that is valid for the whole corpus.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, append: bool = False)`: Write arbitrary corpus level string data to annotation file.


## OutputData
This class represents an annotation holding arbitrary data (i.e. data that is not tied to spans in the corpus text) that
is used as output.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.
- `doc`: The name of the document.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, append: bool = False)`: Write arbitrary corpus level string data to annotation file.
- `exists()`: Return True if annotation file exists.


## OutputDataAllDocs
Like [`OutputData`](#outputdata), this class is used for annotations holding arbitrary data and that is used as output,
but the document must be specified for all actions.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, doc: str, append: bool = False)`: Write arbitrary corpus level string data to annotation file.
- `exists(doc: str)`: Return True if annotation file exists.


## Source
An instance of this class holds a path to the directory containing input files.

**Arguments:**

- default argument: Path to directory containing input files.

**Methods:**

- `get_path(doc: Document, extension: str)`: Get path to a specific source file.


## SourceAnnotations
List of source annotations to be included in the export. This list is defined in the corpus configuration.

**Arguments:**

- `config_name`: The config variable pointing out what source annotations to include.
- `is_input`: If set to `False` the annotations won't be added to the rule's input. Default: `True`


## SourceStructure
Every annotation available in a source document.

**Arguments:**

- default argument: The name of the document.

**Methods:**

- `read()`: Read structure file.
- `write(structure)`: Sort the document's structural elements and write structure file.


## SourceStructureParser
This is an abstract class that should be implemented by an importer's structure parser.

**Arguments:**

- `source_dir: pathlib.Path`: Path to corpus source files.

**Methods:**

- `setup()`: Return a list of wizard dictionaries with questions needed for setting up the class. Answers to the
  questions will automatically be saved to self.answers.


## Text
An instance of this class represents the corpus text.

**Arguments:**

- `doc`: The name of the document.

**Methods:**

- `read()`: Get corpus text.
- `write(text)`: Write text to the designated file of a corpus. `text` is a unicode string.


## Wildcard
An instance of this class holds wildcard information. It is typically used in the `wildcards` list passed as an argument to the [`@annotator` decorator](developers-guide/sparv-decorators.md#annotator), e.g.:
```python
@annotator("Number {annotation} by relative position within {parent}", wildcards=[
    Wildcard("annotation", Wildcard.ANNOTATION),
    Wildcard("parent", Wildcard.ANNOTATION)
])
```

**Arguments:**

- `name`: The name of the wildcard.
- `type`: The type of the wildcard. One of `Wildcard.ANNOTATION`, `Wildcard.ATTRIBUTE`, `Wildcard.ANNOTATION_ATTRIBUTE`,
  `Wildcard.OTHER`. Defaults to `Wildcard.OTHER`.
- `description`: An optional description.
