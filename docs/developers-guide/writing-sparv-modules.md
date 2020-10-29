# Writing Sparv Modules
When writing your first Sparv module a good starting point may be to take a look at an existing module that does
something similar to your goal.

The Sparv pipeline is comprised of different modules like importers, annotators and exporters. None of these modules are
hard-coded into the Sparv pipeline and therefore it can easily be extended.

A Sparv module is a Python script that imports Sparv classes (and util functions if needed) which are used for
describing dependencies to other entities (e.g. annotations or models) handled or created by the pipeline. Here is an
example of a small annotation module that converts tokens to uppercase:
```python
from sparv import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

In this script we import two classes from Sparv (`Annotation` and `Output`) and the `annotator` decorator. Please note
that nothing should be imported from the Sparv code unless it is directly available from the sparv package (i.e. `from
sparv import ...`).

Our `uppercase` function is decorated with `@annotator` which tells Sparv that this function can be used to produce one
or more annotations. The first argument in the decorator is its description which is used for displaying help texts in
the CLI (e.g. when running `sparv modules`).

The function's relation to other pipeline components is described by its signature. The function arguments contain type
hints to the Sparv classes `Annotation` and `Output` which indicate what dependencies (e.g. annotations, models or
config variables) must be satisfied before the function can do its job, and what it will produce. In this example Sparv
will make sure that a word annotation exists before it will attempt to call the `uppercase` function because it knows
that `word` is an input as it is of type `Annotation`. It also knows that the function produces the output annotation
`<token>:custom.convert.upper`, so if any other module would request this annotation as input, it will run `uppercase`
prior to calling that module.

A function decorated with a Sparv decorator should never be actively called by you or by another decorated function.
When running Sparv through the CLI Sparv's dependency system will calculate a dependency graph and all the functions
necessary for producing the desired output will be run automatically.

Sparv classes like `Annotation` and `Output` have built-in methods for reading and writing files (like `word.read()` and
`out.write()` in the example). A Sparv module should never read or write any files without using the provided class
methods. This is to make sure that files are written to the correct places in the file structure so that they can be
found by other modules. The read and write methods also make sure that Sparv's internal data format is handled
correctly. Not using these provided methods can lead to procedures breaking if the internal data format or file
structure is updated in the future.

## Annotation Classes
When describing dependencies to other annotations one can make use of annotation classes which are denoted by angle
brackets (`<token>` and `<token:word>` in the example). Annotation classes are used to create abstract instances for
common annotations such as tokens, sentences and text units. They simplify dependencies between annotation modules and
increase the flexibility of the annotation pipeline. Many annotations modules need tokenised text as input but they
might not care about what tokeniser is being used. So instead of telling a module that it needs tokens produced by
another specific module we can tell it to take the class `<token>` as input. In the [corpus
configuration](user-manual/corpus-configuration.md) we can then set `classes.token` to `segment.token` which tells Sparv
that `<token>` refers to output produced by the segment module. In the above example we define that `word` is an input
annotation of the class `<token:word>` and `out` is an output annotation which provides new attributes for token
elements.

**TODO:** Give an example of an annotation without class (`segment.token:misc.word`)

Annotation classes are valid across all modules and may be used wherever you see fit. There is no closed set of
annotation classes and each module can invent its own classes if desired. Within a corpus directory all existing classes
can be listed with the `sparv classes` command.
