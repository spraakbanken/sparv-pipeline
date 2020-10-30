# General Concepts
This section will give a brief overview of how Sparv modules work and introduce some general concepts. More details are
provided in the following chapters.

The Sparv pipeline is comprised of some core functionality and many different modules containing Sparv functions that
serve different purposes like reading and parsing source documents, building or downloading models, segmenting texts,
producing annotations and producing output documents that contain the source text and annotations. All of these modules
(i.e. the code inside the `sparv/modules` directory) are replacable. A Sparv function is decorated with a special
[decorator](developers-guide/sparv-decorators) that tells Sparv what purpose it serves. A function's parameters hold
information about what input is needed in order to run the function and what output is produced by it. The Sparv core
automatically finds all decorated functions, scans their parameters and builds a registry for what modules are available
and how they depend on each other.

## Annotations
The most common Sparv function is the [annotator](developers-guide/sparv-decorators#annotator) which produces one or
more annotations. An annotation consists of spans that hold information about what text positions it covers and an
optional attribute for each span. For example, a function that segments a text into tokens produces a span annotation
that tells us where each token begins and ends in the source text. A function that produces part-of-speech tags on the
other hand would rely on the token spans produced by another function and just add an attribute for each token span,
telling us whether this token is a noun or a verb or something else.

Annotations are referred to by their internal names and which follow a strict naming syntax. The name of an span
annotation starts with the name of the module that it is produced by, followed by a dot, followed by an arbitrary name
consisting of lowercase ASCII letters and underscores. The token span annotation produced by the `segment` module for
example is called `segment.token`. The name of an attribute annotation follows the same rules, except that it is
prefixed by the name of the span annotation that it is adding attributes to, and a colon. So the part-of-speech
annotation produced by the `hunpos` module is called `segment.token:hunpos.pos` because it add part-of-speech attributes
to the `segment.token` span annotation.

## Dependencies
**TODO**

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

Annotation classes are valid across all modules and may be used wherever you see fit. There is no closed set of
annotation classes and each module can invent its own classes if desired. Within a corpus directory all existing classes
can be listed with the `sparv classes` command.



**TODO:** What else goes here?
