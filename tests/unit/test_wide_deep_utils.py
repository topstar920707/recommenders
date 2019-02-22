# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import shutil

import pandas as pd
import tensorflow as tf

from reco_utils.common.tf_utils import (
    pandas_input_fn,
    MODEL_DIR
)
from reco_utils.recommender.wide_deep.wide_deep_utils import (
    build_model,
    build_feature_columns,
)
from reco_utils.common.constants import (
    DEFAULT_USER_COL,
    DEFAULT_ITEM_COL,
    DEFAULT_RATING_COL
)

ITEM_FEAT_COL = 'itemFeat'


@pytest.fixture(scope='module')
def pd_df():
    df = pd.DataFrame(
        {
            DEFAULT_USER_COL: [1, 1, 1, 2, 2, 2],
            DEFAULT_ITEM_COL: [1, 2, 3, 1, 4, 5],
            ITEM_FEAT_COL: [[1, 1, 1], [2, 2, 2], [3, 3, 3], [1, 1, 1], [4, 4, 4], [5, 5, 5]],
            DEFAULT_RATING_COL: [5, 4, 3, 5, 5, 3],
        }
    )
    users = df.drop_duplicates(DEFAULT_USER_COL)[DEFAULT_USER_COL].values
    items = df.drop_duplicates(DEFAULT_ITEM_COL)[DEFAULT_ITEM_COL].values
    return df, users, items


@pytest.mark.gpu
def test_build_feature_columns(pd_df):
    data, users, items = pd_df

    # Test if wide column has one crossed column
    wide_columns, _ = build_feature_columns(users, items, model_type='wide')
    assert len(wide_columns) == 1

    # Test if deep columns have user and item columns
    _, deep_columns = build_feature_columns(users, items, model_type='deep')
    assert len(deep_columns) == 2

    # Test if wide and deep columns have correct columns
    wide_columns, deep_columns = build_feature_columns(users, items, model_type='wide_deep')
    assert len(wide_columns) == 1
    assert len(deep_columns) == 2


@pytest.mark.gpu
def test_build_model(pd_df):
    data, users, items = pd_df

    # Test wide model
    wide_columns, deep_columns = build_feature_columns(users, items, model_type='wide')
    model = build_model('wide_'+MODEL_DIR, wide_columns=wide_columns)
    assert isinstance(model, tf.estimator.LinearRegressor)
    model = build_model('wide_'+MODEL_DIR, wide_columns=wide_columns, deep_columns=deep_columns)
    assert isinstance(model, tf.estimator.LinearRegressor)

    # Test if model train works
    model.train(
        input_fn=pandas_input_fn(df=data, y_col=DEFAULT_RATING_COL, batch_size=1, num_epochs=10, shuffle=True)
    )
    shutil.rmtree('wide_' + MODEL_DIR, ignore_errors=True)

    # Test deep model
    wide_columns, deep_columns = build_feature_columns(users, items, model_type='deep')
    model = build_model('deep_'+MODEL_DIR, deep_columns=deep_columns)
    assert isinstance(model, tf.estimator.DNNRegressor)
    model = build_model('deep_'+MODEL_DIR, wide_columns=wide_columns, deep_columns=deep_columns)
    assert isinstance(model, tf.estimator.DNNRegressor)

    # Test if model train works
    model.train(
        input_fn=pandas_input_fn(df=data, y_col=DEFAULT_RATING_COL, batch_size=1, num_epochs=10, shuffle=True)
    )
    shutil.rmtree('deep_' + MODEL_DIR, ignore_errors=True)

    # Test wide_deep model
    wide_columns, deep_columns = build_feature_columns(users, items, model_type='wide_deep')
    model = build_model('wide_deep_'+MODEL_DIR, wide_columns=wide_columns, deep_columns=deep_columns)
    assert isinstance(model, tf.estimator.DNNLinearCombinedRegressor)

    # Test if model train works
    model.train(
        input_fn=pandas_input_fn(df=data, y_col=DEFAULT_RATING_COL, batch_size=1, num_epochs=10, shuffle=True)
    )
    shutil.rmtree('wide_deep_'+MODEL_DIR, ignore_errors=True)
