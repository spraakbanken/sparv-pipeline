# Sparv Classes
Sparv classes are used to represent common data types within Sparv such as annotations and models. They are used for
type hints and default arguments within the signatures of decorated functions. Sparv uses these classes to figure out
what inputs and outputs a function has, which is essential for building dependencies between annotations. Sparv classes
also provide useful methods such as methods for reading and writing annotations. Using these, an annotator can read and
write annotation files without the need to know anything about Sparv's internal data format. Below is a list with all
the available Sparv classes, their arguments, properties, and public methods.


## AllSourceFilenames
An instance of this class holds an iterable with the names of all source files. It is typically used by exporter
functions that combine annotations from all source files.


## Annotation
An instance of this class represents a regular annotation tied to one source file. This class is used when an
annotation is needed as input for a function, e.g. `Annotation("<token:word>")`.

**Arguments:**

- `name`: The name of the annotation.
- `source_file`: The name of the source file.

**Properties:**

- `has_attribute`: Return True if the annotation has an attribute.
- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation).

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.
- `read(allow_newlines: bool = False)`: Yield each line from the annotation.
- `read_spans(decimals=False, with_annotation_name=False)`: Yield the spans of the annotation.
- `read_attributes(annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]], with_annotation_name: bool =
  False, allow_newlines: bool = False)`: Yield tuples of multiple attributes on the same annotation.
- `get_children(child: BaseAnnotation, orphan_alert=False, preserve_parent_annotation_order=False)`: Return two lists.
    The first one is a list with n (= total number of parents) elements where every element is a list of indices in the
    child annotation. The second one is a list of orphans, i.e. containing indices in the child annotation that have no
    parent. Both parents and children are sorted according to their position in the source file, unless
    preserve_parent_annotation_order is set to True, in which case the parents keep the order from the parent
    annotation.
- `get_parents(parent: BaseAnnotation, orphan_alert: bool = False)`: Return a list with n (= total number of children)
  elements where every element is an index in the parent annotation. Return None when no parent is found.
- `read_parents_and_children(parent, child)`: Read parent and child annotations. Reorder them according to span
  position, but keep original index information.
- `create_empty_attribute()`: Return a list filled with None of the same size as this annotation.
- `get_size()`: Get the number of values.


## AnnotationAllSourceFiles
Regular annotation but the source filename must be specified for all actions. Use as input to an annotator function to
require the specified annotation for every source file in the corpus.

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `has_attribute`: Return True if the annotation has an attribute.
- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation).

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists(source_file: str)`: Return True if annotation file exists.
- `remove(source_file: str)`: Remove annotation file.
- `read(source_file: str, allow_newlines: bool = False)`: Yield each line from the annotation.
- `read_spans(source_file: str, decimals=False, with_annotation_name=False)`: Yield the spans of the annotation.
- `read_attributes(source_file: str, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]], with_annotation_name: bool =
  False, allow_newlines: bool = False)`: Yield tuples of multiple attributes on the same annotation.
- `get_children(source_file: str, child: BaseAnnotation, orphan_alert=False, preserve_parent_annotation_order=False)`: Return two lists.
    The first one is a list with n (= total number of parents) elements where every element is a list of indices in the
    child annotation. The second one is a list of orphans, i.e. containing indices in the child annotation that have no
    parent. Both parents and children are sorted according to their position in the source file, unless
    preserve_parent_annotation_order is set to True, in which case the parents keep the order from the parent
    annotation.
- `get_parents(source_file: str, parent: BaseAnnotation, orphan_alert: bool = False)`: Return a list with n (= total number of children)
  elements where every element is an index in the parent annotation. Return None when no parent is found.
- `read_parents_and_children(source_file: str, parent, child)`: Read parent and child annotations. Reorder them according to span
  position, but keep original index information.
- `create_empty_attribute(source_file: str)`: Return a list filled with None of the same size as this annotation.
- `get_size(source_file: str)`: Get the number of values.


## AnnotationCommonData
Like [`AnnotationData`](#annotationdata), an instance of this class represents an annotation with arbitrary data, but
`AnnotationCommonData` is used for data that applies to the whole corpus (i.e. data that is not specific to one source
file).

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation)

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `read()`: Read arbitrary corpus level string data from annotation file.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.


## AnnotationName
Use this class when only the name of an annotation is of interest, not the actual data. The annotation will not be added
as a prerequisite for the annotator, meaning that the use of `AnnotationName` will not automatically trigger the
creation of the referenced annotation.

**Arguments:**

- `name`: The name of the annotation.
- `source_file`: The name of the source file.


## AnnotationData
This class represents an annotation holding arbitrary data, i.e. data that is not tied to spans in the corpus text.

**Arguments:**

- `name`: The name of the annotation.
- `source_file`: The name of the source file.

**Properties:**

- `has_attribute`: Return True if the annotation has an attribute.
- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation).

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.
- `read(source_file: Optional[str] = None)`: Read arbitrary string data from annotation file.


## AnnotationDataAllSourceFiles
Like [`AnnotationData`](#annotationdata), this class is used for annotations holding arbitrary data but the source file
must be specified for all actions. Use as input to an annotator to require the specified annotation for every source
file in the corpus.

**Arguments:**

- `name`: The name of the annotation.

**Properties:**

- `annotation_name`: Get annotation name (excluding name of any attribute).
- `attribute_name`: Get attribute name (excluding name of annotation)

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `exists(source_file: str)`: Return True if annotation file exists.
- `remove(source_file: str)`: Remove annotation file.
- `read(source_file: str)`: Read arbitrary string data from annotation file.


## Binary
An instance of this class holds a path to a binary executable. This may be a path relative to the `bin` path inside the
Sparv data directory. This class is often used to define a prerequisite for an annotator function.

**Arguments:**

- Path to binary executable.


## BinaryDir
An instance of this class holds the path to a directory containing executable binaries. This may be a path relative to
the `bin` path inside the Sparv data directory.

**Arguments:**

- Path to directory containing executable binaries.


## Config
An instance of this class holds a configuration key name and its default value. The datatype and values allowed can be
specified, and will be used both for validating the config and when generating the Sparv config JSON schema.

**Arguments:**

- `name`: The name of the configuration key.
- `default`: An optional default value of the configuration key.
- `description`: An obligatory description.
- `datatype`: Typehint specifying the allowed datatype(s).
- `choices`: Iterable with valid choices.
- `pattern`: Regular expression matching valid values (only for the datatype `str`).
- `min`: A `float` representing the minimum numeric value.
- `max`: A `float` representing the maximum numeric value.
- `const`: Restrict the value to a single value.
- `conditions`: List of `Config` objects with conditions that must also be met.

## Corpus
An instance of this class holds the name (ID) of the corpus.


## SourceFilename
An instance of this class holds the name of a source file.


## Export
An instance of this class represents an export file. This class is used to define an output of an exporter function.

**Arguments:**

- The export directory and filename pattern (e.g. `"xml_export.pretty/[xml_export.filename]"`). The export directory
  must contain the module name as a prefix, or be equal to the module name.


## ExportAnnotations
Iterable with annotations to be included in the export. This list is defined in the corpus configuration.
Annotation files for the current source file will automatically be added as dependencies when using this class.

**Arguments:**

- `config_name`: The config variable pointing out what annotations to include.


## ExportAnnotationsAllSourceFiles
Iterable with annotations to be included in the export. This list is defined in the corpus configuration.
Annotation files for _all_ source files will automatically be added as dependencies when using this class.

**Arguments:**

- `config_name`: The config variable pointing out what annotations to include.


## ExportAnnotationNames
Iterable with annotations to be included in the export. This list is defined in the corpus configuration. Unlike
`ExportAnnotations`, the annotations will not be added as dependencies when using this class.

**Arguments:**

- `config_name`: The config variable pointing out what annotations to include.


## ExportInput
Export directory and filename pattern, used as input. Use this class if you need export files as input in another
function.

**Arguments:**

- `val`: The export directory and filename pattern (e.g. `"xml_export.pretty/[xml_export.filename]"`).
- `all_files`: Set to `True` to get the export for all source files. Default: `False`


## HeaderAnnotations
Iterable containing header annotations from the source to be included in the export. This list is defined in the corpus
configuration.

**Arguments:**

- `config_name`: The config variable pointing out what header annotations to include.


## HeaderAnnotationsAllSourceFiles
Iterable containing header annotations from the source to be included in the export. This list is defined in the corpus
configuration. This differs from `HeaderAnnotations` in that the header annotations file (created by using
`Headers`) of _every_ source file will be added as dependencies.

**Arguments:**

- `config_name`: The config variable pointing out what source annotations to include.


## Headers
List of header annotation names for a given source file.

**Arguments:**

- The name of the source file.

**Methods:**

- `read()`: Read the headers file and return a list of header annotation names.
- `write(header_annotations: List[str])`: Write headers file.
- `exists()`: Return True if headers file exists for this source file.
- `remove()`: Remove headers file.


## Language
In instance of this class holds information about the language of the corpus. This information is retrieved from the
corpus configuration and is specified as ISO 639-3 code.


## Marker
Similar to `AnnotationCommonData`, but usually without any actual data. Markers are simply used to tell if something has
been run. Created by using `OutputMarker`.

**Arguments:**

- `name`: The name of the marker.

**Methods:**

- `read()`: Read arbitrary corpus level string data from marker file.
- `exists()`: Return True if marker file exists.
- `remove()`: Remove marker file.


## MarkerOptional
Same as `Marker`, but if the marker file doesn't exist, it won't be created. This is mainly used to remove markers
from connected (un)installers without triggering the connected (un)installation.


## Model
An instance of this class holds a path to a model file relative to the Sparv model directory. This class is typically
used as input to annotator functions.

**Arguments**:
- `name`: The path to the model file relative to the model directory.

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
- `source_file`: The name of the source file.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(values, append: bool = False, allow_newlines: bool = False, source_file: Optional[str] = None)`: Write an
  annotation to file. Existing annotation will be overwritten. 'values' should be a list of values.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.


## OutputAllSourceFiles
Similar to [`Output`](#output) this class represents a regular annotation or attribute used as output, but the source
file must be specified for all actions.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(values, source_file: str, append: bool = False, allow_newlines: bool = False)`: Write an annotation to file.
   Existing annotation will be overwritten. 'values' should be a list of values.
- `exists(source_file: str)`: Return True if annotation file exists.
- `remove(source_file: str)`: Remove annotation file.


## OutputCommonData
Similar to [`OutputData`](#outputdata) but for a data annotation that is valid for the whole corpus.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, append: bool = False)`: Write arbitrary corpus level string data to annotation file.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.


## OutputData
This class represents an annotation holding arbitrary data (i.e. data that is not tied to spans in the corpus text) that
is used as output.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.
- `source_file`: The name of the source file.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, append: bool = False)`: Write arbitrary corpus level string data to annotation file.
- `exists()`: Return True if annotation file exists.
- `remove()`: Remove annotation file.


## OutputDataAllSourceFiles
Like [`OutputData`](#outputdata), this class is used for annotations holding arbitrary data and that is used as output,
but the source file must be specified for all actions.

**Arguments**:
- `name`: The name of the annotation.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `split()`: Split name into annotation name and attribute.
- `write(value, source_file: str, append: bool = False)`: Write arbitrary corpus level string data to annotation file.
- `exists(source_file: str)`: Return True if annotation file exists.
- `remove(source_file: str)`: Remove annotation file.


## OutputMarker
Similar to `OutputCommonData`, but usually without any actual data. Markers are simply used to tell that something has
been run, usually used by functions that don't have any natural output, like installers and uninstallers.

**Arguments**:
- `name`: The name of the marker.
- `cls`: The annotation class of the output.
- `description`: An optional description.

**Methods:**

- `write(value = "")`: Write arbitrary corpus level string data to marker file. Usually called without arguments.
- `exists()`: Return True if marker file exists.
- `remove()`: Remove marker file.


## Source
An instance of this class holds a path to the directory containing input files.

**Arguments:**

- Path to directory containing input files.

**Methods:**

- `get_path(source_file: SourceFilename, extension: str)`: Get path to a specific source file.


## SourceAnnotations
Iterable containing source annotations to be included in the export. This list is defined in the corpus configuration.

**Arguments:**

- `config_name`: The config variable pointing out what source annotations to include.


## SourceAnnotationsAllSourceFiles
Iterable containing source annotations to be included in the export. This list is defined in the corpus configuration.
This differs from `SourceAnnotations` in that the source annotations structure file (created by using `SourceStructure`)
of _every_ source file will be added as dependencies.

**Arguments:**

- `config_name`: The config variable pointing out what source annotations to include.


## SourceStructure
Every annotation name available in a source file.

**Arguments:**

- The name of the source file.

**Methods:**

- `read()`: Read structure file.
- `write(structure)`: Sort the source file's annotation names and write to structure file.


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

- `source_file`: The name of the source file.

**Methods:**

- `read()`: Get corpus text.
- `write(text)`: Write text to the designated file of a corpus. `text` is a unicode string.


## Wildcard
An instance of this class holds wildcard information. It is typically used in the `wildcards` list passed as an argument
to the [`@annotator` decorator](developers-guide/sparv-decorators.md#annotator), e.g.:
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
