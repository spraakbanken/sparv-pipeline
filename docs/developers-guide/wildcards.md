# Wildcards

Some annotators use wildcards in their input and output. This is a useful mechanism that makes it possible for an
annotator to produce many different annotations with different wildcard values. The annotator `misc.number_by_position`
is an example of such an annotator. Its output is defined as `Output("{annotation}:misc.number_position")`. The
wildcard `{annotation}` can be replaced with any annotation and the annotator will produce a new attribute belonging to
the spans of the annotation. So if a user asks for the annotation `<sentence>:misc.number_position` (by including it in
one of the export lists in the corpus config) Sparv will add numbers to every sentence, when asking for
`document:misc.number_position` Sparv will add a number attribute to the annotation called `document` and so on.

In a way wildcards are similar to config variables as they add some level of customization to annotators. The main
difference is that a config variable is set explicitly in the corpus configuration while a wildcard receives its value
automatically when referenced in an annotation.

In the function arguments wildcards are always marked with curly brackets and they must be declared in the wildcard
argument of the `@annotator` decorator as in the following example:
```python
@annotator("Number {annotation} by position", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def number_by_position(out: Output = Output("{annotation}:misc.number_position"),
                       chunk: Annotation = Annotation("{annotation}"),
                       ...)
    ...
```

It probably goes without saying that in order for a wildcard to make sense, the same wildcard variable must be used in
the name of an input annotation (typically `Annotation`) and the name of an output annotation (e.g. `Output`) in the
same annotation function.

An annotator may also have multiple wildcards as shown in the following example:
```python
@annotator("Number {annotation} by relative position within {parent}", wildcards=[
    Wildcard("annotation", Wildcard.ANNOTATION),
    Wildcard("parent", Wildcard.ANNOTATION)
])
def number_relative(out: Output = Output("{annotation}:misc.number_rel_{parent}"),
                    parent: Annotation = Annotation("{parent}"),
                    child: Annotation = Annotation("{annotation}"),
                    ...
    ...
```
