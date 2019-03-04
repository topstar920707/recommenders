# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import os
import glob
from numba import cuda
from numba.cuda.cudadrv.error import CudaSupportError


def get_number_gpus():
    """Get the number of GPUs in the system.
    
    Returns:
        int: Number of GPUs.
    """
    try:
        return len(cuda.gpus)
    except CudaSupportError:
        return 0


def clear_memory_all_gpus():
    """Clear memory of all GPUs."""
    try:
        for gpu in cuda.gpus:
            with gpu:
                cuda.current_context().deallocations.clear()
    except CudaSupportError:
        print("No CUDA available")


def get_cuda_version():
    """Get CUDA version
    
    Returns:
        str: Version of the library.
    """
    if sys.platform == "win32":
        raise NotImplementedError("Implement this!")
    elif sys.platform == "linux" or sys.platform == "darwin":
        path = "/usr/local/cuda/version.txt"
        if os.path.isfile(path):
            with open(path, "r") as f:
                data = f.read().replace("\n", "")
            return data
        else:
            return "No CUDA in this machine"
    else:
        raise ValueError("Not in Windows, Linux or Mac")


def get_cudnn_version():
    """Get the CuDNN version
    
    Returns:
        str: Version of the library.
    """

    def find_cudnn_in_headers(candiates):
        for c in candidates:
            file = glob.glob(c)
            if file:
                break
        if file:
            with open(file[0], "r") as f:
                version = ""
                for line in f:
                    if "#define CUDNN_MAJOR" in line:
                        version = line.split()[-1]
                    if "#define CUDNN_MINOR" in line:
                        version += "." + line.split()[-1]
                    if "#define CUDNN_PATCHLEVEL" in line:
                        version += "." + line.split()[-1]
            if version:
                return version
            else:
                return "Cannot find CUDNN version"
        else:
            return "No CUDNN in this machine"

    if sys.platform == "win32":
        candidates = [r"C:\NVIDIA\cuda\include\cudnn.h"]
    elif sys.platform == "linux":
        candidates = [
            "/usr/include/x86_64-linux-gnu/cudnn_v[0-99].h",
            "/usr/local/cuda/include/cudnn.h",
            "/usr/include/cudnn.h",
        ]
    elif sys.platform == "darwin":
        candidates = ["/usr/local/cuda/include/cudnn.h", "/usr/include/cudnn.h"]
    else:
        raise ValueError("Not in Windows, Linux or Mac")
    return find_cudnn_in_headers(candidates)
