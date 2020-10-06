
# Writing Sparv modules
The Sparv pipeline is comprised of different modules like importers, annotators and exporters. None of these modules are
hard-coded into the Sparv pipeline and therefore it can easily be extended.

When writing a Sparv module one basically creates a Python script that imports Sparv classes (and util functions if
needed) which are needed for describing dependencies to other entities (e.g. annotations or models) handled or created
by the pipeline.

Here is an example of a minimal annotation module that converts tokens to uppercase:

```python
from sparv import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

- vad importeras? Importera bara från sparv!
- en modul är en funktion som dekoreras med lämplig dekorator (som tar argument...)
- det som beskriver en funktions relation till annat i pipelinen är funktionens signatur, genom typehints anges vad
  varje argument har för funktion (input, output, modeller, beroenden...). Rerefera till exemplet.
- funktionen du skriver kommer anropas automatisk av Sparv, ingen annan annoterare kommer att anropa den direkt, och du
  behöver aldrig anropa någon annan annoterare direkt. Vilka moduler som körs beräknas automatiskt av en beroendegraf.
- Instanserna av klasserna som finns i funktionssignaturen har metoder för att läsa och skriva till filer etc. Ingen
  modul ska skriva annotationsfiler själv, Sparvs util-funktioner ska fixa detta. Man behöver inte bekymra sig om Sparvs
  interna dataformat. Detta för att det ska vara framtidssäkert (om Sparvs format ändras, ska inte modulerna behöva
  uppdateras). Peka på read() och write() i exemplet. Peka även på fullständig lista av bös längre ner i dokumentet.
- Nånting om classes... Det är fritt fram för varje modul att hitta på egna klasser, det finns ingen closed lista över
  klasser (dock får de som finns användas med fördel)
