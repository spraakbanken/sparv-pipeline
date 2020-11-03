# Writing Sparv Modules
When writing your first Sparv module a good starting point may be to take a look at an existing module that does
something similar to your goal.

The Sparv pipeline is comprised of different modules like importers, annotators and exporters. None of these modules are
hard-coded into the Sparv pipeline and therefore it can easily be extended.

A Sparv module is a Python script that imports [Sparv classes](developers-guide/sparv-classes) (and [util
functions](developers-guide/util-functions) if needed) which are used for describing dependencies to other entities
(e.g. annotations or models) handled or created by the pipeline. Here is an example of a small annotation module that
converts tokens to uppercase:
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
`out.write()` in the example). A Sparv module should never read or write any files without using the provided class
methods. This is to make sure that files are written to the correct places in the file structure so that they can be
found by other modules. The read and write methods also make sure that Sparv's internal data format is handled
correctly. Not using these provided methods can lead to procedures breaking if the internal data format or file
structure is updated in the future.


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

By default Sparv will write log output with level WARNING and higher to the terminal. You can change the log level with
the flag `--log [LOGLEVEL]`. Most commands support this flag. You can also choose to write the log output to a file by
using the `--log-to-file [LOGLEVEL]` flag. The log file will recieve the current date and timestamp as filename and can
be found inside `logs` in the corpus directory.


## Plugins
A Sparv Plugin is a Sparv module that is not stored together with the Sparv code. Instead it usually lives in a separate
repository. Reasons for writing a plugin could be that the author does not want it to be part of the Sparv core or that
the code cannot be distributed under the same license. Any Sparv module can be converted into a plugin by adding a
[Python setup script](https://docs.python.org/3/distutils/setupscript.html).

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

In the above example the `freeling` folder is basically a Sparv module. The `setup.py` is what really makes this behave
as a plugin. If the `setup.py` is constructed correctly, the plugin code can then be injected into the Sparv pipeline
code using pipx:
```bash
pipx inject sparv-pipeline ./sparv-freeling
```

In order for this to work you need to make sure that there is a `sparv.plugin` entry point inside the setup script that
points to your module(s):
```python
entry_points={"sparv.plugin": ["freeling = freeling"]}
```

Now the plugin functionality should be available and it should be treated just like any other module within the Sparv
pipeline.
