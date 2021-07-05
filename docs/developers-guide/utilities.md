# Utilities

Sparv has a number of utility functions, classes and constants that are not specific to any particular module.
Most of them are imported from `sparv.api.util` and its submodules, e.g.:
```python
from sparv.api.util.system import call_binary
```


## Constants
`sparv.api.util.constants` contains the following constants:

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
  Namespace to be used in case annotation names collide and `sparv_namespace` is not set in config
- `UTF8 = "UTF-8"`
  UTF-8 encoding
- `LATIN1 = "ISO-8859-1"`
  Latin-1 encoding
- `HEADER_CONTENTS = "contents"`
  Name of annotation containing header contents


## Export Utils
`sparv.api.util.export` provides util functions used for preparing data for export.

### gather_annotations()
Calculate the span hierarchy and the annotation_dict containing all annotation elements and attributes. Returns a
`spans_dict` and an `annotation_dict` if `flatten` is set to `True`, otherwise `span_positions` and `annotation_dict`.

**Arguments:**

- `annotations`: A list of annotations to include.
- `export_names`: Dictionary that maps from annotation names to export names.
- `header_annotations`: A list of header annotations.
- `doc`: The document name.
- `flatten`: Whether to return the spans as a flat list. Default: `True`
- `split_overlaps`: Whether to split up overlapping spans. Default: `False`


### get_annotation_names()
Get a list of annotations, token attributes and a dictionary with translations from annotation names to export names.

**Arguments:**

- `annotations`: List of elements:attributes (annotations) to include.
- `source_annotations`: List of elements:attributes from the original document to include. If not specified, everything
  will be included.
- `doc`: Name of the source document.
- `docs`: List of names of source documents (alternative to `doc`).
- `token_name`: Name of the token annotation.
- `remove_namespaces`: Remove all namespaces in export_names unless names are ambiguous. Default: `False`
- `keep_struct_names`: For structural attributes (anything other than token), include the annotation base name
  (everything before ":") in export_names (used in cwb encode). Default: `False`
- `sparv_namespace`: The namespace to be added to all Sparv annotations.
- `source_namespace`: The namespace to be added to all annotations present in the source.


### get_header_names()
Get a list of header annotations and a dictionary for renamed annotations.

**Arguments:**

- `header_annotation_names`: List of header elements:attributes from the original document to include. If not specified,
  everything will be included.
- `doc`: Name of the source document.
- `docs`: List of names of source documents (alternative to `doc`).


### scramble_spans()
Reorder chunks according to `chunk_order` and open/close tags in the correct order.

**Arguments:**

- `span_positions`: The original span positions (usually retrieved from [`gather_annotations()`](#gather_annotations)).
- `chunk_name`: The name of the annotation to scramble on.
- `chunk_order`: Annotation containing the new order of the chunk.


## Install Utils
`sparv.api.util.install` provides util functions used for installing corpora onto remote locations.


### install_directory()
Rsync every file from a local directory to a target host. The target path is extracted from filenames by replacing "#"
with "/".

**Arguments:**

- `host`: The remote host to install to.
- `directory`: The directory to sync.


### install_file()
Rsync a file to a target host.

**Arguments:**

- `local_file`: Path to the local file to sync.
- `host`: The remote host to install to.
- `remote_file`: The name of the resulting file on the remote host.


### install_mysql()
Insert tables and data from local SQL-file to remote MySQL database.

**Arguments:**

- `host`: The remote host to install to.
- `db_name`: Name of the remote database.
- `sqlfile`: Path to a local SQL file, or multiple paths separated by whitespaces.


### install_mysql_dump()
Copy selected tables (including data) from local to remote MySQL database.

**Arguments:**

- `host`: The remote host to install to.
- `db_name`: Name of the remote database.
- `tables`: Names of SQL tables to be copied separated by whitespaces.


## System Utils
`sparv.api.util.system` provides functions related to starting and stopping processes, creating directories etc.


### call_binary()
Call a binary with `arguments` and `stdin` and return a pair `(stdout, stderr)`.

**Arguments:**

- `name`: Name of the binary call.
- `arguments`: Arguments to pass to the call. Defaults to `()`.
- `stdin`: Stdin input to pass to the call. Defaults to `""`.
- `raw_command`: Don't use this unless you really have to! String holding the raw command that will be executed through
  the shell. Defaults to `None`.
- `search_paths`: List of paths where to look for the binary `name`, in addition to the environment variable PATH.
  Defaults to `()`.
- `encoding`: Encoding to use for `stdin`. Defaults to `None`.
- `verbose`: If set to `True` pipes all stderr output from the subprocess to stderr in the terminal, and an empty string
  is returned as the stderr component. Defaults to `False`.
- `use_shell`: Don't use this unless you really have to! If set to `True` the binary will be executed through the shell.
  Defaults to `False`. Is automatically set to `True` when using `raw_command`.
- `allow_error`: If set to `False` an exeption is raised if stderr is not empty and stderr and stdout will be logged.
  Defaults to `False`.
- `return_command`: If set to `True` the process is returned. Defaults to `False`.


### call_java()
Call Java with a jar file, command line arguments and stdin. Returns a pair `(stdout, stderr)`.

**Arguments:**

- `jar`: The name of the jar file to call.
- `arguments`: Arguments to pass to the call. Defaults to `()`.
- `options`: List of Java options to pass to the call. Defaults to `[]`, 
- `stdin`: Stdin input to pass to the call. Defaults to `""`.
- `search_paths`: List of paths where to look for the binary `name`, in addition to the environment variable PATH.
  Defaults to `()`.
- `encoding`: Encoding to use for `stdin`. Defaults to `None`.
- `verbose`: If set to `True` pipes all stderr output from the subprocess to stderr in the terminal, and an empty string
  is returned as the stderr component. Defaults to `False`.
- `return_command`: If set to `True` the process is returned. Defaults to `False`.


### clear_directory()
Create a new empty directory. Remove it's contents if it already exists.

**Arguments:**

- `path`: Path to the directory to be created.


### find_binary()
Search for the binary for a program. Returns the path to binary, or `None` if not found.

**Arguments:**

- `name`: Name of the binary, either a string or a list of strings with alternative names.
- `search_paths`: List of paths where to look, in addition to the environment variable PATH.
- `executable`: Set to `False` to not fail when binary is not executable. Defaults to `True`.
- `allow_dir`: Set to `True` to allow the target to be a directory instead of a file.  Defaults to `False`.
- `raise_error`: If set to `True` raises error if binary could not be found. Defaults to `False`.


### kill_process()
Kill a process, and ignore the error if it is already dead.

**Arguments:**

- `process`: The process to be killed.


### rsync()
Transfer files and/or directories using rsync. When syncing directories, extraneous files in destination dirs are
deleted.

**Arguments:**

- `local`: Path to a local file or directory.
- `host`: The remote host to rsync to.
- `remote`: Path on the remote host to rsync to. Defaults to `None`. If not provided, the path will be the same as on
  the local machine.


## Tagsets
`sparv.api.util.tagsets` is a subpackage with modules containing functions and objects related to tagset conversions.

### tagmappings.join_tag()
Convert a complex SUC or SALDO tag record into a string.

**Arguments:**

- `tag`: The tag to convert to a string. Can be a dict (`{'pos': pos, 'msd': msd}`) or a tuple (`(pos, msd)`)
- `sep`: The separator to be used. Default: "."


### tagmappings.mappings
Dictionary containing mappings (dictionaries) for of part-of-speech tag mappings between different tag sets.


### pos_to_upos()
Map POS tags to Universal Depenendy POS tags. This only works if there is a conversion function in
`util.tagsets.pos_to_upos` for the given language and tagset.

**Arguments:**

- `pos`: The part-of-speech tag to convert.
- `lang`: The language code.
- `tagset`: The name of the tagset that `pos` belongs to.


### tagmappings.split_tag()
Split a SUC or Saldo tag string ('X.Y.Z') into a tuple ('X', 'Y.Z') where 'X' is a part of speech and 'Y', 'Z' etc. are
morphologic features (i.e. MSD tags).

**Arguments:**

- `tag`: The tag string to convert into a tuple.
- `sep`: The separator to split on. Default: "."


### suc_to_feats()
Convert SUC MSD tags into UCoNNL feature list (universal morphological features). Returns a list of universal features.

**Arguments:**

- `pos`: The SUC part-of-speech tag.
- `msd`: The SUC MSD tag.
- `delim`: The delimiter separating the features in `msd`. Default: "."


### tagmappings.tags
Dictionary containing sets of part-of-speech tags.


## Miscellaneous Utils
`sparv.api.util.misc` provides miscellaneous util functions.


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


### indent_xml()
Add pretty-print indentation to an XML tree.

**Arguments:**

- `elem`: The XML tree (`xml.etree.ElementTree.Element`) to indent.
- `level`: The indentation start level. Default: `0`
- `indentation`: The indentation to add on each level. Default: '  '


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


### test_lexicon()
Test the validity of a lexicon. Takes a dictionary (lexicon) and a list of test words that are expected to occur as keys
in the lexicon. Prints the value for each test word.

**Arguments:**

- `lexicon`: A dictionary.
- `testwords`: An iterable containing strings that are expected to occur as keys in `lexicon`.


## Error Messages and Logging
The `SparvErrorMessage` exception and `get_logger` function are integral parts of the Sparv pipeline, and unlike other
utilities on this page, they are found directly under `sparv.api`.


### SparvErrorMessage
Exception (class) used to notify users of errors in a friendly way without displaying traceback. Its usage is described
in the [Writing Sparv Plugins](developers-guide/writing-sparv-plugins#error-messages) section.

> [!NOTE]
> Only the `message` argument should be used when raisning this exception in a Sparv module.

**Arguments:**

- `message`: The error message to display.
- `module`: Name of the module where the error occurred (optional, not used in Sparv modules). Default: ""
- `function`: Name of the function where the error occurred (optional, not used in Sparv modules). Default: ""


### get_logger()
Get a logger that is a child of `sparv.modules`. Its usage is described in the
[Writing Sparv Plugins](developers-guide/writing-sparv-plugins#logging) section.

**Arguments:**

- `name`: The name of the current module (usually `__name__`)
