# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import pytest
from reco_utils.common.gpu_utils import get_number_gpus, clear_memory_all_gpus, get_cuda_version, get_cudnn_version


@pytest.mark.gpu
def test_get_number_gpus():
    assert get_number_gpus() >= 1


@pytest.mark.gpu
@pytest.mark.skip(reason="TODO: Implement this")
def test_clear_memory_all_gpus():
    pass


@pytest.mark.gpu
@pytest.mark.skipif(sys.platform == 'win32', reason="Not implemented on Windows")
def test_get_cuda_version():
    assert get_cuda_version() > "9.0.0"


@pytest.mark.gpu
def test_get_cudnn_version():
    assert get_cudnn_version() > "7.0.0"
