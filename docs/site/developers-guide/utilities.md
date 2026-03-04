# Utilities

Sparv provides a variety of utility functions, classes, and constants that are useful across different modules. These
utilities are primarily imported from `sparv.api.util` and its submodules. For example:

```python
from sparv.api.util.system import call_binary
```

## Constants

The `sparv.api.util.constants` module includes several predefined constants that are used throughout the Sparv pipeline:

- `DELIM = "|"`: Delimiter character used to separate ambiguous results.
- `AFFIX = "|"`: Character used to enclose results, marking them as a set.
- `SCORESEP = ":"`: Character that separates an annotation from its score.
- `COMPSEP = "+"`: Character used to separate parts of a compound.
- `UNDEF = "__UNDEF__"`: Value representing undefined annotations.
- `OVERLAP_ATTR = "overlap"`: Name for automatically created overlap attributes.
- `SPARV_DEFAULT_NAMESPACE = "sparv"`: Default namespace used when annotation names collide and `sparv_namespace` is not
  set in the configuration.
- `UTF8 = "UTF-8"`: UTF-8 encoding.
- `LATIN1 = "ISO-8859-1"`: Latin-1 encoding.
- `HEADER_CONTENTS = "contents"`: Name of the annotation containing header contents.

## Export Utils

::: sparv.api.util.export
    options:
      show_root_toc_entry: false
      heading_level: 3

## Install/Uninstall Utils

::: sparv.api.util.install
    options:
      show_root_toc_entry: false
      heading_level: 3

## System Utils

::: sparv.api.util.system
    options:
      show_root_toc_entry: false
      heading_level: 3

## Tag Sets

The `sparv.api.util.tagsets` subpackage includes modules with functions and objects for tag set conversions.

::: sparv.api.util.tagsets.tagmappings.join_tag
    options:
      show_root_toc_entry: false
      heading_level: 3

### tagmappings.join_tag()

Convert a complex SUC or SALDO tag record into a string.

**Parameters**:

- `tag`: The tag to convert, which can be a dictionary (`{'pos': pos, 'msd': msd}`) or a tuple (`(pos, msd)`).
- `sep`: The separator to use. Default: "."

### tagmappings.mappings

Mappings of part-of-speech tags between different tag sets.

### pos_to_upos()

Map part-of-speech tags to Universal Dependency part-of-speech tags. This function only works if there is a conversion
function in `util.tagsets.pos_to_upos` for the specified language and tag set.

**Parameters**:

- `pos`: The part-of-speech tag to convert.
- `lang`: The language code.
- `tagset`: The name of the tag set to which `pos` belongs.

### tagmappings.split_tag()

Split a SUC or Saldo tag string ('X.Y.Z') into a tuple ('X', 'Y.Z'), where 'X' is the part of speech and 'Y', 'Z', etc.,
are morphological features (i.e., MSD tags).

**Parameters**:

- `tag`: The tag string to split into a tuple.
- `sep`: The separator to split on. Default: "."

### suc_to_feats()

Convert SUC MSD tags into a UCoNNL feature list (universal morphological features). Returns a list of universal
features.

**Parameters**:

- `pos`: The SUC part-of-speech tag.
- `msd`: The SUC MSD tag.
- `delim`: The delimiter separating the features in `msd`. Default: "."

### tagmappings.tags

Different sets of part-of-speech tags.

## Miscellaneous Utils

::: sparv.api.util.misc
    options:
      show_root_toc_entry: false
      heading_level: 3
      filters:
        - "!^chain$"

::: sparv.core.misc.parse_annotation_list
    options:
      show_root_toc_entry: true
      show_root_heading: true
      heading: parse_annotation_list
      heading_level: 3

## Error Messages and Logging

The `SparvErrorMessage` exception and `get_logger` function are essential components of the Sparv pipeline. Unlike other
utilities mentioned on this page, they are located directly under `sparv.api`.

### SparvErrorMessage

This exception class is used to halt the pipeline, while notifying users of errors in a user-friendly manner without
displaying a traceback. Its usage is detailed in the [Writing Sparv Plugins](writing-sparv-plugins.md#error-messages)
section.

> [!NOTE]
>
> When raising this exception in a Sparv module, only the `message` argument should be used.

::: sparv.api.SparvErrorMessage
    options:
      show_root_toc_entry: false
      show_docstring_description: false
      show_bases: false

### get_logger

This function retrieves a logger that is a child of `sparv.modules`. Its usage is explained in the [Writing Sparv
Plugins](writing-sparv-plugins.md#logging) section.

:::sparv.api.get_logger
    options:
      show_root_toc_entry: false
      show_docstring_description: false
