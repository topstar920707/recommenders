# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import papermill as pm
from tests.notebooks_common import OUTPUT_NOTEBOOK, KERNEL_NAME
from reco_utils.common.spark_utils import start_or_get_spark


TOL = 0.05
ABS_TOL = 0.05


@pytest.mark.spark
@pytest.mark.integration
def test_als_pyspark_integration(notebooks):
    notebook_path = notebooks["als_pyspark"]
    pm.execute_notebook(
        notebook_path,
        OUTPUT_NOTEBOOK,
        kernel_name=KERNEL_NAME,
        parameters=dict(TOP_K=10, MOVIELENS_DATA_SIZE="1m"),
    )
    nb = pm.read_notebook(OUTPUT_NOTEBOOK)
    results = nb.dataframe.set_index("name")["value"]
    start_or_get_spark("ALS PySpark").stop()

    assert results["map"] == pytest.approx(0.00201, rel=TOL, abs=ABS_TOL)
    assert results["ndcg"] == pytest.approx(0.02516, rel=TOL, abs=ABS_TOL)
    assert results["precision"] == pytest.approx(0.03172, rel=TOL, abs=ABS_TOL)
    assert results["recall"] == pytest.approx(0.009302, rel=TOL, abs=ABS_TOL)
    assert results["rmse"] == pytest.approx(0.8621, rel=TOL, abs=ABS_TOL)
    assert results["mae"] == pytest.approx(0.68023, rel=TOL, abs=ABS_TOL)
    assert results["exp_var"] == pytest.approx(0.4094, rel=TOL, abs=ABS_TOL)
    assert results["rsquared"] == pytest.approx(0.4038, rel=TOL, abs=ABS_TOL)
