# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
from urllib.request import urlretrieve
import logging

log = logging.getLogger(__name__)

from tqdm import tqdm


class TqdmUpTo(tqdm):
    """Wrapper class for the progress bar tqdm to get `update_to(n)` functionality"""

    def update_to(self, b=1, bsize=1, tsize=None):
        """A progress bar showing how much is left to finish the opperation
        
        Args:
            b (int): Number of blocks transferred so far.
            bsize (int): Size of each block (in tqdm units).
            tsize (int): Total size (in tqdm units). 
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)  # will also set self.n = b * bsize


def maybe_download(url, filename=None, work_directory=".", expected_bytes=None):
    """Download a file if it is not already downloaded.
    
    Args:
        filename (str): File name.
        work_directory (str): Working directory.
        url (str): URL of the file to download.
        expected_bytes (int): Expected file size in bytes.

    Returns:
        str: File path of the file downloaded.
    """
    if filename is None:
        filename = url.split("/")[-1]
    filepath = os.path.join(work_directory, filename)
    if not os.path.exists(filepath):
        with TqdmUpTo(unit="B", unit_scale=True) as t:
            filepath, _ = urlretrieve(url, filepath, reporthook=t.update_to)
    else:
        log.debug("File {} already downloaded".format(filepath))
    if expected_bytes is not None:
        statinfo = os.stat(filepath)
        if statinfo.st_size != expected_bytes:
            os.remove(filepath)
            raise IOError("Failed to verify {}".format(filepath))

    return filepath

