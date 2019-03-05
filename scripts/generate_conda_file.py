#!/usr/bin/python

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# This script creates yaml files to build conda environments
# For generating a conda file for running only python code:
# $ python generate_conda_file.py
# For generating a conda file for running python gpu:
# $ python generate_conda_file.py --gpu
# For generating a conda file for running pyspark:
# $ python generate_conda_file.py --pyspark
# For generating a conda file for running python gpu and pyspark:
# $ python generate_conda_file.py --gpu --pyspark
# For generating a conda file for running python gpu and pyspark with a particular version:
# $ python generate_conda_file.py --gpu --pyspark-version 2.4.0

import argparse
import textwrap


HELP_MSG = """
To create the conda environment:
$ conda env create -f {conda_env}.yaml

To update the conda environment:
$ conda env update -f {conda_env}.yaml

To register the conda environment in Jupyter:
$ conda activate {conda_env}
$ python -m ipykernel install --user --name {conda_env} --display-name "Python ({conda_env})"
"""

CHANNELS = [ "defaults", "conda-forge", "pytorch", "fastai"]

CONDA_BASE = {
    "mock": "mock==2.0.0",
    "dask": "dask>=0.17.1",
    "fastparquet": "fastparquet>=0.1.6",
    "gitpython": "gitpython>=2.1.8",
    "ipykernel": "ipykernel>=4.6.1",
    "jupyter": "jupyter>=1.0.0",
    "matplotlib": "matplotlib>=2.2.2",
    "numpy": "numpy>=1.13.3",
    "pandas": "pandas>=0.23.4",
    "pymongo": "pymongo>=3.6.1",
    "python": "python==3.6.8",
    "pytest": "pytest>=3.6.4",
    "pytorch": "pytorch-cpu>=1.0.0",
    "seaborn": "seaborn>=0.8.1",
    "scikit-learn": "scikit-learn==0.19.1",
    "scipy": "scipy>=1.0.0",
    "scikit-surprise": "scikit-surprise>=1.0.6",
    "tensorflow": "tensorflow==1.12.0",
}

CONDA_PYSPARK = {"pyarrow": "pyarrow>=0.8.0", "pyspark": "pyspark==2.3.1"}

CONDA_GPU = {"numba": "numba>=0.38.1", "pytorch": "pytorch>=1.0.0", "tensorflow": "tensorflow-gpu==1.12.0"}

PIP_BASE = {
    "azureml-sdk[notebooks,contrib]": "azureml-sdk[notebooks,contrib]==1.0.10",
    "azure-storage": "azure-storage>=0.36.0",
    "black": "black>=18.6b4",
    "dataclasses": "dataclasses>=0.6",
    "hyperopt": "hyperopt==0.1.1",
    "idna": "idna==2.7",
    "memory-profiler": "memory-profiler>=0.54.0",
    "nvidia-ml-py3": "nvidia-ml-py3>=7.352.0",
    "papermill": "papermill>=0.15.0",
    "pydocumentdb": "pydocumentdb>=2.3.3",
    "fastai": "fastai==1.0.46",
}

PIP_PYSPARK = {}
PIP_GPU = {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """
        This script generates a conda file for different environments.
        Plain python is the default, but flags can be used to support PySpark and GPU functionality"""
        ),
        epilog=HELP_MSG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", help="specify name of conda environment")
    parser.add_argument(
        "--gpu", action="store_true", help="include packages for GPU support"
    )
    parser.add_argument(
        "--pyspark", action="store_true", help="include packages for PySpark support"
    )
    parser.add_argument(
        "--pyspark-version", help="provide specific version of PySpark to use"
    )
    args = parser.parse_args()

    # check pyspark version
    if args.pyspark_version is not None:
        args.pyspark = True
        pyspark_version_info = args.pyspark_version.split(".")
        if len(pyspark_version_info) != 3 or any(
            [not x.isdigit() for x in pyspark_version_info]
        ):
            raise TypeError(
                "PySpark version input must be valid numeric format (e.g. --pyspark-version=2.3.1)"
            )
    else:
        args.pyspark_version = "2.3.1"

    # set name for environment and output yaml file
    conda_env = "reco_base"
    if args.gpu and args.pyspark:
        conda_env = "reco_full"
    elif args.gpu:
        conda_env = "reco_gpu"
    elif args.pyspark:
        conda_env = "reco_pyspark"

    # overwrite environment name with user input
    if args.name is not None:
        conda_env = args.name

    # update conda and pip packages based on flags provided
    conda_packages = CONDA_BASE
    pip_packages = PIP_BASE
    if args.pyspark:
        conda_packages.update(CONDA_PYSPARK)
        conda_packages["pyspark"] = "pyspark=={}".format(args.pyspark_version)
        pip_packages.update(PIP_PYSPARK)
    if args.gpu:
        conda_packages.update(CONDA_GPU)
        pip_packages.update(PIP_GPU)

    # write out yaml file
    conda_file = "{}.yaml".format(conda_env)
    with open(conda_file, "w") as f:
        for line in HELP_MSG.format(conda_env=conda_env).split("\n"):
            f.write("# {}\n".format(line))
        f.write("name: {}\n".format(conda_env))
        f.write("channels:\n")
        for channel in CHANNELS:
            f.write("- {}\n".format(channel))
        f.write("dependencies:\n")
        for conda_package in conda_packages.values():
            f.write("- {}\n".format(conda_package))
        f.write("- pip:\n")
        for pip_package in pip_packages.values():
            f.write("  - {}\n".format(pip_package))

    print("Generated conda file: {}".format(conda_file))
    print(HELP_MSG.format(conda_env=conda_env))
