# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import tensorflow as tf
import numpy as np

from reco_utils.recommender.deeprec.IO.iterator import BaseIterator

__all__ = ["DKNTextIterator"]


class DKNTextIterator(BaseIterator):
    """Data loader for the DKN model.
    DKN requires a special type of data format, where each instance contains a label, the candidate news article,
    and user's clicked news article. Articles are represented by title words and title entities. Words and entities
    are aligned.

    Iterator will not load the whole data into memory. Instead, it loads data into memory
    per mini-batch, so that large files can be used as input data.
    """

    def __init__(self, hparams, graph, col_spliter=" ", ID_spliter="%"):
        """Initialize an iterator. Create necessary placeholders for the model.
        
        Args:
            hparams (obj): Global hyper-parameters. Some key setttings such as #_feature and #_field are there.
            graph (obj): the running graph. All created placeholder will be added to this graph.
            col_spliter (str): column spliter in one line.
            ID_spliter (str): ID spliter in one line.
        """
        self.col_spliter = col_spliter
        self.ID_spliter = ID_spliter
        self.batch_size = hparams.batch_size
        self.doc_size = hparams.doc_size

        self.graph = graph
        with self.graph.as_default():
            self.labels = tf.placeholder(tf.float32, [None, 1], name="label")
            self.candidate_news_index_batch = tf.placeholder(
                tf.int64, [self.batch_size, self.doc_size], name="candidate_news_index"
            )
            self.candidate_news_val_batch = tf.placeholder(
                tf.int64, [self.batch_size, self.doc_size], name="candidate_news_val"
            )
            self.click_news_indices = tf.placeholder(
                tf.int64, [None, 2], name="click_news_indices"
            )
            self.click_news_values = tf.placeholder(
                tf.int64, [None], name="click_news_values"
            )
            self.click_news_weights = tf.placeholder(
                tf.float32, [None], name="click_news_weights"
            )
            self.click_news_shape = tf.placeholder(
                tf.int64, [None], name="dnn_feat_shape"
            )
            self.candidate_news_entity_index_batch = tf.placeholder(
                tf.int64,
                [self.batch_size, self.doc_size],
                name="candidate_news_entity_index",
            )
            self.click_news_entity_values = tf.placeholder(
                tf.int64, [None], name="click_news_entity"
            )

    def parser_one_line(self, line):
        """Parse one string line into feature values.
        
        Args:
            line (str): a string indicating one instance

        Returns:
            list: Parsed results including label, candidate_news_index, candidate_news_val, click_news_index, click_news_val,
            candidate_news_entity_index, click_news_entity_index, impression_id

        """
        impression_id = None
        words = line.strip().split(self.ID_spliter)
        if len(words) == 2:
            impression_id = words[1].strip()

        cols = words[0].strip().split(self.col_spliter)
        label = float(cols[0])
        candidate_news_index = []
        candidate_news_val = []
        click_news_index = []
        click_news_val = []
        candidate_news_entity_index = []
        click_news_entity_index = []

        for news in cols[1:]:
            tokens = news.split(":")
            if tokens[0] == "CandidateNews":
                # word index start by 0
                for item in tokens[1].split(","):
                    candidate_news_index.append(int(item))
                    candidate_news_val.append(float(1))
            elif "clickedNews" in tokens[0]:
                for item in tokens[1].split(","):
                    click_news_index.append(int(item))
                    click_news_val.append(float(1))

            elif tokens[0] == "entity":
                for item in tokens[1].split(","):
                    candidate_news_entity_index.append(int(item))
            elif "entity" in tokens[0]:
                for item in tokens[1].split(","):
                    click_news_entity_index.append(int(item))

            else:
                raise ValueError("data format is wrong")

        return (
            label,
            candidate_news_index,
            candidate_news_val,
            click_news_index,
            click_news_val,
            candidate_news_entity_index,
            click_news_entity_index,
            impression_id,
        )

    def load_data_from_file(self, infile):
        """Read and parse data from a file.
        
        Args:
            infile (str): text input file. Each line in this file is an instance.

        Returns:
            obj: An iterator that will yields parsed results, in the format of graph feed_dict.
        """
        candidate_news_index_batch = []
        candidate_news_val_batch = []
        click_news_index_batch = []
        click_news_val_batch = []
        candidate_news_entity_index_batch = []
        click_news_entity_index_batch = []
        label_list = []
        impression_id_list = []
        cnt = 0

        with tf.gfile.GFile(infile, "r") as rd:
            while True:
                line = rd.readline()
                if not line:
                    break

                label, candidate_news_index, candidate_news_val, click_news_index, click_news_val, candidate_news_entity_index, click_news_entity_index, impression_id = self.parser_one_line(
                    line
                )

                candidate_news_index_batch.append(candidate_news_index)
                candidate_news_val_batch.append(candidate_news_val)
                click_news_index_batch.append(click_news_index)
                click_news_val_batch.append(click_news_val)
                candidate_news_entity_index_batch.append(candidate_news_entity_index)
                click_news_entity_index_batch.append(click_news_entity_index)
                label_list.append(label)
                impression_id_list.append(impression_id)

                cnt += 1
                if cnt >= self.batch_size:
                    res = self._convert_data(
                        label_list,
                        candidate_news_index_batch,
                        candidate_news_val_batch,
                        click_news_index_batch,
                        click_news_val_batch,
                        candidate_news_entity_index_batch,
                        click_news_entity_index_batch,
                    )
                    yield self.gen_feed_dict(res)
                    candidate_news_index_batch = []
                    candidate_news_val_batch = []
                    click_news_index_batch = []
                    click_news_val_batch = []
                    candidate_news_entity_index_batch = []
                    click_news_entity_index_batch = []
                    label_list = []
                    impression_id_list = []
                    cnt = 0

    def _convert_data(
        self,
        label_list,
        candidate_news_index_batch,
        candidate_news_val_batch,
        click_news_index_batch,
        click_news_val_batch,
        candidate_news_entity_index_batch,
        click_news_entity_index_batch,
    ):
        """Convert data into numpy arrays that are good for further model operation.
        
        Args:
            label_list (list): a list of ground-truth labels.
            candidate_news_index_batch (list): the candidate news article's words indices
            candidate_news_val_batch (list): the candidate news article's word values. For now the values are always 1.0
            click_news_index_batch (list): words indices for user's clicked news articles
            click_news_val_batch (list): words values for user's clicked news articles. For now the values are always 1.0
            candidate_news_entity_index_batch (list): the candidate news article's entities indices
            click_news_entity_index_batch (list): the user's clicked news article's entities indices

        Returns:
            dict: A dictionary, contains multiple numpy arrays that are convenient for further operation.
        """
        instance_cnt = len(label_list)

        click_news_indices = []
        click_news_values = []
        click_news_weights = []
        click_news_shape = [instance_cnt, -1]
        click_news_entity_values = []

        batch_max_len = 0
        for i in range(instance_cnt):
            m = len(click_news_index_batch[i])
            batch_max_len = m if m > batch_max_len else batch_max_len
            for j in range(m):
                click_news_indices.append([i, j])
                click_news_values.append(click_news_index_batch[i][j])
                click_news_weights.append(click_news_val_batch[i][j])
                click_news_entity_values.append(click_news_entity_index_batch[i][j])

        click_news_shape[1] = batch_max_len

        res = {}
        res["labels"] = np.asarray([[label] for label in label_list], dtype=np.float32)
        res["candidate_news_index_batch"] = np.asarray(
            candidate_news_index_batch, dtype=np.int64
        )
        res["candidate_news_val_batch"] = np.asarray(
            candidate_news_val_batch, dtype=np.float32
        )
        res["click_news_indices"] = np.asarray(click_news_indices, dtype=np.int64)
        res["click_news_values"] = np.asarray(click_news_values, dtype=np.int64)
        res["click_news_weights"] = np.asarray(click_news_weights, dtype=np.float32)
        res["click_news_shape"] = np.asarray(click_news_shape, dtype=np.int64)
        res["candidate_news_entity_index_batch"] = np.asarray(
            candidate_news_entity_index_batch, dtype=np.int64
        )
        res["click_news_entity_values"] = np.asarray(
            click_news_entity_values, dtype=np.int64
        )
        return res

    def gen_feed_dict(self, data_dict):
        """Construct a dictionary that maps graph elements to values.
        
        Args:
            data_dict (dict): a dictionary that maps string name to numpy arrays.

        Returns:
            dict: a dictionary that maps graph elements to numpy arrays.

        """
        feed_dict = {
            self.labels: data_dict["labels"].reshape([-1, 1]),
            self.candidate_news_index_batch: data_dict[
                "candidate_news_index_batch"
            ].reshape([self.batch_size, self.doc_size]),
            self.candidate_news_val_batch: data_dict[
                "candidate_news_val_batch"
            ].reshape([self.batch_size, self.doc_size]),
            self.click_news_indices: data_dict["click_news_indices"].reshape([-1, 2]),
            self.click_news_values: data_dict["click_news_values"],
            self.click_news_weights: data_dict["click_news_weights"],
            self.click_news_shape: data_dict["click_news_shape"],
            self.candidate_news_entity_index_batch: data_dict[
                "candidate_news_entity_index_batch"
            ].reshape([-1, self.doc_size]),
            self.click_news_entity_values: data_dict["click_news_entity_values"],
        }
        return feed_dict
