# General Concepts

This section provides a brief overview of how Sparv modules (including plugins) work and introduces some general
concepts. More details are provided in the following chapters.

## Sparv Modules and Processors

Sparv consists of a core and various modules. These modules contain Sparv functions, or *processors*, that serve
different purposes, such as reading and parsing source files, building or downloading models, producing annotations, and
generating output files that contain the source text and annotations.

Sparv comes with a set of built-in modules, but can also be extended with custom modules, so-called *plugins*.
Technically, a plugin is a Python package that contains one or more functions decorated with Sparv
[decorators](sparv-decorators.md) that indicate their purpose. A function's parameters specify the input needed to run
the function and the output it produces. The Sparv core automatically discovers all decorated functions, scans their
parameters, and builds a registry of available modules and their dependencies and outputs.

> [!NOTE]
>
> In the Sparv documentation, the terms *module* and *plugin* are often used interchangeably. Unless otherwise
> specified, both refer to Python packages that provide Sparv functionality through decorated functions.

## Annotations

The most common processor is the [*annotator*](sparv-decorators.md#sparv.core.registry.annotator), which produces one or
more annotations. Annotations are structured data that represent linguistic or other information about the source text.
They can be either *span annotations* or *attribute annotations*. A span annotation specifies the start and end
positions of text segments, while an attribute annotation adds attributes to existing spans, providing additional
information about the text segments. For example, a function that segments a text into tokens produces a *span
annotation* that specifies where each token begins and ends in the source text. A function that produces part-of-speech
tags, on the other hand, relies on the token spans produced by another function and adds an *attribute annotation* for
each token span, indicating whether the token is a noun, verb, or another part of speech.

Annotations are named according to a strict convention. The name of a *span annotation* consists of the following parts:

- The name of the module that produces the annotation
- A period
- An arbitrary name consisting of lowercase ASCII letters, numbers, underscores, and hyphens

For example, the token span annotation produced by the `segment` module is called `segment.token`.

An *attribute annotation* is always named by combining a *span annotation* with the attribute's name. These two parts
are separated by a colon (`:`). The rules for naming the attribute itself are the same as those for naming the span
annotation. For example, the part-of-speech annotation produced by the `stanza` module is called
`segment.token:stanza.pos` because it adds part-of-speech attributes to the `segment.token` span annotation.

## Dependencies and Sparv Classes

Processors often require the output of other processors to function. For example, a part-of-speech tagger typically
needs a tokenized text as input, so it depends on a tokenizer that produces token spans. Similarly, a lemmatizer may
require part-of-speech annotations to generate the correct base forms of words. In Sparv, these dependencies are defined
through the parameters of each processor function. By using special [Sparv classes](sparv-classes.md) as default
arguments in a function's signature, the Sparv core can automatically track which annotations are produced by which
functions and in what order processors need to run.

Dependencies can be specified in two ways:

- **Module-specific dependencies:** A processor can require input from a specific module. For example, an annotator that
  produces word base forms may depend on a part-of-speech annotation with a particular tagset, and therefore specify
  that its input must be an annotation produced by a certain module.
- **Abstract dependencies:** Sometimes, the processor only needs a certain type of annotation, regardless of which
  module produces it. For example, a part-of-speech tagger usually just needs word segments as input, and it does not
  matter which module created those segments. In such cases, the dependency can be expressed using an abstract
  annotation class, described in the next section.

## Annotation Classes

When describing dependencies on other annotations, you can use annotation classes, which are written in angle brackets
(e.g., `<token>`, `<token:word>`). Annotation classes represent abstract types for common annotations such as tokens,
sentences, or text units. They make it easier to define dependencies between modules and increase the flexibility of the
annotation pipeline.

For example, many annotation modules require tokenized text as input, but do not care which tokenizer is used. Instead
of specifying a dependency on a specific module's output, a processor can declare a dependency on the `<token>` class.
In the [corpus configuration](../user-manual/corpus-configuration.md), you can then set `classes.token` to
`segment.token`, which tells Sparv that `<token>` refers to the annotation produced by the `segment` module.

Annotation classes are available across all modules and can be used wherever needed. There is no fixed set of annotation
classes, and modules can define their own as required. To see all available classes, use the `sparv classes` command
from a corpus directory.
