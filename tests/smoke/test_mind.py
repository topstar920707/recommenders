# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import os
from reco_utils.dataset.mind import download_mind


@pytest.mark.smoke
def test_download_mind(tmp_path):
    train_path, valid_path = download_mind(size="small", dest_path=tmp_path)
    statinfo = os.stat(train_path)
    assert statinfo.st_size == 54772957
    statinfo = os.stat(valid_path)
    assert statinfo.st_size == 32470157

