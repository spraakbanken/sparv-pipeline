"""Model builders for older Swedish lexicons."""

import logging

from sparv import Model, ModelOutput, modelbuilder
from sparv.util.lmflexicon import lmf_to_pickle

log = logging.getLogger(__name__)


@modelbuilder("Dalin morphology model", language=["swe"])
def build_dalin(out: ModelOutput = ModelOutput("hist/dalin.pickle")):
    """Download Dalin morphology XML and save as a pickle file."""
    # Download dalinm.xml
    xml_model = Model("hist/dalinm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()


@modelbuilder("Swedberg morphology model", language=["swe"])
def build_swedberg(out: ModelOutput = ModelOutput("hist/swedberg.pickle")):
    """Download Swedberg morphology XML and save as a pickle file."""
    # Download diapivot.xml
    xml_model = Model("hist/swedbergm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()
