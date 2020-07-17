"""Model-related util functions like reading and writing data."""

import gzip
import logging
import os
import pathlib
import pickle
import urllib.request
import zipfile

from typing import Union

from sparv.core.paths import models_dir
from sparv.util.classes import Model, ModelOutput

log = logging.getLogger(__name__)


def get_model_path(name: Union[str, pathlib.Path, Model, ModelOutput]) -> pathlib.Path:
    """Get full path to model file."""
    if isinstance(name, str):
        name = pathlib.Path(name)
    elif isinstance(name, (Model, ModelOutput)):
        name = pathlib.Path(name.name)
    # Check if name already includes full path to models dir
    if models_dir in name.parents:
        return name
    else:
        return models_dir / name


def write_model_data(name: Union[ModelOutput, str, pathlib.Path], data):
    """Write arbitrary string data to models directory."""
    file_path = get_model_path(name)
    os.makedirs(file_path.parent, exist_ok=True)

    with open(file_path, "w") as f:
        f.write(data)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    log.info("Wrote %d bytes: %s", len(data), file_path)


def read_model_data(name: Union[Model, str, pathlib.Path]):
    """Read arbitrary string data from file in models directory."""
    file_path = get_model_path(name)

    with open(file_path) as f:
        data = f.read()
    log.info("Read %d bytes: %s", len(data), name)
    return data


def write_model_pickle(name: Union[ModelOutput, str, pathlib.Path], data, protocol=-1):
    """Dump data to pickle file in models directory."""
    file_path = get_model_path(name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        pickle.dump(data, f, protocol=protocol)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    log.info("Wrote %d bytes: %s", len(data), file_path)


def read_model_pickle(name: Union[Model, str, pathlib.Path]):
    """Read pickled data from file in models directory."""
    file_path = get_model_path(name)

    with open(file_path, "rb") as f:
        data = pickle.load(f)
    log.info("Read %d bytes: %s", len(data), name)
    return data


def download_model(url: str, name: Union[ModelOutput, str, pathlib.Path]):
    """Download file from url and save to modeldir/filename."""
    name = get_model_path(name)
    os.makedirs(name.parent, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, name)
        log.info("Successfully downloaded %s", name)
    except Exception as e:
        log.error("Download from %s failed", url)
        raise e


def unzip_model(zip_file: Union[ModelOutput, str, pathlib.Path]):
    """Unzip zip_file inside modeldir."""
    zip_file = get_model_path(zip_file)
    out_dir = zip_file.parent
    with zipfile.ZipFile(zip_file) as z:
        z.extractall(out_dir)
    log.info("Successfully unzipped %s", zip_file)


def ungzip_model(gzip_file: Union[ModelOutput, str, pathlib.Path], out: str):
    """Unzip gzip_file inside modeldir."""
    gzip_file = get_model_path(gzip_file)
    with gzip.open(gzip_file) as z:
        data = z.read()
        with open(out, "wb") as f:
            f.write(data)
    log.info("Successfully unzipped %s", out)


def remove_model_files(files: list, raise_errors: bool = False):
    """Remove files from disk."""
    for f in files:
        file_path = get_model_path(f)
        try:
            os.remove(file_path)
        except FileNotFoundError as e:
            if raise_errors:
                raise e
