# -*- coding: utf-8 -*-

"""
Annotates geographical features.
"""

import sparv.util as util
import sparv.parent as parent
import sparv.annotate as annotate
import pickle
from collections import defaultdict


def build_model(geonames, alternate_names, out, protocol=-1):
    """Read list of cities from Geonames dump (http://download.geonames.org/export/dump/).
    Add alternate names for each city."""

    util.log.info("Reading geonames: %s", geonames)
    result = {}
    with open(geonames, encoding="UTF-8") as model_file:
        for line in model_file:
            geonameid, name, _, _, latitude, longitude, feature_class, feature_code, country, _, admin1, admin2, admin3, admin4, population, _, _, _, _ = line.split("\t")

            result[geonameid] = {
                "name": name,
                "alternate_names": {},
                "latitude": latitude,
                "longitude": longitude,
                "country": country,
                "population": population
            }

    # Parse file with alternate names of locations, paired with language codes
    util.log.info("Reading alternate names: %s", alternate_names)

    with open(alternate_names, encoding="UTF-8") as model_file:
        for line in model_file:
            altid, geonameid, isolanguage, altname, is_preferred_name, is_short_name, is_colloquial, is_historic = line.split("\t")
            if geonameid in result:
                result[geonameid]["alternate_names"].setdefault(isolanguage, [])
                result[geonameid]["alternate_names"][isolanguage].append(altname)

    util.log.info("Saving geomodel in Pickle format")

    with open(out, "wb") as outfile:
        pickle.dump(result, outfile, protocol=protocol)

    util.log.info("OK, saved")


def load_model(model, language=()):
    util.log.info("Reading geomodel: %s", model)
    with open(model, "rb") as infile:
        m = pickle.load(infile)

    result = defaultdict(set)
    for geonameid, l in list(m.items()):
        result[l["name"].lower()].add((l["name"], l["latitude"], l["longitude"], l["country"], l["population"]))
        for lang in l["alternate_names"]:
            if lang in language or not language:
                for altname in l["alternate_names"][lang]:
                    result[altname.lower()].add((l["name"], l["latitude"], l["longitude"], l["country"], l["population"]))

    util.log.info("Read %d geographical names", len(result))

    return result


def most_populous(locations):
    """Disambiguate locations by only keeping the most populous ones."""
    new_locations = {}

    for chunk in locations:
        new_locations[chunk] = set()

        for l in locations[chunk]:
            biggest = (l[0], sorted(l[1], key=lambda x: -int(x[-1]))[0])
            new_locations[chunk].add(biggest)
    return new_locations


def _format_location(location_data):
    """Format location as city;country;latitude;longitude"""
    return util.cwbset(";".join((y[0], y[3], y[1], y[2])) for x, y in location_data)


def contextual(out, chunk, context, ne, ne_subtype, text, model, method="populous", language=[], encoding="UTF-8"):
    """Annotate chunks with location data, based on locations contained within the text.
    context = text chunk to use for disambiguating places (when applicable).
    chunk = text chunk to which the annotation will be added.
    """

    if isinstance(language, str):
        language = language.split()

    model = load_model(model, language=language)

    text = util.read_corpus_text(text)
    chunk = util.read_annotation(chunk)
    context = util.read_annotation(context)
    ne = util.read_annotation(ne)
    ne_text = annotate.text_spans(text, ne, None)
    ne_subtype = util.read_annotation(ne_subtype)

    children_context_chunk = parent.annotate_children(text, None, context, chunk, ignore_missing_parent=True)
    children_chunk_ne = parent.annotate_children(text, None, chunk, ne, ignore_missing_parent=True)

    result = {}

    for cont, chunks in list(children_context_chunk.items()):
        all_locations = []  # TODO: Maybe not needed for anything?
        context_locations = []
        chunk_locations = defaultdict(list)

        for ch in chunks:
            for n in children_chunk_ne[ch]:
                if ne[n] == "LOC" and "PPL" in ne_subtype[n]:
                    location_text = ne_text[n].replace("\n", " ").replace("  ", " ")
                    location_data = model.get(location_text.lower())
                    if location_data:
                        all_locations.append((location_text, list(location_data)))
                        context_locations.append((location_text, list(location_data)))
                        chunk_locations[ch].append((location_text, list(location_data)))
                    else:
                        pass
                        # util.log.info("No location found for %s" % ne_text[n].replace("%", "%%"))

        chunk_locations = most_populous(chunk_locations)

        for c in chunks:
            result[c] = _format_location(chunk_locations.get(c, ()))

    util.write_annotation(out, result)


def metadata(out, chunk, source, model, text=None, method="populous", language=[], encoding="UTF-8"):
    """Get location data based on metadata containing location names.
    """

    if isinstance(language, str):
        language = language.split()

    model = load_model(model, language=language)

    same_target_source = chunk == source
    chunk = util.read_annotation(chunk)
    source = util.read_annotation(source)

    # If location source and target chunk are not the same, we need
    # to find the parent/child relations between them.
    if not same_target_source and text:
        text = util.read_corpus_text(text)
        target_source_parents = parent.annotate_parents(text, None, source, chunk, ignore_missing_parent=True)

    result = {}
    chunk_locations = {}

    for c in chunk:
        if same_target_source:
            location_source = source.get(c)
        else:
            location_source = source.get(target_source_parents.get(c))

        if location_source:
            location_data = model.get(location_source.strip().lower())
            if location_data:
                chunk_locations[c] = [(location_source, list(location_data))]
        else:
            chunk_locations[c] = []

    chunk_locations = most_populous(chunk_locations)

    for c in chunk:
        result[c] = _format_location(chunk_locations.get(c, ()))

    util.write_annotation(out, result)


if __name__ == '__main__':
    util.run.main(contextual,
                  metadata=metadata,
                  build_model=build_model
                  )
