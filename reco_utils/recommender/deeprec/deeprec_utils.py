# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import tensorflow as tf
import six
import os
from sklearn.metrics import (
    roc_auc_score,
    log_loss,
    mean_squared_error,
    accuracy_score,
    f1_score,
)
import numpy as np
import yaml
import zipfile
from reco_utils.dataset.url_utils import maybe_download


def flat_config(config):
    """Flat config loaded from a yaml file to a flat dict.
    Args:
        config (dict): Configuration loaded from a yaml file.

    Returns:
        dict: Configuration dictionary.
    """
    f_config = {}
    category = config.keys()
    for cate in category:
        for key, val in config[cate].items():
            f_config[key] = val
    return f_config


def check_type(config):
    """Check that the config parameters are the correct type
    Args:
        config (dict): Configuration dictionary.

    Raises:
        TypeError: If the parameters are not the correct type.
    """

    int_parameters = [
        "word_size",
        "entity_size",
        "doc_size",
        "FEATURE_COUNT",
        "FIELD_COUNT",
        "dim",
        "epochs",
        "batch_size",
        "show_step",
        "save_epoch",
        "PAIR_NUM",
        "DNN_FIELD_NUM",
        "attention_layer_sizes",
        "n_user",
        "n_item",
        "n_user_attr",
        "n_item_attr",
    ]
    for param in int_parameters:
        if param in config and not isinstance(config[param], int):
            raise TypeError("Parameters {0} must be int".format(param))

    float_parameters = [
        "init_value",
        "learning_rate",
        "embed_l2",
        "embed_l1",
        "layer_l2",
        "layer_l1",
        "mu",
    ]
    for param in float_parameters:
        if param in config and not isinstance(config[param], float):
            raise TypeError("Parameters {0} must be float".format(param))

    str_parameters = [
        "train_file",
        "eval_file",
        "test_file",
        "infer_file",
        "method",
        "load_model_name",
        "infer_model_name",
        "loss",
        "optimizer",
        "init_method",
        "attention_activation",
    ]
    for param in str_parameters:
        if param in config and not isinstance(config[param], str):
            raise TypeError("Parameters {0} must be str".format(param))

    list_parameters = ["layer_sizes", "activation", "dropout"]
    for param in list_parameters:
        if param in config and not isinstance(config[param], list):
            raise TypeError("Parameters {0} must be list".format(param))


def check_nn_config(f_config):
    """Check neural networks configuration.
    
    Args:
        f_config (dict): Neural network configuration.
    
    Raises:
        ValueError: If the parameters are not correct.
    """
    if f_config["model_type"] in ["fm", "FM"]:
        required_parameters = ["FEATURE_COUNT", "dim", "loss", "data_format", "method"]
    elif f_config["model_type"] in ["lr", "LR"]:
        required_parameters = ["FEATURE_COUNT", "loss", "data_format", "method"]
    elif f_config["model_type"] in ["dkn", "DKN"]:
        required_parameters = [
            "doc_size",
            "wordEmb_file",
            "entityEmb_file",
            "word_size",
            "entity_size",
            "data_format",
            "dim",
            "layer_sizes",
            "activation",
            "attention_activation",
            "attention_activation",
            "attention_dropout",
            "loss",
            "data_format",
            "dropout",
            "method",
            "num_filters",
            "filter_sizes",
        ]
    elif f_config["model_type"] in ["exDeepFM", "xDeepFM"]:
        required_parameters = [
            "FIELD_COUNT",
            "FEATURE_COUNT",
            "method",
            "dim",
            "layer_sizes",
            "cross_layer_sizes",
            "activation",
            "loss",
            "data_format",
            "dropout",
        ]
    else:
        required_parameters = [
            "FIELD_COUNT",
            "FEATURE_COUNT",
            "method",
            "dim",
            "layer_sizes",
            "activation",
            "loss",
            "data_format",
            "dropout",
        ]

    # check required parameters
    for param in required_parameters:
        if param not in f_config:
            raise ValueError("Parameters {0} must be set".format(param))

    if f_config["model_type"] in ["exDeepFM", "xDeepFM"]:
        if f_config["data_format"] != "ffm":
            raise ValueError(
                "For xDeepFM model, data format must be 'ffm', but your set is {0}".format(
                    f_config["data_format"]
                )
            )
    elif f_config["model_type"] in ["dkn", "DKN"]:
        if f_config["data_format"] != "dkn":
            raise ValueError(
                "For dkn model, data format must be 'dkn', but your set is {0}".format(
                    f_config["data_format"]
                )
            )
    else:
        if f_config["data_format"] not in ["fm"]:
            raise ValueError(
                "The default data format should be fm, but your set is {0}".format(
                    f_config["data_format"]
                )
            )
    check_type(f_config)


def load_yaml(filename):
    """Load a yaml file.

    Args:
        filename (str): Filename.

    Returns:
        dict: Dictionary.
    """
    try:
        with open(filename, "r") as f:
            config = yaml.load(f, yaml.SafeLoader)
        return config
    except FileNotFoundError: # for file not found
        raise
    except Exception as e: # for other exceptions
        raise IOError("load {0} error!".format(filename))


def create_hparams(flags):
    """Create the model hyperparameters.

    Args:
        flags (dict): Dictionary with the model requirements.

    Returns:
        obj: Hyperparameter object in TF (tf.contrib.training.HParams).
    """
    return tf.contrib.training.HParams(
        # data
        kg_file=flags["kg_file"] if "kg_file" in flags else None,
        user_clicks=flags["user_clicks"] if "user_clicks" in flags else None,
        FEATURE_COUNT=flags["FEATURE_COUNT"] if "FEATURE_COUNT" in flags else None,
        FIELD_COUNT=flags["FIELD_COUNT"] if "FIELD_COUNT" in flags else None,
        data_format=flags["data_format"] if "data_format" in flags else None,
        PAIR_NUM=flags["PAIR_NUM"] if "PAIR_NUM" in flags else None,
        DNN_FIELD_NUM=flags["DNN_FIELD_NUM"] if "DNN_FIELD_NUM" in flags else None,
        n_user=flags["n_user"] if "n_user" in flags else None,
        n_item=flags["n_item"] if "n_item" in flags else None,
        n_user_attr=flags["n_user_attr"] if "n_user_attr" in flags else None,
        n_item_attr=flags["n_item_attr"] if "n_item_attr" in flags else None,
        iterator_type=flags["iterator_type"] if "iterator_type" in flags else None,
        SUMMARIES_DIR=flags["SUMMARIES_DIR"] if "SUMMARIES_DIR" in flags else None,
        MODEL_DIR=flags["MODEL_DIR"] if "MODEL_DIR" in flags else None,
        # dkn
        wordEmb_file=flags["wordEmb_file"] if "wordEmb_file" in flags else None,
        entityEmb_file=flags["entityEmb_file"] if "entityEmb_file" in flags else None,
        doc_size=flags["doc_size"] if "doc_size" in flags else None,
        word_size=flags["word_size"] if "word_size" in flags else None,
        entity_size=flags["entity_size"] if "entity_size" in flags else None,
        entity_dim=flags["entity_dim"] if "entity_dim" in flags else None,
        entity_embedding_method=flags["entity_embedding_method"]
        if "entity_embedding_method" in flags
        else None,
        transform=flags["transform"] if "transform" in flags else None,
        train_ratio=flags["train_ratio"] if "train_ratio" in flags else None,
        # model
        dim=flags["dim"] if "dim" in flags else None,
        layer_sizes=flags["layer_sizes"] if "layer_sizes" in flags else None,
        cross_layer_sizes=flags["cross_layer_sizes"]
        if "cross_layer_sizes" in flags
        else None,
        cross_layers=flags["cross_layers"] if "cross_layers" in flags else None,
        activation=flags["activation"] if "activation" in flags else None,
        cross_activation=flags["cross_activation"]
        if "cross_activation" in flags
        else "identity",
        user_dropout=flags["user_dropout"] if "user_dropout" in flags else False,
        dropout=flags["dropout"] if "dropout" in flags else [0.0],
        attention_layer_sizes=flags["attention_layer_sizes"]
        if "attention_layer_sizes" in flags
        else None,
        attention_activation=flags["attention_activation"]
        if "attention_activation" in flags
        else None,
        attention_dropout=flags["attention_dropout"]
        if "attention_dropout" in flags
        else 0.0,
        model_type=flags["model_type"] if "model_type" in flags else None,
        method=flags["method"] if "method" in flags else None,
        load_saved_model=flags["load_saved_model"]
        if "load_saved_model" in flags
        else False,
        load_model_name=flags["load_model_name"]
        if "load_model_name" in flags
        else None,
        filter_sizes=flags["filter_sizes"] if "filter_sizes" in flags else None,
        num_filters=flags["num_filters"] if "num_filters" in flags else None,
        mu=flags["mu"] if "mu" in flags else None,
        fast_CIN_d=flags["fast_CIN_d"] if "fast_CIN_d" in flags else 0,
        use_Linear_part=flags["use_Linear_part"]
        if "use_Linear_part" in flags
        else False,
        use_FM_part=flags["use_FM_part"] if "use_FM_part" in flags else False,
        use_CIN_part=flags["use_CIN_part"] if "use_CIN_part" in flags else False,
        use_DNN_part=flags["use_DNN_part"] if "use_DNN_part" in flags else False,
        # train
        init_method=flags["init_method"] if "init_method" in flags else "tnormal",
        init_value=flags["init_value"] if "init_value" in flags else 0.01,
        embed_l2=flags["embed_l2"] if "embed_l2" in flags else 0.0000,
        embed_l1=flags["embed_l1"] if "embed_l1" in flags else 0.0000,
        layer_l2=flags["layer_l2"] if "layer_l2" in flags else 0.0000,
        layer_l1=flags["layer_l1"] if "layer_l1" in flags else 0.0000,
        cross_l2=flags["cross_l2"] if "cross_l2" in flags else 0.0000,
        cross_l1=flags["cross_l1"] if "cross_l1" in flags else 0.0000,
        reg_kg=flags["reg_kg"] if "reg_kg" in flags else 0.0000,
        learning_rate=flags["learning_rate"] if "learning_rate" in flags else 0.001,
        lr_rs=flags["lr_rs"] if "lr_rs" in flags else 1,
        lr_kg=flags["lr_kg"] if "lr_kg" in flags else 0.5,
        kg_training_interval=flags["kg_training_interval"]
        if "kg_training_interval" in flags
        else 5,
        max_grad_norm=flags["max_grad_norm"] if "max_grad_norm" in flags else 2,
        is_clip_norm=flags["is_clip_norm"] if "is_clip_norm" in flags else 0,
        dtype=flags["dtype"] if "dtype" in flags else 32,
        loss=flags["loss"] if "loss" in flags else None,
        optimizer=flags["optimizer"] if "optimizer" in flags else "adam",
        epochs=flags["epochs"] if "epochs" in flags else 10,
        batch_size=flags["batch_size"] if "batch_size" in flags else 1,
        enable_BN=flags["enable_BN"] if "enable_BN" in flags else False,
        # show info
        show_step=flags["show_step"] if "show_step" in flags else 1,
        save_model=flags["save_model"] if "save_model" in flags else True,
        save_epoch=flags["save_epoch"] if "save_epoch" in flags else 5,
        metrics=flags["metrics"] if "metrics" in flags else None,
        write_tfevents=flags["write_tfevents"] if "write_tfevents" in flags else False,
    )


def prepare_hparams(yaml_file=None, **kwargs):
    """Prepare the model hyperparameters and check that all have the correct value.

    Args:
        yaml_file (str): YAML file as configuration.

    Returns:
        obj: Hyperparameter object in TF (tf.contrib.training.HParams).
    """
    if yaml_file is not None:
        config = load_yaml(yaml_file)
        config = flat_config(config)
    else:
        config = {}

    if kwargs:
        for name, value in six.iteritems(kwargs):
            config[name] = value

    check_nn_config(config)
    return create_hparams(config)


def download_deeprec_resources(azure_container_url, data_path, remote_resource_name):
    """Download resources.

    Args:
        azure_container_url (str): URL of Azure container.
        data_path (str): Path to download the resources.
        remote_resource_name (str): Name of the resource.
    """
    os.makedirs(data_path, exist_ok=True)
    remote_path = azure_container_url + remote_resource_name
    maybe_download(remote_path, remote_resource_name, data_path)
    zip_ref = zipfile.ZipFile(os.path.join(data_path, remote_resource_name), "r")
    zip_ref.extractall(data_path)
    zip_ref.close()
    os.remove(os.path.join(data_path, remote_resource_name))


def cal_metric(labels, preds, metrics):
    """Calculate metrics,such as auc, logloss
    FIXME: refactor this with the reco metrics
    """
    res = {}
    for metric in metrics:
        if metric == "auc":
            auc = roc_auc_score(np.asarray(labels), np.asarray(preds))
            res["auc"] = round(auc, 4)
        elif metric == "rmse":
            rmse = mean_squared_error(np.asarray(labels), np.asarray(preds))
            res["rmse"] = np.sqrt(round(rmse, 4))
        elif metric == "logloss":
            # avoid logloss nan
            preds = [max(min(p, 1.0 - 10e-12), 10e-12) for p in preds]
            logloss = log_loss(np.asarray(labels), np.asarray(preds))
            res["logloss"] = round(logloss, 4)
        elif metric == "acc":
            pred = np.asarray(preds)
            pred[pred >= 0.5] = 1
            pred[pred < 0.5] = 0
            acc = accuracy_score(np.asarray(labels), pred)
            res["acc"] = round(acc, 4)
        elif metric == "f1":
            pred = np.asarray(preds)
            pred[pred >= 0.5] = 1
            pred[pred < 0.5] = 0
            f1 = f1_score(np.asarray(labels), pred)
            res["f1"] = round(f1, 4)
        else:
            raise ValueError("not define this metric {0}".format(metric))
    return res
