# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import papermill as pm
import pytest
from reco_utils.common.gpu_utils import get_number_gpus
from tests.notebooks_common import OUTPUT_NOTEBOOK, KERNEL_NAME

TOL = 0.5
ABS_TOL = 0.05


@pytest.mark.integration
@pytest.mark.gpu
def test_gpu_vm():
    assert get_number_gpus() >= 1


@pytest.mark.integration
@pytest.mark.gpu
@pytest.mark.parametrize(
    "size, epochs, expected_values, seed",
    [
        (
            "1m",
            10,
            {
                "map": 0.0255283,
                "ndcg": 0.15656,
                "precision": 0.145646,
                "recall": 0.0557367,
            },
            42,
        ),
        # ("10m", 5, {"map": 0.024821, "ndcg": 0.153396, "precision": 0.143046, "recall": 0.056590})# takes too long
    ],
)
def test_ncf_integration(notebooks, size, epochs, expected_values, seed):
    notebook_path = notebooks["ncf"]
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(
            TOP_K=10, MOVIELENS_DATA_SIZE=size, EPOCHS=epochs, BATCH_SIZE=512, SEED=seed,
        ),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    for key, value in expected_values.items():
        assert results[key] == pytest.approx(value, rel=TOL, abs=ABS_TOL)


@pytest.mark.integration
@pytest.mark.gpu
@pytest.mark.parametrize(
    "size, epochs, batch_size, expected_values, seed",
    [
        (
            "100k",
            10,
            512,
            {
                "map": 0.0435856,
                "ndcg": 0.37586,
                "precision": 0.169353,
                "recall": 0.0923963,
                "map2": 0.0510391,
                "ndcg2": 0.202186,
                "precision2": 0.179533,
                "recall2": 0.106434,
            },
            42,
        )
    ],
)
def test_ncf_deep_dive_integration(
    notebooks, size, epochs, batch_size, expected_values, seed
):
    notebook_path = notebooks["ncf_deep_dive"]
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(
            TOP_K=10, MOVIELENS_DATA_SIZE=size, EPOCHS=epochs, BATCH_SIZE=batch_size, SEED=seed,
        ),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    for key, value in expected_values.items():
        assert results[key] == pytest.approx(value, rel=TOL, abs=ABS_TOL)


@pytest.mark.integration
@pytest.mark.gpu
@pytest.mark.parametrize(
    "size, epochs, expected_values",
    [
        (
            "1m",
            10,
            {
                "map": 0.025739,
                "ndcg": 0.183417,
                "precision": 0.167246,
                "recall": 0.054307,
                "rmse": 0.881267,
                "mae": 0.700747,
                "rsquared": 0.379963,
                "exp_var": 0.382842,
            },
        ),
        # ("10m", 5, ), # it gets an OOM on pred = learner.model.forward(u, m)
    ],
)
def test_fastai_integration(notebooks, size, epochs, expected_values):
    notebook_path = notebooks["fastai"]
    pm.execute_notebook(notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME)
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(TOP_K=10, MOVIELENS_DATA_SIZE=size, EPOCHS=epochs),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    for key, value in expected_values.items():
        assert results[key] == pytest.approx(value, rel=TOL, abs=ABS_TOL)


@pytest.mark.integration
@pytest.mark.gpu
@pytest.mark.parametrize(
    "syn_epochs, criteo_epochs, expected_values, seed",
    [
        (
            15,
            10,
            {
                "res_syn": {
                    "auc": 0.9716,
                    "logloss": 0.699,
                },
                "res_real": {
                    "auc": 0.749,
                    "logloss": 0.4926,
                },
            },
            42,
        )
    ],
)
def test_xdeepfm_integration(notebooks, syn_epochs, criteo_epochs, expected_values, seed):
    notebook_path = notebooks["xdeepfm_quickstart"]
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(
            EPOCHS_FOR_SYNTHETIC_RUN=syn_epochs,
            EPOCHS_FOR_CRITEO_RUN=criteo_epochs,
            BATCH_SIZE_SYNTHETIC=1024,
            BATCH_SIZE_CRITEO=1024,
            RANDOM_SEED=seed,
        ),
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]

    for key, value in expected_values.items():
        assert results[key]["auc"] == pytest.approx(value["auc"], rel=TOL, abs=ABS_TOL)
        assert results[key]["logloss"] == pytest.approx(value["logloss"], rel=TOL, abs=ABS_TOL)


@pytest.mark.integration
@pytest.mark.gpu
@pytest.mark.parametrize(
    "size, steps, expected_values, seed",
    [
        (
            "1m",
            50000,
            {
                "rmse": 0.924958,
                "mae": 0.741425,
                "rsquared": 0.316534,
                "exp_var": 0.322202,
                "ndcg_at_k": 0.118114,
                "map_at_k": 0.0139213,
                "precision_at_k": 0.107087,
                "recall_at_k": 0.0328638,
            },
            42,
        )
    ],
)
def test_wide_deep_integration(notebooks, size, steps, expected_values, seed, tmp):
    notebook_path = notebooks["wide_deep"]

    params = {
        "MOVIELENS_DATA_SIZE": size,
        "STEPS": steps,
        "EVALUATE_WHILE_TRAINING": False,
        "MODEL_DIR": tmp,
        "EXPORT_DIR_BASE": tmp,
        "RATING_METRICS": ["rmse", "mae", "rsquared", "exp_var"],
        "RANKING_METRICS": ["ndcg_at_k", "map_at_k", "precision_at_k", "recall_at_k"],
        "RANDOM_SEED": seed,
    }
    pm.execute_notebook(
        notebook_path, OUTPUT_NOTEBOOK, kernel_name=KERNEL_NAME, parameters=params
    )
    results = pm.read_notebook(OUTPUT_NOTEBOOK).dataframe.set_index("name")["value"]
    for key, value in expected_values.items():
        assert results[key] == pytest.approx(value, rel=TOL, abs=ABS_TOL)
