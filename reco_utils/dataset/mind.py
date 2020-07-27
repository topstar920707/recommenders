# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


from reco_utils.dataset.download_utils import maybe_download, download_path, unzip_file


URL_MIND_LARGE_TRAIN = (
    "https://mind201910small.blob.core.windows.net/release/MINDlarge_train.zip"
)
URL_MIND_LARGE_VALID = (
    "https://mind201910small.blob.core.windows.net/release/MINDlarge_dev.zip"
)
URL_MIND_SMALL_TRAIN = (
    "https://mind201910small.blob.core.windows.net/release/MINDsmall_train.zip"
)
URL_MIND_SMALL_VALID = (
    "https://mind201910small.blob.core.windows.net/release/MINDsmall_dev.zip"
)
URL_MIND = {
    "large": (URL_MIND_LARGE_TRAIN, URL_MIND_LARGE_VALID),
    "small": (URL_MIND_SMALL_TRAIN, URL_MIND_SMALL_VALID),
}


def _maybe_download_mind(size, dest_path):
    url_train, url_valid = URL_MIND[size]
    with download_path(dest_path) as path:
        train_path = maybe_download(url=url_train, work_directory=path)
        valid_path = maybe_download(url=url_valid, work_directory=path)
    return train_path, valid_path


def download_mind(
    size="small", dest_path=None, train_folder="train", valid_folder="valid"
):
    """Download MIND dataset

    Args:
        size (str): Dataset size. One of ["small", "large"]
        dest_path (str): Download path. If path is None, it will download the dataset on a temporal path
    Returns:
        str, str: Path to train and validation sets.
    """
    train_zip, valid_zip = _maybe_download_mind(size, dest_path)
    train_path = os.path.join(dest_path, train_folder)
    valid_path = os.path.join(dest_path, valid_folder)
    unzip_file(train_zip, train_path)
    unzip_file(valid_zip, valid_path)
    return train_path, valid_path

