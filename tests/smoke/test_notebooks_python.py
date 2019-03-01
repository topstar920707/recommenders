# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import papermill as pm
from tests.notebooks_common import OUTPUT_NOTEBOOK, KERNEL_NAME


TOL = 0.05
ABS_TOL = 0.05


@pytest.mark.smoke
def test_sar_single_node_smoke(notebooks):
    notebook_path = notebooks["sar_single_node"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(TOP_K=10, MOVIELENS_DATA_SIZE="100k"),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    assert results["map"] == pytest.approx(0.105815262, rel=TOL, abs=ABS_TOL)
    assert results["ndcg"] == pytest.approx(0.373197255, rel=TOL, abs=ABS_TOL)
    assert results["precision"] == pytest.approx(0.326617179, rel=TOL, abs=ABS_TOL)
    assert results["recall"] == pytest.approx(0.175956743, rel=TOL, abs=ABS_TOL)


@pytest.mark.smoke
def test_baseline_deep_dive_smoke(notebooks):
    notebook_path = notebooks["baseline_deep_dive"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(TOP_K=10, MOVIELENS_DATA_SIZE="100k"),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    assert results["rmse"] == pytest.approx(1.054252, rel=TOL, abs=ABS_TOL)
    assert results["mae"] == pytest.approx(0.846033, rel=TOL, abs=ABS_TOL)
    assert results["rsquared"] == pytest.approx(0.136435, rel=TOL, abs=ABS_TOL)
    assert results["exp_var"] == pytest.approx(0.136446, rel=TOL, abs=ABS_TOL)
    assert results["map"] == pytest.approx(0.052850, rel=TOL, abs=ABS_TOL)
    assert results["ndcg"] == pytest.approx(0.248061, rel=TOL, abs=ABS_TOL)
    assert results["precision"] == pytest.approx(0.223754, rel=TOL, abs=ABS_TOL)
    assert results["recall"] == pytest.approx(0.108826, rel=TOL, abs=ABS_TOL)


@pytest.mark.smoke
def test_surprise_svd_smoke(notebooks):
    notebook_path = notebooks["surprise_svd_deep_dive"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(MOVIELENS_DATA_SIZE="100k"),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    assert results["rmse"] == pytest.approx(0.96, rel=TOL, abs=ABS_TOL)
    assert results["mae"] == pytest.approx(0.75, rel=TOL, abs=ABS_TOL)
    assert results["rsquared"] == pytest.approx(0.29, rel=TOL, abs=ABS_TOL)
    assert results["exp_var"] == pytest.approx(0.29, rel=TOL, abs=ABS_TOL)
    assert results["map"] == pytest.approx(0.013, rel=TOL, abs=ABS_TOL)
    assert results["ndcg"] == pytest.approx(0.1, rel=TOL, abs=ABS_TOL)
    assert results["precision"] == pytest.approx(0.095, rel=TOL, abs=ABS_TOL)
    assert results["recall"] == pytest.approx(0.032, rel=TOL, abs=ABS_TOL)


def test_vw_deep_dive_smoke(notebooks):
    notebook_path = notebooks["vowpal_wabbit_deep_dive"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(MOVIELENS_DATA_SIZE="100k"),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    assert results["rmse"] == pytest.approx(0.99575, rel=TOL, abs=ABS_TOL)
    assert results["mae"] == pytest.approx(0.72024, rel=TOL, abs=ABS_TOL)
    assert results["rsquared"] == pytest.approx(0.22961, rel=TOL, abs=ABS_TOL)
    assert results["exp_var"] == pytest.approx(0.22967, rel=TOL, abs=ABS_TOL)
    assert results["map"] == pytest.approx(0.25684, rel=TOL, abs=ABS_TOL)
    assert results["ndcg"] == pytest.approx(0.65339, rel=TOL, abs=ABS_TOL)
    assert results["precision"] == pytest.approx(0.514738, rel=TOL, abs=ABS_TOL)
    assert results["recall"] == pytest.approx(0.25684, rel=TOL, abs=ABS_TOL)
