# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pytest
import shutil

import pandas as pd
import tensorflow as tf

from reco_utils.common.tf_utils import (
    pandas_input_fn,
    build_optimizer,
    evaluation_log_hook,
    Logger,
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
from reco_utils.evaluation.python_evaluation import rmse

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
def test_pandas_input_fn(pd_df):
    df, _, _ = pd_df

    input_fn = pandas_input_fn(df)
    sample = input_fn()

    # check the input function returns all the columns
    assert len(df.columns) == len(sample)
    for k, v in sample.items():
        assert k in df.columns.values
        # check if a list feature column converted correctly
        if len(v.shape) == 2:
            assert v.shape[1] == len(df[k][0])

    input_fn_with_label = pandas_input_fn(df, y_col=DEFAULT_RATING_COL)
    X, y = input_fn_with_label()
    features = df.copy()
    features.pop(DEFAULT_RATING_COL)
    assert len(X) == len(features.columns)


@pytest.mark.gpu
def test_build_optimizer():
    adadelta = build_optimizer('Adadelta')
    assert isinstance(adadelta, tf.train.AdadeltaOptimizer)

    adagrad = build_optimizer('Adagrad')
    assert isinstance(adagrad, tf.train.AdagradOptimizer)

    adam = build_optimizer('Adam')
    assert isinstance(adam, tf.train.AdamOptimizer)

    ftrl = build_optimizer('Ftrl', **{'l1_regularization_strength': 0.001})
    assert isinstance(ftrl,  tf.train.FtrlOptimizer)

    momentum = build_optimizer('Momentum', **{'momentum': 0.5})
    assert isinstance(momentum, tf.train.MomentumOptimizer)

    rmsprop = build_optimizer('RMSProp')
    assert isinstance(rmsprop, tf.train.RMSPropOptimizer)

    sgd = build_optimizer('SGD')
    assert isinstance(sgd, tf.train.GradientDescentOptimizer)


@pytest.mark.gpu
def test_evaluation_log_hook(pd_df):
    data, users, items = pd_df

    # Run hook 10 times
    hook_frequency = 10
    train_steps = 101

    _, deep_columns = build_feature_columns(users, items, model_type='deep')

    model = build_model(
        'deep_'+MODEL_DIR, deep_columns=deep_columns, save_checkpoints_steps=train_steps//hook_frequency
    )

    class EvaluationLogger(Logger):
        def __init__(self):
            self.eval_log = {}

        def log(self, metric, value):
            if metric not in self.eval_log:
                self.eval_log[metric] = []
            self.eval_log[metric].append(value)

        def get_log(self):
            return self.eval_log

    evaluation_logger = EvaluationLogger()

    hooks = [
        evaluation_log_hook(
            model,
            logger=evaluation_logger,
            true_df=data,
            y_col=DEFAULT_RATING_COL,
            eval_df=data.drop(DEFAULT_RATING_COL, axis=1),
            every_n_iter=train_steps//hook_frequency,
            model_dir='deep_'+MODEL_DIR,
            eval_fns=[rmse],
        )
    ]
    model.train(
        input_fn=pandas_input_fn(df=data, y_col=DEFAULT_RATING_COL, batch_size=1, num_epochs=None, shuffle=True),
        hooks=hooks,
        steps=train_steps
    )
    shutil.rmtree('deep_' + MODEL_DIR, ignore_errors=True)

    # Check if hook logged the given metric
    assert rmse.__name__ in evaluation_logger.get_log()
    assert len(evaluation_logger.get_log()[rmse.__name__]) == hook_frequency
