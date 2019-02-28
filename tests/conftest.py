# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# NOTE: This file is used by pytest to inject fixtures automatically. As it is explained in the documentation
# https://docs.pytest.org/en/latest/fixture.html:
# "If during implementing your tests you realize that you want to use a fixture function from multiple test files
# you can move it to a conftest.py file. You don’t need to import the fixture you want to use in a test, it
# automatically gets discovered by pytest."

import calendar
import datetime
import os
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split
from tests.notebooks_common import path_notebooks

try:
    from pyspark.sql import SparkSession
except ImportError:
    pass  # so the environment without spark doesn't break


@pytest.fixture(scope="session")
def spark(app_name="Sample", url="local[*]", memory="1G"):
    """Start Spark if not started
    Args:
        app_name (str): sets name of the application
        url (str): url for spark master
        memory (str): size of memory for spark driver
    Other Spark settings which you might find useful:
        .config("spark.executor.cores", "4")
        .config("spark.executor.memory", "2g")
        .config("spark.memory.fraction", "0.9")
        .config("spark.memory.stageFraction", "0.3")
        .config("spark.executor.instances", 1)
        .config("spark.executor.heartbeatInterval", "36000s")
        .config("spark.network.timeout", "10000000s")
        .config("spark.driver.maxResultSize", memory)
    """
    SUBMIT_ARGS = "--packages eisber:sarplus:0.2.3 pyspark-shell"
    os.environ["PYSPARK_SUBMIT_ARGS"] = SUBMIT_ARGS

    return (
        SparkSession.builder.appName(app_name)
        .master(url)
        .config("spark.driver.memory", memory)
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.local.dir", "/mnt")
        .config("spark.worker.cleanup.enabled", "true")
        .config("spark.worker.cleanup.appDataTtl", "3600")
        .config("spark.worker.cleanup.interval", "300")
        .config("spark.storage.cleanupFilesAfterExecutorExit", "true")
        .getOrCreate()
    )


@pytest.fixture(scope="module")
def sar_settings():
    return {
        # absolute tolerance parameter for matrix equivalence in SAR tests
        "ATOL": 1e-8,
        # directory of the current file - used to link unit test data
        "FILE_DIR": "http://recodatasets.blob.core.windows.net/sarunittest/",
        # user ID used in the test files (they are designed for this user ID, this is part of the test)
        "TEST_USER_ID": "0003000098E85347",
    }


@pytest.fixture(scope="module")
def header():
    header = {
        "col_user": "UserId",
        "col_item": "MovieId",
        "col_rating": "Rating",
        "col_timestamp": "Timestamp",
    }
    return header


@pytest.fixture(scope="module")
def pandas_dummy(header):
    ratings_dict = {
        header["col_user"]: [1, 1, 1, 1, 2, 2, 2, 2, 2, 2],
        header["col_item"]: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        header["col_rating"]: [1.0, 2.0, 3.0, 4.0, 5.0, 1.0, 2.0, 3.0, 4.0, 5.0],
    }
    df = pd.DataFrame(ratings_dict)
    return df


@pytest.fixture(scope="module")
def pandas_dummy_timestamp(pandas_dummy, header):
    time = 1535133442
    time_series = [time + 20 * i for i in range(10)]
    df = pandas_dummy
    df[header["col_timestamp"]] = time_series
    return df


@pytest.fixture(scope="module")
def train_test_dummy_timestamp(pandas_dummy_timestamp):
    return train_test_split(pandas_dummy_timestamp, test_size=0.2, random_state=0)


@pytest.fixture(scope="module")
def demo_usage_data(header, sar_settings):
    # load the data
    data = pd.read_csv(sar_settings["FILE_DIR"] + "demoUsage.csv")
    data["rating"] = pd.Series([1.0] * data.shape[0])
    data = data.rename(
        columns={
            "userId": header["col_user"],
            "productId": header["col_item"],
            "rating": header["col_rating"],
            "timestamp": header["col_timestamp"],
        }
    )

    # convert timestamp
    data[header["col_timestamp"]] = data[header["col_timestamp"]].apply(
        lambda s: float(
            calendar.timegm(
                datetime.datetime.strptime(s, "%Y/%m/%dT%H:%M:%S").timetuple()
            )
        )
    )

    return data


@pytest.fixture(scope="module")
def demo_usage_data_spark(spark, demo_usage_data, header):
    data_local = demo_usage_data[[x[1] for x in header.items()]]
    return spark.createDataFrame(data_local)


@pytest.fixture(scope="module")
def notebooks():
    folder_notebooks = path_notebooks()

    # Path for the notebooks
    paths = {
        "template": os.path.join(folder_notebooks, "template.ipynb"),
        "sar_single_node": os.path.join(
            folder_notebooks, "00_quick_start", "sar_movielens.ipynb"
        ),
        "ncf": os.path.join(folder_notebooks, "00_quick_start", "ncf_movielens.ipynb"),
        "als_pyspark": os.path.join(
            folder_notebooks, "00_quick_start", "als_movielens.ipynb"
        ),
        "fastai": os.path.join(
            folder_notebooks, "00_quick_start", "fastai_movielens.ipynb"
        ),
        "xdeepfm_quickstart": os.path.join(
            folder_notebooks, "00_quick_start", "xdeepfm_synthetic.ipynb"
        ),
        "dkn_quickstart": os.path.join(
            folder_notebooks, "00_quick_start", "dkn_synthetic.ipynb"
        ),
        "wide_deep": os.path.join(
            folder_notebooks, "00_quick_start", "wide_deep_movielens.ipynb"
        ),
        "data_split": os.path.join(
            folder_notebooks, "01_prepare_data", "data_split.ipynb"
        ),
        "als_deep_dive": os.path.join(
            folder_notebooks, "02_model", "als_deep_dive.ipynb"
        ),
        "surprise_svd_deep_dive": os.path.join(
            folder_notebooks, "02_model", "surprise_svd_deep_dive.ipynb"
        ),
        "baseline_deep_dive": os.path.join(
            folder_notebooks, "02_model", "baseline_deep_dive.ipynb"
        ),
        "ncf_deep_dive": os.path.join(
            folder_notebooks, "02_model", "ncf_deep_dive.ipynb"
        ),
        "sar_deep_dive": os.path.join(
            folder_notebooks, "02_model", "sar_deep_dive.ipynb"
        ),
        "vowpal_wabbit_deep_dive": os.path.join(
            folder_notebooks, "02_model", "vowpal_wabbit_deep_dive.ipynb"
        ),
        "evaluation": os.path.join(folder_notebooks, "03_evaluate", "evaluation.ipynb")
    }
    return paths

