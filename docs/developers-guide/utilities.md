# Utilities

These utility functions, classes and constants can be imported from `sparv.util`, e.g.:
```python
from sparv.util import UTF8
```


## Constants

- `DELIM = "|"`
  Delimiter char to put between ambiguous results
- `AFFIX = "|"`
  Character to put before and after results to mark a set
- `SCORESEP = ":"`
  Character that separates an annotation from a score
- `COMPSEP = "+"`
  Character to separate compound parts
- `UNDEF = "__UNDEF__"`
  Value for undefined annotations
- `OVERLAP_ATTR = "overlap"`
  Name for automatically created overlap attributes
- `SPARV_DEFAULT_NAMESPACE = "sparv"`
  Namespace to be used in case annotation names collide and sparv_namespace is not set in config
- `UTF8 = "UTF-8"`
  UTF-8 encoding
- `LATIN1 = "ISO-8859-1"`
  Latin-1 encoding
- `HEADER_CONTENTS = "contents"`
  Name of annotation containing header contents


## Export Utils

### gather_annotations()
### get_annotation_names()
### get_header_names()
### scramble_spans()


## Install Utils

### install_directory()`
### install_file()`
### install_mysql()`


## System Utils

### call_binary()
### call_java()
### clear_directory()
### find_binary()
### kill_process()
### rsync()


## Tagsets

### tagsets.pos_to_upos()
Map POS tags to Universal Depenendy POS tags. This only works if there is a conversion function in `util.pos_to_upos`
for the given language and tagset.

**Arguments:**
- `pos`: The part-of-speech tag to convert.
- `lang`: The language code.
- `tagset`: The name of the tagset that `pos` belongs to.


## Miscellaneous Utils

<!-- ### chain() -->


### cwbset()
Take an iterable object and return a set in the format used by Corpus Workbench.

**Arguments:**
- `values`: An iterable containing some string values.
- `delimiter`: Character that delimits the elements in the resulting set. Default: "|"
- `affix`: Character that the resulting set starts and ends with. that Default: "|"
- `sort: Set to `True` if you want to values to be sorted. Default: `False`
- `maxlength`: Maximum length in characters for the resulting set. Default: 4095
- `encoding`: Encoding of `values`. Default: "UTF-8"


### get_logger()
Get a logger that is a child of `sparv.modules`.

**Arguments:**
- `name`: The name of the current module (usually `__name__`)


### parse_annotation_list()
Take a list of annotation names and possible export names, and return a list of tuples. Each list item will be split
into a tuple by the string ' as '. Each tuple will contain 2 elements. If there is no ' as ' in the string, the second
element will be None.

**Arguments:**
- `annotation_names`: List of annotations.
- `all_annotations`: List of annotations. If there is an element called '...' everything from all_annotations will be
  included in the result, except for the elements that are prefixed with 'not '. Default: `[]`
- `add_plain_annotations`: Plain annotations (without attributes) will be added if needed, unless add_plain_annotations
  is set to False. Make sure to disable add_plain_annotations if the annotation names may include classes or config
  variables. Default: `True`


### PickledLexicon
Class for reading basic pickled lexicon and looking up keys.

**Arguments:**
- default argument: A `pathlib.Path` or `Model` object pointing to a pickled lexicon.
- `verbose`: Logs status updates upon reading the lexicon if set to `True`. Default: `True`

**Methods:**
- `lookup(key, default=set())`: Look up `key` in the lexicon. Return `default` if `key` is not found.


### remove_control_characters()
Remove control characters from `text`, except for those in `keep`.

**Arguments:**
- `text`: String to remove control characters from.
- `keep`: List of control characters to keep. Default: `["\n", "\t", "\r"]`


### remove_formatting_characters()
Remove formatting characters from `text`, except for those in `keep`.

**Arguments:**
- `text`: String to remove formatting characters from.
- `keep`: List of formatting characters to keep. Default: `[]`


### set_to_list()
Turn a set string into a list.

**Arguments:**
- `setstring`: A string that can be converted into a list by stripping it of `affix` and splitting the elements on
  `delimiter`.
- `delimiter`: Character that delimits the elements in `setstring`. Default: "|"
- `affix`: Character that `setstring` starts and ends with. that Default: "|"


### SparvErrorMessage
Exception (class) used to notify users of errors in a friendly way without displaying traceback.

**Arguments:**
- `message`: The error message to display.
- `module`: Name of the module where the error occurred (optional, not used in Sparv modules). Default: ""
- `function`: Name of the function where the error occurred (optional, not used in Sparv modules). Default: ""


### test_lexicon()
Test the validity of a lexicon. Takes a dictionary (lexicon) and a list of test words that are expected to occur as keys
in the lexicon. Prints the value for each test word.

**Arguments:**
- `lexicon`: A dictionary.
- `testwords`: An iterable containing strings that are expected to occur as keys in `lexicon`.
