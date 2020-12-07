"""Annotate geographical features."""

import logging
import pickle
from collections import defaultdict

import sparv.util as util
from sparv import Annotation, Config, Model, ModelOutput, Output, Wildcard, annotator, modelbuilder

log = logging.getLogger(__name__)


@annotator("Annotate {chunk} with location data, based on locations contained within the text", language=["swe"],
           config=[
               Config("geo.context_chunk", default="<sentence>",
                      description="Text chunk (annotation) to use for disambiguating places")
           ], wildcards=[Wildcard("chunk", Wildcard.ANNOTATION)])
def contextual(out: Output = Output("{chunk}:geo.geo_context", description="Geographical places with coordinates"),
               chunk: Annotation = Annotation("{chunk}"),
               context: Annotation = Annotation("[geo.context_chunk]"),
               ne_type: Annotation = Annotation("swener.ne:swener.type"),
               ne_subtype: Annotation = Annotation("swener.ne:swener.subtype"),
               ne_name: Annotation = Annotation("swener.ne:swener.name"),
               model: Model = Model("[geo.model]"),
               method: str = "populous",
               language: list = []):
    """Annotate chunks with location data, based on locations contained within the text.

    context = text chunk to use for disambiguating places (when applicable).
    chunk = text chunk to which the annotation will be added.
    """
    model = load_model(model, language=language)

    ne_type_annotation = list(ne_type.read())
    ne_subtype_annotation = list(ne_subtype.read())
    ne_name_annotation = list(ne_name.read())

    children_context_chunk, _orphans = context.get_children(chunk)
    children_chunk_ne, _orphans = chunk.get_children(ne_type)

    out_annotation = chunk.create_empty_attribute()

    for chunks in children_context_chunk:
        all_locations = []  # TODO: Maybe not needed for anything?
        context_locations = []
        chunk_locations = defaultdict(list)

        for ch in chunks:
            for n in children_chunk_ne[ch]:
                if ne_type_annotation[n] == "LOC" and "PPL" in ne_subtype_annotation[n]:
                    location_text = ne_name_annotation[n].replace("\n", " ").replace("  ", " ")
                    location_data = model.get(location_text.lower())
                    if location_data:
                        all_locations.append((location_text, list(location_data)))
                        context_locations.append((location_text, list(location_data)))
                        chunk_locations[ch].append((location_text, list(location_data)))
                    else:
                        pass
                        # log.info("No location found for %s" % ne_name_annotation[n].replace("%", "%%"))

        chunk_locations = most_populous(chunk_locations)

        for c in chunks:
            out_annotation[c] = _format_location(chunk_locations.get(c, ()))

    out.write(out_annotation)


@annotator("Annotate {chunk} with location data, based on metadata containing location names", config=[
    Config("geo.metadata_source", default="", description="Source attribute for location metadata"),
    Config("geo.model", default="geo/geo.pickle", description="Path to model")
], wildcards=[Wildcard("chunk", Wildcard.ANNOTATION)])
def metadata(out: Output = Output("{chunk}:geo.geo_metadata", description="Geographical places with coordinates"),
             chunk: Annotation = Annotation("{chunk}"),
             source: Annotation = Annotation("[geo.metadata_source]"),
             model: Model = Model("[geo.model]"),
             method: str = "populous",
             language: list = []):
    """Get location data based on metadata containing location names."""
    geomodel = load_model(model, language=language)

    same_target_source = chunk.split()[0] == source.split()[0]
    chunk_annotation = list(chunk.read())
    source_annotation = list(source.read())

    # If location source and target chunk are not the same, we need
    # to find the parent/child relations between them.
    if not same_target_source:
        target_source_parents = list(source.get_parents(chunk))

    chunk_locations = {}

    for i, _ in enumerate(chunk_annotation):
        if same_target_source:
            location_source = source_annotation[i]
        else:
            location_source = source_annotation[target_source_parents[i]] if target_source_parents[
                i] is not None else None

        if location_source:
            location_data = geomodel.get(location_source.strip().lower())
            if location_data:
                chunk_locations[i] = [(location_source, list(location_data))]
        else:
            chunk_locations[i] = []

    chunk_locations = most_populous(chunk_locations)

    out_annotation = chunk.create_empty_attribute()
    for c in chunk_locations:
        out_annotation[c] = _format_location(chunk_locations.get(c, ()))

    out.write(out_annotation)


@modelbuilder("Model for geo tagging")
def build_model(out: ModelOutput = ModelOutput("geo/geo.pickle")):
    """Download and build geo model."""
    # Download and extract cities1000.txt
    cities_zip = Model("geo/cities1000.zip")
    cities_zip.download("http://download.geonames.org/export/dump/cities1000.zip")
    cities_zip.unzip()

    # Download and extract alternateNames.txt
    names_zip = Model("geo/alternateNames.zip")
    names_zip.download("http://download.geonames.org/export/dump/alternateNames.zip")
    names_zip.unzip()

    pickle_model(Model("geo/cities1000.txt"), Model("geo/alternateNames.txt"), out)

    # Clean up
    cities_zip.remove()
    names_zip.remove()
    Model("geo/iso-languagecodes.txt").remove()
    Model("geo/cities1000.txt").remove()
    Model("geo/alternateNames.txt").remove()


def pickle_model(geonames, alternative_names, out):
    """Read list of cities from Geonames dump (http://download.geonames.org/export/dump/).

    Add alternative names for each city.
    """
    log.info("Reading geonames: %s", geonames.name)
    result = {}

    model_file = geonames.read()
    for line in model_file.split("\n"):
        if line.strip():
            geonameid, name, _, _, latitude, longitude, _feature_class, _feature_code, \
                country, _, _admin1, _admin2, _admin3, _admin4, population, _, _, _, _ = line.split("\t")

            result[geonameid] = {
                "name": name,
                "alternative_names": {},
                "latitude": latitude,
                "longitude": longitude,
                "country": country,
                "population": population
            }

    # Parse file with alternative names of locations, paired with language codes
    log.info("Reading alternative names: %s", alternative_names.name)

    model_file = alternative_names.read()
    for line in model_file.split("\n"):
        if line.strip():
            _altid, geonameid, isolanguage, altname, _is_preferred_name, _is_short_name, \
                _is_colloquial, _is_historic = line.split("\t")
            if geonameid in result:
                result[geonameid]["alternative_names"].setdefault(isolanguage, [])
                result[geonameid]["alternative_names"][isolanguage].append(altname)

    log.info("Saving geomodel in Pickle format")
    out.write_pickle(result)


########################################################################################################
# HELPERS
########################################################################################################


def load_model(model: Model, language=()):
    """Load geo model and return as dict."""
    log.info("Reading geomodel: %s", model)
    with open(model.path, "rb") as infile:
        m = pickle.load(infile)

    result = defaultdict(set)
    for _geonameid, l in list(m.items()):
        result[l["name"].lower()].add((l["name"], l["latitude"], l["longitude"], l["country"], l["population"]))
        for lang in l["alternative_names"]:
            if lang in language or not language:
                for altname in l["alternative_names"][lang]:
                    result[altname.lower()].add(
                        (l["name"], l["latitude"], l["longitude"], l["country"], l["population"]))

    log.info("Read %d geographical names", len(result))

    return result


def most_populous(locations):
    """Disambiguate locations by only keeping the most populous ones."""
    new_locations = {}

    for chunk in locations:
        new_locations[chunk] = set()

        for loc in locations[chunk]:
            biggest = (loc[0], sorted(loc[1], key=lambda x: -int(x[-1]))[0])
            new_locations[chunk].add(biggest)
    return new_locations


def _format_location(location_data):
    """Format location as city;country;latitude;longitude."""
    return util.cwbset(";".join((y[0], y[3], y[1], y[2])) for x, y in location_data)
