"""Model builders for older Swedish lexicons."""

import logging

import sparv.util as util
from sparv.util.lmflexicon import lmf_to_pickle
from sparv import ModelOutput, modelbuilder

log = logging.getLogger(__name__)


@modelbuilder("Dalin morphology model")
def build_dalin(out: str = ModelOutput("hist/dalin.pickle")):
    """Download Dalin morphology XML and save as a pickle file."""
    # Download dalinm.xml
    xml_path = "hist/dalinm.xml"
    util.download_model("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml", xml_path)

    # Create pickle file
    lmf_to_pickle(util.get_model_path(xml_path), out)

    # Clean up
    util.remove_model_files([xml_path])


@modelbuilder("Dalin morphology model")
def build_swedberg(out: str = ModelOutput("hist/swedberg.pickle")):
    """Download Dalin morphology XML and save as a pickle file."""
    # Download diapivot.xml
    xml_path = "hist/swedbergm.xml"
    util.download_model("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml", xml_path)

    # Create pickle file
    lmf_to_pickle(util.get_model_path(xml_path), out)

    # Clean up
    util.remove_model_files([xml_path])
