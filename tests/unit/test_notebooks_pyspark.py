# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import papermill as pm
from tests.notebooks_common import OUTPUT_NOTEBOOK, KERNEL_NAME


@pytest.mark.notebooks
@pytest.mark.spark
def test_als_pyspark_runs(notebooks):
    notebook_path = notebooks["als_pyspark"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)


@pytest.mark.notebooks
@pytest.mark.spark
def test_data_split_runs(notebooks):
    notebook_path = notebooks["data_split"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)


@pytest.mark.notebooks
@pytest.mark.spark
def test_als_deep_dive_runs(notebooks):
    notebook_path = notebooks["als_deep_dive"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)


@pytest.mark.notebooks
@pytest.mark.spark
def test_evaluation_runs(notebooks):
    notebook_path = notebooks["evaluation"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)



@pytest.mark.notebooks
@pytest.mark.spark
def test_spark_hypertune(notebooks):
    notebook_path = notebooks["spark_hypertune"]
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(
            NUMBER_CORES="*",
            NUMBER_ITERATIONS=3,
            RANK=[5, 5],
            REG=[0.1, 0.01]
        )
    )

