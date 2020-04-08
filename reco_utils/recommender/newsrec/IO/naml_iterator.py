# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import tensorflow as tf
import numpy as np

from reco_utils.recommender.deeprec.IO.iterator import BaseIterator

__all__ = ["NAMLIterator"]


class NAMLIterator(BaseIterator):
    """Train data loader for NAML model.
    The model require a special type of data format, where each instance contains a label, impresion id, user id,
    the candidate news articles and user's clicked news article. Articles are represented by title words,
    body words, verts and subverts. 

    Iterator will not load the whole data into memory. Instead, it loads data into memory
    per mini-batch, so that large files can be used as input data.

    Attributes:
        col_spliter (str): column spliter in one line.
        ID_spliter (str): ID spliter in one line.
        batch_size (int): the samples num in one batch.
        doc_size (int): max word num in news title.
        his_size (int): max clicked news num in user click history.
    """

    def __init__(self, hparams, npratio=0, col_spliter=" ", ID_spliter="%"):
        """Initialize an iterator. Create necessary placeholders for the model.
        
        Args:
            hparams (obj): Global hyper-parameters. Some key setttings such as head_num and head_dim are there.
            graph (obj): the running graph. All created placeholder will be added to this graph.
            col_spliter (str): column spliter in one line.
            ID_spliter (str): ID spliter in one line.
        """
        self.col_spliter = col_spliter
        self.ID_spliter = ID_spliter
        self.batch_size = hparams.batch_size
        self.doc_size = hparams.doc_size
        self.his_size = hparams.his_size
        self.npratio = npratio

    def parser_one_line(self, line):
        """Parse one string line into feature values.
        
        Args:
            line (str): a string indicating one instance.

        Returns:
            list: Parsed results including label, impression id , user id, 
            candidate_title_index, clicked_title_index, candidate_body_index,
            clicked_body_index, candidate_vert_index, clicked_vert_index,
            candidate_subvert_index, clicked_suvert_index.
        """
        words = line.strip().split(self.ID_spliter)

        cols = words[0].strip().split(self.col_spliter)
        label = [float(i) for i in cols[: self.npratio + 1]]
        candidate_title_index = []
        click_title_index = []
        candidate_body_index = []
        click_body_index = []
        candidate_vert_index = []
        click_vert_index = []
        candidate_subvert_index = []
        click_subvert_index = []
        imp_index = []
        user_index = []

        for news in cols[self.npratio + 1 :]:
            tokens = news.split(":")
            if "Impression" in tokens[0]:
                imp_index.append(int(tokens[1]))
            elif "User" in tokens[0]:
                user_index.append(int(tokens[1]))
            elif "CandidateTitle" in tokens[0]:
                # word index start by 0
                candidate_title_index.append([int(i) for i in tokens[1].split(",")])
            elif "ClickedTitle" in tokens[0]:
                click_title_index.append([int(i) for i in tokens[1].split(",")])
            elif "CandidateBody" in tokens[0]:
                candidate_body_index.append([int(i) for i in tokens[1].split(",")])
            elif "ClickedBody" in tokens[0]:
                click_body_index.append([int(i) for i in tokens[1].split(",")])
            elif "CandidateVert" in tokens[0]:
                candidate_vert_index.append([int(tokens[1])])
            elif "ClickedVert" in tokens[0]:
                click_vert_index.append([int(tokens[1])])
            elif "CandidateSubvert" in tokens[0]:
                candidate_subvert_index.append([int(tokens[1])])
            elif "ClickedSubvert" in tokens[0]:
                click_subvert_index.append([int(tokens[1])])
            else:
                print(tokens[0])
                raise ValueError("data format is wrong")

        return (
            label,
            imp_index,
            user_index,
            candidate_title_index,
            click_title_index,
            candidate_body_index,
            click_body_index,
            candidate_vert_index,
            click_vert_index,
            candidate_subvert_index,
            click_subvert_index,
        )

    def load_data_from_file(self, infile):
        """Read and parse data from a file.
        
        Args:
            infile (str): text input file. Each line in this file is an instance.

        Returns:
            obj: An iterator that will yields parsed results, in the format of graph feed_dict.
        """
        label_list = []
        imp_indexes = []
        user_indexes = []
        candidate_title_indexes = []
        click_title_indexes = []
        candidate_body_indexes = []
        click_body_indexes = []
        candidate_vert_indexes = []
        click_vert_indexes = []
        candidate_subvert_indexes = []
        click_subvert_indexes = []
        cnt = 0

        with tf.gfile.GFile(infile, "r") as rd:
            while True:
                line = rd.readline()
                if not line:
                    break

                (
                    label,
                    imp_index,
                    user_index,
                    candidate_title_index,
                    click_title_index,
                    candidate_body_index,
                    click_body_index,
                    candidate_vert_index,
                    click_vert_index,
                    candidate_subvert_index,
                    click_subvert_index,
                ) = self.parser_one_line(line)

                candidate_title_indexes.append(candidate_title_index)
                click_title_indexes.append(click_title_index)
                candidate_body_indexes.append(candidate_body_index)
                click_body_indexes.append(click_body_index)
                candidate_vert_indexes.append(candidate_vert_index)
                click_vert_indexes.append(click_vert_index)
                candidate_subvert_indexes.append(candidate_subvert_index)
                click_subvert_indexes.append(click_subvert_index)
                imp_indexes.append(imp_index)
                user_indexes.append(user_index)
                label_list.append(label)

                cnt += 1
                if cnt >= self.batch_size:
                    yield self._convert_data(
                        label_list,
                        imp_indexes,
                        user_indexes,
                        candidate_title_indexes,
                        click_title_indexes,
                        candidate_body_indexes,
                        click_body_indexes,
                        candidate_vert_indexes,
                        click_vert_indexes,
                        candidate_subvert_indexes,
                        click_subvert_indexes,
                    )
                    label_list = []
                    imp_indexes = []
                    user_indexes = []
                    candidate_title_indexes = []
                    click_title_indexes = []
                    candidate_body_indexes = []
                    click_body_indexes = []
                    candidate_vert_indexes = []
                    click_vert_indexes = []
                    candidate_subvert_indexes = []
                    click_subvert_indexes = []
                    cnt = 0

    def _convert_data(
        self,
        label_list,
        imp_indexes,
        user_indexes,
        candidate_title_indexes,
        click_title_indexes,
        candidate_body_indexes,
        click_body_indexes,
        candidate_vert_indexes,
        click_vert_indexes,
        candidate_subvert_indexes,
        click_subvert_indexes,
    ):
        """Convert data into numpy arrays that are good for further model operation.
        
        Args:
            label_list (list): a list of ground-truth labels.
            imp_indexes (list): a list of impression indexes.
            user_indexes (list): a list of user indexes.
            candidate_title_indexes (list): the candidate news titles' words indices.
            click_title_indexes (list): words indices for user's clicked news titles.
            candidate_body_indexes (list): the candidate news bodies' words indices.
            click_body_indexes (list): words indices for user's clicked news bodies.
            candidate_vert_indexes (list): the candidate news vert indexes.
            click_vert_indexes (list): vert indexes for user's clicked news.
            candidate_subvert_indexes (list): the candidate news subvert indexes.
            click_subvert_indexes (list): subvert indexes for user's clicked news.
            
        Returns:
            dict: A dictionary, contains multiple numpy arrays that are convenient for further operation.
        """

        labels = np.asarray(label_list, dtype=np.float32)
        imp_indexes = np.asarray(imp_indexes, dtype=np.int32)
        user_indexes = np.asarray(user_indexes, dtype=np.int32)
        candidate_title_index_batch = np.asarray(
            candidate_title_indexes, dtype=np.int64
        )
        click_title_index_batch = np.asarray(click_title_indexes, dtype=np.int64)
        candidate_body_index_batch = np.asarray(candidate_body_indexes, dtype=np.int64)
        click_body_index_batch = np.asarray(click_body_indexes, dtype=np.int64)
        candidate_vert_index_batch = np.asarray(candidate_vert_indexes, dtype=np.int64)
        click_vert_index_batch = np.asarray(click_vert_indexes, dtype=np.int64)
        candidate_subvert_index_batch = np.asarray(
            candidate_subvert_indexes, dtype=np.int64
        )
        click_subvert_index_batch = np.asarray(click_subvert_indexes, dtype=np.int64)
        return {
            "impression_index_batch": imp_indexes,
            "user_index_batch": user_indexes,
            "clicked_title_batch": click_title_index_batch,
            "clicked_body_batch": click_body_index_batch,
            "clicked_vert_batch": click_vert_index_batch,
            "clicked_subvert_batch": click_subvert_index_batch,
            "candidate_title_batch": candidate_title_index_batch,
            "candidate_body_batch": candidate_body_index_batch,
            "candidate_vert_batch": candidate_vert_index_batch,
            "candidate_subvert_batch": candidate_subvert_index_batch,
            "labels": labels,
        }
