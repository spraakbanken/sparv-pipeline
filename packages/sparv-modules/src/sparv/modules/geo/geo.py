"""Annotate geographical features."""

import pickle
from collections import defaultdict
from collections.abc import Container

from sparv.api import (
    Annotation,
    Config,
    Model,
    ModelOutput,
    Output,
    Wildcard,
    annotator,
    get_logger,
    modelbuilder,
    util,
)

logger = get_logger(__name__)


@annotator(
    "Annotate {chunk} with location data, based on locations contained within the text",
    language=["swe"],
    wildcards=[Wildcard("chunk", Wildcard.ANNOTATION)],
)
def contextual(
    out: Output = Output("{chunk}:geo.geo_context", description="Geographical places with coordinates"),
    chunk: Annotation = Annotation("{chunk}"),
    ne_type: Annotation = Annotation("swener.ne:swener.type"),
    ne_subtype: Annotation = Annotation("swener.ne:swener.subtype"),
    ne_name: Annotation = Annotation("swener.ne:swener.name"),
    model: Model = Model("[geo.model]"),
    language: Container = (),
) -> None:
    """Annotate chunks with location data, based on locations contained within the text.

    Args:
        out: Output annotation for geographical places with coordinates.
        chunk: Input chunk annotation to which location data will be added.
        ne_type: Named entity type annotation.
        ne_subtype: Named entity subtype annotation.
        ne_name: Named entity name annotation.
        model: Path to the geographical model.
        language: List of languages to use for the model.
    """
    model = load_model(model, language=language)

    ne_type_annotation = list(ne_type.read())
    ne_subtype_annotation = list(ne_subtype.read())
    ne_name_annotation = list(ne_name.read())

    children_chunk_ne, _orphans = chunk.get_children(ne_type)
    out_annotation = chunk.create_empty_attribute()

    for chunk_index, chunk_nes in enumerate(children_chunk_ne):
        chunk_locations = []
        for n in chunk_nes:
            if ne_type_annotation[n] == "LOC" and "PPL" in ne_subtype_annotation[n]:
                location_text = ne_name_annotation[n].replace("\n", " ").replace("  ", " ")
                location_data = model.get(location_text.lower())
                if location_data:
                    chunk_locations.append((location_text, list(location_data)))
                else:
                    pass
                    # logger.info("No location found for %s" % ne_name_annotation[n].replace("%", "%%"))

        chunk_locations = most_populous(chunk_locations)
        out_annotation[chunk_index] = _format_location(chunk_locations)

    out.write(out_annotation)


@annotator(
    "Annotate {chunk} with location data, based on metadata containing location names",
    config=[
        Config("geo.metadata_source", description="Source attribute for location metadata", datatype=str),
        Config("geo.model", default="geo/geo.pickle", description="Path to model", datatype=str),
    ],
    wildcards=[Wildcard("chunk", Wildcard.ANNOTATION)],
)
def metadata(
    out: Output = Output("{chunk}:geo.geo_metadata", description="Geographical places with coordinates"),
    chunk: Annotation = Annotation("{chunk}"),
    source: Annotation = Annotation("[geo.metadata_source]"),
    model: Model = Model("[geo.model]"),
    language: Container = (),
) -> None:
    """Get location data based on metadata containing location names.

    Args:
        out: Output annotation for geographical places with coordinates.
        chunk: Input chunk annotation to which location data will be added.
        source: Source attribute for location metadata.
        model: Path to the geographical model.
        language: List of languages to use for the model.
    """
    geomodel = load_model(model, language=language)

    same_target_source = chunk.split()[0] == source.split()[0]
    chunk_annotation = list(chunk.read())
    source_annotation = list(source.read())
    out_annotation = chunk.create_empty_attribute()

    # If location source and target chunk are not the same, we need
    # to find the parent/child relations between them.
    if not same_target_source:
        target_source_parents = list(source.get_parents(chunk))

    for i in range(len(chunk_annotation)):
        chunk_locations = []
        if same_target_source:
            location_source = source_annotation[i]
        else:
            location_source = (
                source_annotation[target_source_parents[i]] if target_source_parents[i] is not None else None
            )

        if location_source:
            location_data = geomodel.get(location_source.strip().lower())
            if location_data:
                chunk_locations = [(location_source, list(location_data))]

        chunk_locations = most_populous(chunk_locations)
        out_annotation[i] = _format_location(chunk_locations)

    out.write(out_annotation)


@modelbuilder("Model for geo tagging")
def build_model(out: ModelOutput = ModelOutput("geo/geo.pickle")) -> None:
    """Download and build geo model.

    Args:
        out: Output model for geographical data.
    """
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


def pickle_model(geonames: Model, alternative_names: Model, out: ModelOutput) -> None:
    """Read list of cities from Geonames dump (http://download.geonames.org/export/dump/).

    Also adds alternative names for each city.

    Args:
        geonames: Model containing geographical names.
        alternative_names: Model containing alternative names for geographical locations.
        out: Output model for geographical data in Pickle format.
    """
    logger.info("Reading geonames: %s", geonames.name)
    result = {}

    model_file = geonames.read()
    for line in model_file.split("\n"):
        if line.strip():
            (
                geonameid,
                name,
                _,
                _,
                latitude,
                longitude,
                _feature_class,
                _feature_code,
                country,
                _,
                _admin1,
                _admin2,
                _admin3,
                _admin4,
                population,
                _,
                _,
                _,
                _,
            ) = line.split("\t")

            result[geonameid] = {
                "name": name,
                "alternative_names": {},
                "latitude": latitude,
                "longitude": longitude,
                "country": country,
                "population": population,
            }

    # Parse file with alternative names of locations, paired with language codes
    logger.info("Reading alternative names: %s", alternative_names.name)

    model_file = alternative_names.read()
    for line in model_file.split("\n"):
        if line.strip():
            (
                _altid,
                geonameid,
                isolanguage,
                altname,
                _is_preferred_name,
                _is_short_name,
                _is_colloquial,
                _is_historic,
            ) = line.split("\t")
            if geonameid in result:
                result[geonameid]["alternative_names"].setdefault(isolanguage, [])
                result[geonameid]["alternative_names"][isolanguage].append(altname)

    logger.info("Saving geomodel in Pickle format")
    out.write_pickle(result)


########################################################################################################
# HELPERS
########################################################################################################


def load_model(model: Model, language: Container = ()) -> dict:
    """Load geo model and return as dict.

    Args:
        model: The model to load.
        language: Optional list of languages to filter alternative names.

    Returns:
        dict: A dictionary containing geographical data.
    """
    logger.info("Reading geomodel: %s", model)
    with model.path.open("rb") as infile:
        m = pickle.load(infile)

    result = defaultdict(set)
    for l in m.values():
        result[l["name"].lower()].add((l["name"], l["latitude"], l["longitude"], l["country"], l["population"]))
        for lang in l["alternative_names"]:
            if lang in language or not language:
                for altname in l["alternative_names"][lang]:
                    result[altname.lower()].add(
                        (l["name"], l["latitude"], l["longitude"], l["country"], l["population"])
                    )

    logger.info("Read %d geographical names", len(result))

    return result


def most_populous(locations: list) -> set:
    """Disambiguate locations by only keeping the most populous ones.

    Args:
        locations: List of locations to disambiguate.

    Returns:
        set: A set of the most populous locations.
    """
    result = set()

    for loc in locations:
        biggest = (loc[0], min(loc[1], key=lambda x: -int(x[-1])))
        result.add(biggest)
    return result


def _format_location(location_data: set) -> str:
    """Format location as city;country;latitude;longitude.

    Args:
        location_data: Set of location data to format.

    Returns:
        str: Formatted location string.
    """
    return util.misc.cwbset(";".join((y[0], y[3], y[1], y[2])) for x, y in location_data)
