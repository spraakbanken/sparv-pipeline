# Writing Sparv Modules
When writing your first Sparv module, a good starting point may be to take a look at an existing module that does
something similar to your goal.

The Sparv pipeline is comprised of different modules like importers, annotators and exporters. None of these modules are
hard-coded into the Sparv pipeline and therefore it can easily be extended.

A Sparv module is a Python package containing at least one Python script that imports [Sparv
classes](developers-guide/sparv-classes) (and [util functions](developers-guide/utilities) if needed) which are used for
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

## Reading and Writing Files
Sparv classes like `Annotation` and `Output` have built-in methods for reading and writing files (like `word.read()` and
`out.write()` in the above example). A Sparv module should never read or write any files without using the provided
class methods. This is to make sure that files are written to the correct places in the file structure so that they can
be found by other modules. The read and write methods also make sure that Sparv's internal data format is handled
correctly. Not using these provided methods can lead to procedures breaking if the internal data format or file
structure is updated in the future.


## Init File
Each Sparv module must contain a [Python init file](https://docs.python.org/3/reference/import.html#regular-packages)
(`__init__.py`). The python scripts containing decorated Sparv functions should be imported here. Module-specific
configuration parameters may also be declared in this file. Furthermore, you should provide a short description (one
sentence) for your module in the `__init__.py` file. This description will be shown when running the `sparv modules`
command.

Example of an `__init__.py` file:
```python
"""Korp-related annotators, exporters and installers."""

from sparv import Config
from . import install_corpus, lemgram_index, relations, timespan

__config__ = [
    Config("korp.remote_host", "", description="Remote host to install to")
]
```


## Logging
Logging from Sparv modules is done with [Python's logging library](https://docs.python.org/3.6/library/logging.html).
Please use the provided `get_logger` wrapper when declaring your logger which takes care of importing the logging
library and sets the correct module name in the log output:
```python
import sparv.util as util
logger = util.get_logger(__name__)
logger.error("An error was encountered!")
```

Any of the officially [Python logging levels](https://docs.python.org/3.6/library/logging.html#levels) may be used.

By default, Sparv will write log output with level WARNING and higher to the terminal. You can change the log level with
the flag `--log [LOGLEVEL]`. Most commands support this flag. You can also choose to write the log output to a file by
using the `--log-to-file [LOGLEVEL]` flag. The log file will recieve the current date and timestamp as filename and can
be found inside `logs` in the corpus directory.


## Error Messages
When raising critical errors that should be displayed to the user (e.g. to tell the user that he/she did something
wrong) you should use the [SparvErrorMessage class](developers-guide/utilities#SparvErrorMessage). This will raise an
exception (and thus stop the current Sparv process) and notify the user of errors in a friendly way without displaying
the usual Python traceback.
```python
if not host:
    raise util.SparvErrorMessage("No host provided! Corpus not installed.")
```


## Function Order
Sometimes one may want to create multiple Sparv functions that create the same output files (e.g. annotation files,
export files or model files). In this case Sparv needs to be informed about the priority of these functions. Let's say
that there are two functions `annotate()` and `annotate_backoff()` that both produce an annotation output called
`mymodule.foo`. Ideally `mymodule.foo` should be produced by `annotate()` but if this function cannot be run for any
reason (e.g. because it needs another annotation file `mymodule.bar` that cannot be produced for some corpora), then you
want `mymodule.foo` to be produced by `annotate_backoff()`. The priority of functions is stated with the `order`
argument in the `@annotator`, `@exporter`, or `@modelbuilder` decorator. The integer value given by `order` will help
Sparv decide which function to try to use first. A lower number indicates higher priority.
```python
@annotator("Create foo annotation", order=1)
def annotate(
    out: Output = Output("mymodule.foo"),
    bar_input: Annotation = Annotation("mymodule.bar")):
    ...


@annotator("Create foo annotation for when bar is not available", order=2)
def annotate_backoff(
    out: Output = Output("mymodule.foo")):
    ...
```

<!-- Functions with a higher order number can explicitly be called with `sparv run-rule`. Not working at the moment due
to a bug! -->


## Plugins
A Sparv Plugin is a Sparv module that is not stored together with the Sparv code. Instead, it usually lives in a
separate repository. Reasons for writing a plugin could be that the author does not want it to be part of the Sparv
core or that the code cannot be distributed under the same license. Any Sparv module can be converted into a plugin
by adding a [Python setup script](https://docs.python.org/3/distutils/setupscript.html).

A working sparv plugin is the [sparv-freeling](https://github.com/spraakbanken/sparv-freeling) plugin.

The following is an example of a typical folder structure of a plugin:
```
sparv-freeling/
├── freeling
│   ├── freeling.py
│   ├── __init__.py
│   └── models.py
├── LICENSE
├── README.md
└── setup.py
```

In the above example the `freeling` folder is a Sparv module. The `setup.py` is what really makes it behave as a plugin.
If the `setup.py` is constructed correctly, the plugin code can then be injected into the Sparv pipeline code using
pipx:
```bash
pipx inject sparv-pipeline ./sparv-freeling
```

In order for this to work you need to make sure that there is a `sparv.plugin` entry point inside the setup script that
points to your module(s):
```python
entry_points={"sparv.plugin": ["freeling = freeling"]}
```

Now the plugin functionality should be available, and it should be treated just like any other module within the Sparv
pipeline.


## Preloaders
Preloader functions are used by the `sparv preload` command to speed up the annotation process. It works by
preloading the Python module together with models or processes which would otherwise need to be loaded once for every
source file.

A preload function is simply a function that takes a subset of the arguments from an annotator, and returns a value that
is passed on to the annotator. Here is an example:

```python
from sparv import Annotation, Model, Output, annotator


def preloader(model):
    """Preload POS-model."""
    return load_model(model)


@annotator("Part-of-speech tagging.",
           preloader=preloader,
           preloader_params=["model"],
           preloader_target="model_preloaded")
def pos_tag(word: Annotation = Annotation("<token:word>"),
            out: Output = Output("<token>:pos.tag"),
            model: Model = Model("pos.model"),
            model_preloaded=None):
    """Annotate tokens with POS tags."""
    if model_preloaded:
        model = model_preloaded
    else:
        model = load_model(model)
```

This annotator uses a model. It also has an extra argument called `model_preloaded` which can optionally take
an already loaded model. In the decorator we point out the preloader function using the `preloader` parameter.
`preloader_params` is a list of parameter names from the annotator, which the preloader needs as arguments. In this
case it's only one: the `model` parameter. `preloader_target` points to a single parameter name of the annotator, which
is the one that will recieve the return value from the preloader function.

When using the `sparv preload` command with this annotator, the preloader function will be run only once, and every
time the annotator is used, it will get the preloaded model via the `model_preloaded` parameter.

The three decorator parameters `preloader`, `preloader_params` and `preloader_target` are all required when adding
a preloader to an annotator. Additionally, there are two optional parameters that can be used: `preloader_shared`
and `preloader_cleanup`.

`preloader_shared` is a boolean with a default value of True. By default, Sparv will run the preloader function
only once, and if using `sparv preload` with multiple parallel processes, they will all share the result from the
preloader. By setting `preloader_shared` to False, the preloader function will instead be run once per process.
This is usually only needed when preloading processes, rather than models.

`preloader_cleanup` refers to a function, just like the `preloader` parameter. This function will be run after every
(preloaded) use of the annotator. As arguments the cleanup function should take the same arguments as the preloader
function, plus an extra argument for receiving the return value of the preloader function. It should return the same
kind of object as the preloader function, which will then be used by Sparv as the new preloaded value. This is rarely
needed, but one possible use case is when preloading a process that for some reason needs to be regularly restarted. The
cleanup function would then keep track of when restarting is needed, call the preloader function to start a new process,
and then return it.
