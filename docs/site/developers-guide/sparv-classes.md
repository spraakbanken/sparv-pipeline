---
toc_depth: 2
---
# Sparv Classes

Sparv classes are used to represent various types of data in Sparv, such as source files, models, and input and output
annotations. By using Sparv classes in the signatures of [processors](sparv-decorators.md), Sparv knows the inputs and
outputs of each processor and can build a dependency graph to determine the order in which processors should be run to
produce the desired output. Additionally, Sparv classes provide methods for reading and writing annotations, allowing
annotators to handle annotation files without needing to understand Sparv's internal data format. Below is a list of all
available Sparv classes, including their parameters, properties, and public methods.

<style>
  /* Hide the module docstring */
  article > div.doc > div.doc > p {
    display: none !important;
  }
</style>

::: sparv.api.classes
    options:
      heading_level: 2
      show_root_toc_entry: false
      members_order: alphabetical
      inherited_members: true
      show_bases: false
      show_symbol_type_heading: true
      docstring_options:
        ignore_init_summary: true
      filters:
        - "!^Base"
        - "!Mixin"
        - "!^_[^_]"
        - "!expand_variables"
        - "!__(contains|eq|hash|format|lt|repr|str)__"
