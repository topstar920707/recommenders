# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import itertools

import pytest
import numpy as np
import pandas as pd
from pandas.util.testing import assert_frame_equal

from reco_utils.common.constants import DEFAULT_PREDICTION_COL
from reco_utils.recommender.sar.sar_singlenode import SARSingleNode
from reco_utils.recommender.sar import TIME_NOW
from tests.sar_common import read_matrix, load_userpred, load_affinity


def _rearrange_to_test(array, row_ids, col_ids, row_map, col_map):
    """Rearranges SAR array into test array order"""
    if row_ids is not None:
        row_index = [row_map[x] for x in row_ids]
        array = array[row_index, :]
    if col_ids is not None:
        col_index = [col_map[x] for x in col_ids]
        array = array[:, col_index]
    return array


def test_init(header):
    model = SARSingleNode(similarity_type="jaccard", **header)

    assert model.col_user == "UserId"
    assert model.col_item == "MovieId"
    assert model.col_rating == "Rating"
    assert model.col_timestamp == "Timestamp"
    assert model.col_prediction == "prediction"
    assert model.similarity_type == "jaccard"
    assert model.time_decay_half_life == 2592000
    assert model.time_decay_flag == False
    assert model.time_now == None
    assert model.threshold == 1


@pytest.mark.parametrize(
    "similarity_type, timedecay_formula", [("jaccard", False), ("lift", True)]
)
def test_fit(similarity_type, timedecay_formula, train_test_dummy_timestamp, header):
    model = SARSingleNode(
        similarity_type=similarity_type, timedecay_formula=timedecay_formula, **header
    )
    trainset, testset = train_test_dummy_timestamp
    model.fit(trainset)


@pytest.mark.parametrize(
    "similarity_type, timedecay_formula", [("jaccard", False), ("lift", True)]
)
def test_predict(
    similarity_type, timedecay_formula, train_test_dummy_timestamp, header
):
    model = SARSingleNode(
        similarity_type=similarity_type, timedecay_formula=timedecay_formula, **header
    )
    trainset, testset = train_test_dummy_timestamp
    model.fit(trainset)
    preds = model.predict(testset)

    assert len(preds) == 2
    assert isinstance(preds, pd.DataFrame)
    assert preds[header["col_user"]].dtype == trainset[header["col_user"]].dtype
    assert preds[header["col_item"]].dtype == trainset[header["col_item"]].dtype
    assert preds[DEFAULT_PREDICTION_COL].dtype == trainset[header["col_rating"]].dtype


def test_predict_all_items(train_test_dummy_timestamp, header):
    model = SARSingleNode(**header)
    trainset, _ = train_test_dummy_timestamp
    model.fit(trainset)

    user_items = itertools.product(
        trainset[header["col_user"]].unique(), trainset[header["col_item"]].unique()
    )
    testset = pd.DataFrame(user_items, columns=[header["col_user"], header["col_item"]])
    preds = model.predict(testset)

    assert len(preds) == len(testset)
    assert isinstance(preds, pd.DataFrame)
    assert preds[header["col_user"]].dtype == trainset[header["col_user"]].dtype
    assert preds[header["col_item"]].dtype == trainset[header["col_item"]].dtype
    assert preds[DEFAULT_PREDICTION_COL].dtype == trainset[header["col_rating"]].dtype


@pytest.mark.parametrize(
    "threshold,similarity_type,file",
    [
        (1, "cooccurrence", "count"),
        (1, "jaccard", "jac"),
        (1, "lift", "lift"),
        (3, "cooccurrence", "count"),
        (3, "jaccard", "jac"),
        (3, "lift", "lift"),
    ],
)
def test_sar_item_similarity(
    threshold, similarity_type, file, demo_usage_data, sar_settings, header
):

    model = SARSingleNode(
        similarity_type=similarity_type,
        timedecay_formula=False,
        time_decay_coefficient=30,
        time_now=TIME_NOW,
        threshold=threshold,
        **header
    )

    model.fit(demo_usage_data)

    true_item_similarity, row_ids, col_ids = read_matrix(
        sar_settings["FILE_DIR"] + "sim_" + file + str(threshold) + ".csv"
    )

    if similarity_type is "cooccurrence":
        test_item_similarity = _rearrange_to_test(
            model.item_similarity.todense(),
            row_ids,
            col_ids,
            model.item2index,
            model.item2index,
        )
        assert np.array_equal(
            true_item_similarity.astype(test_item_similarity.dtype),
            test_item_similarity,
        )
    else:
        test_item_similarity = _rearrange_to_test(
            model.item_similarity, row_ids, col_ids, model.item2index, model.item2index
        )
        assert np.allclose(
            true_item_similarity.astype(test_item_similarity.dtype),
            test_item_similarity,
            atol=sar_settings["ATOL"],
        )


def test_user_affinity(demo_usage_data, sar_settings, header):
    time_now = demo_usage_data[header["col_timestamp"]].max()
    model = SARSingleNode(
        similarity_type="cooccurrence",
        timedecay_formula=True,
        time_decay_coefficient=30,
        time_now=time_now,
        **header
    )
    model.fit(demo_usage_data)

    true_user_affinity, items = load_affinity(sar_settings["FILE_DIR"] + "user_aff.csv")
    user_index = model.user2index[sar_settings["TEST_USER_ID"]]
    sar_user_affinity = np.reshape(
        np.array(
            _rearrange_to_test(
                model.user_affinity, None, items, None, model.item2index
            )[user_index,].todense()
        ),
        -1,
    )
    assert np.allclose(
        true_user_affinity.astype(sar_user_affinity.dtype),
        sar_user_affinity,
        atol=sar_settings["ATOL"],
    )


@pytest.mark.parametrize(
    "threshold,similarity_type,file",
    [(3, "cooccurrence", "count"), (3, "jaccard", "jac"), (3, "lift", "lift")],
)
def test_recommend_k_items(
    threshold, similarity_type, file, header, sar_settings, demo_usage_data
):
    time_now = demo_usage_data[header["col_timestamp"]].max()
    model = SARSingleNode(
        similarity_type=similarity_type,
        timedecay_formula=True,
        time_decay_coefficient=30,
        time_now=time_now,
        threshold=threshold,
        **header
    )
    model.fit(demo_usage_data)

    true_items, true_scores = load_userpred(
        sar_settings["FILE_DIR"]
        + "userpred_"
        + file
        + str(threshold)
        + "_userid_only.csv"
    )
    test_results = model.recommend_k_items(
        demo_usage_data[
            demo_usage_data[header["col_user"]] == sar_settings["TEST_USER_ID"]
        ],
        top_k=10,
        sort_top_k=True,
        remove_seen=True,
    )
    test_items = list(test_results[header["col_item"]])
    test_scores = np.array(test_results["prediction"])
    assert true_items == test_items
    assert np.allclose(true_scores, test_scores, atol=sar_settings["ATOL"])


def test_get_item_based_topk(header, pandas_dummy):

    sar = SARSingleNode(**header)
    sar.fit(pandas_dummy)

    # test with just items provided
    expected = pd.DataFrame(
        dict(UserId=[0, 0, 0], MovieId=[8, 7, 6], prediction=[2.0, 2.0, 2.0])
    )
    items = pd.DataFrame({header["col_item"]: [1, 5, 10]})
    actual = sar.get_item_based_topk(items, top_k=3)
    assert_frame_equal(expected, actual)

    # test with items and users
    expected = pd.DataFrame(
        dict(
            UserId=[100, 100, 100, 1, 1, 1],
            MovieId=[8, 7, 6, 4, 3, 10],
            prediction=[2.0, 2.0, 2.0, 2.0, 2.0, 1.0],
        )
    )
    items = pd.DataFrame(
        {
            header["col_user"]: [100, 100, 1, 100, 1, 1],
            header["col_item"]: [1, 5, 1, 10, 2, 6],
        }
    )
    actual = sar.get_item_based_topk(items, top_k=3, sort_top_k=True)
    assert_frame_equal(expected, actual)

    # test with items, users, and ratings
    expected = pd.DataFrame(
        dict(
            UserId=[100, 100, 100, 1, 1, 1],
            MovieId=[2, 4, 3, 4, 3, 10],
            prediction=[5.0, 5.0, 5.0, 8.0, 8.0, 4.0],
        )
    ).set_index(['UserId', 'MovieId'])
    items = pd.DataFrame(
        {
            header["col_user"]: [100, 100, 1, 100, 1, 1],
            header["col_item"]: [1, 5, 1, 10, 2, 6],
            header["col_rating"]: [5, 1, 3, 1, 5, 4],
        }
    )
    actual = sar.get_item_based_topk(items, top_k=3).set_index(['UserId', 'MovieId'])
    assert_frame_equal(expected, actual, check_like=True)


def test_get_popularity_based_topk(header):

    train_df = pd.DataFrame(
        {
            header["col_user"]: [1, 1, 1, 2, 2, 2, 3, 3, 3],
            header["col_item"]: [1, 2, 3, 1, 3, 4, 5, 6, 1],
            header["col_rating"]: [1, 2, 3, 1, 2, 3, 1, 2, 3]
        }
    )

    sar = SARSingleNode(**header)
    sar.fit(train_df)

    expected = pd.DataFrame(
        dict(MovieId=[1, 3, 4], prediction=[3, 2, 1])
    )
    actual = sar.get_popularity_based_topk(top_k=3, sort_top_k=True)
    assert_frame_equal(expected, actual)
