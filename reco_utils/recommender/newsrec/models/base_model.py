# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from os.path import join
import abc
import time
import numpy as np
import tensorflow as tf
from tensorflow import keras
from reco_utils.recommender.deeprec.deeprec_utils import cal_metric


__all__ = ["BaseModel"]


class BaseModel:
    """Basic class of models

    Attributes:
        hparams (obj): A tf.contrib.training.HParams object, hold the entire set of hyperparameters.
        iterator_creator_train (obj): An iterator to load the data in trainning steps.
        iterator_creator_train (obj): An iterator to load the data in testing steps.
        graph (obj): An optional graph.
        seed (int): Random seed.
    """
    
    def __init__(self, hparams, iterator_creator_train, iterator_creator_test, seed=None):
        """Initializing the model. Create common logics which are needed by all deeprec models, such as loss function, 
        parameter set.

        Args:
            hparams (obj): A tf.contrib.training.HParams object, hold the entire set of hyperparameters.
            iterator_creator_train (obj): An iterator to load the data in trainning steps.
            iterator_creator_train (obj): An iterator to load the data in testing steps.
            graph (obj): An optional graph.
            seed (int): Random seed.
        """
        self.seed = seed
        tf.set_random_seed(seed)
        np.random.seed(seed)

        self.train_iterator = iterator_creator_train(hparams)
        self.test_iterator = iterator_creator_test(hparams)

        self.hparams = hparams
        self.model, self.scorer = self._build_graph()

        self.loss = self._get_loss()
        self.train_optimizer = self._get_opt()

        self.model.compile(
            loss=self.loss, 
            optimizer=self.train_optimizer)

        # set GPU use with demand growth
        gpu_options = tf.GPUOptions(allow_growth=True)

    @abc.abstractmethod
    def _build_graph(self):
        """Subclass will implement this."""
        pass

    def _get_loss(self):
        """Make loss function, consists of data loss and regularization loss
        
        Returns:
            obj: Loss function or loss function name
        """
        if self.hparams.loss == "cross_entropy_loss":
            data_loss = "categorical_crossentropy"
        elif self.hparams.loss == 'log_loss': 
            data_loss = 'binary_crossentropy'
        else:
            raise ValueError("this loss not defined {0}".format(self.hparams.loss))
        return data_loss


    def _get_opt(self):
        """Get the optimizer according to configuration. Usually we will use Adam.
        Returns:
            obj: An optimizer.
        """
        lr = self.hparams.learning_rate
        optimizer = self.hparams.optimizer

        if optimizer == 'adam':
            train_opt = keras.optimizers.Adam(lr=lr)

        return train_opt


    def _get_pred(self, logit, task):
        """Make final output as prediction score, according to different tasks.
        
        Args:
            logit (obj): Base prediction value.
            task (str): A task (values: regression/classification)
        
        Returns:
            obj: Transformed score
        """
        if task == "regression":
            pred = tf.identity(logit)
        elif task == "classification":
            pred = tf.sigmoid(logit)
        else:
            raise ValueError(
                "method must be regression or classification, but now is {0}".format(
                    task
                )
            )
        return pred


    def train(self, train_batch_data):
        """Go through the optimization step once with training data in feed_dict.

        Args:
            sess (obj): The model session object.
            feed_dict (dict): Feed values to train the model. This is a dictionary that maps graph elements to values.

        Returns:
            list: A list of values, including update operation, total loss, data loss, and merged summary.
        """
        rslt = self.model.train_on_batch(
            train_batch_data[0],
            train_batch_data[1]
            )
        return rslt

    def eval(self, eval_batch_data):
        """Evaluate the data in feed_dict with current model.

        Args:
            sess (obj): The model session object.
            feed_dict (dict): Feed values for evaluation. This is a dictionary that maps graph elements to values.

        Returns:
            list: A list of evaluated results, including total loss value, data loss value,
                predicted scores, and ground-truth labels.
        """
        input_data, label = eval_batch_data
        imp_index = input_data[0]
        pred_rslt = self.scorer.predict_on_batch(input_data)

        return pred_rslt, label, imp_index


    def fit(self, train_file, valid_file, test_file=None):
        """Fit the model with train_file. Evaluate the model on valid_file per epoch to observe the training status.
        If test_file is not None, evaluate it too.
        
        Args:
            train_file (str): training data set.
            valid_file (str): validation set.
            test_file (str): test set.

        Returns:
            obj: An instance of self.
        """

        for epoch in range(1, self.hparams.epochs + 1):
            step = 0
            self.hparams.current_epoch = epoch
            epoch_loss = 0
            train_start = time.time()

            for batch_data_input in self.train_iterator.load_data_from_file(train_file):
                step_result = self.train(batch_data_input)
                step_data_loss = step_result
                
                epoch_loss += step_data_loss
                step += 1
                if step % self.hparams.show_step == 0:
                    print(
                        "step {0:d} , total_loss: {1:.4f}, data_loss: {2:.4f}".format(
                            step, epoch_loss, step_data_loss
                        )
                    )

            train_end = time.time()
            train_time = train_end - train_start


            eval_start = time.time()
            
            train_info = ",".join([
                str(item[0]) + ":" + str(item[1])
                    for item in [('logloss loss', epoch_loss/step)]
            ])

            eval_res = self.run_eval(valid_file)
            eval_info = ", ".join(
                [
                    str(item[0]) + ":" + str(item[1])
                    for item in sorted(eval_res.items(), key=lambda x: x[0])
                ]
            )
            if test_file is not None:
                test_res = self.run_eval(test_file)
                test_info = ", ".join(
                    [
                        str(item[0]) + ":" + str(item[1])
                        for item in sorted(test_res.items(), key=lambda x: x[0])
                    ]
                )
            eval_end = time.time()
            eval_time = eval_end - eval_start

            if test_file is not None:
                print(
                    "at epoch {0:d}".format(epoch)
                    + "\ntrain info: "
                    + train_info
                    + "\neval info: "
                    + eval_info
                    + "\ntest info: "
                    + test_info
                )
            else:
                print(
                    "at epoch {0:d}".format(epoch)
                    + "\ntrain info: "
                    + train_info
                    + "\neval info: "
                    + eval_info
                )
            print(
                "at epoch {0:d} , train time: {1:.1f} eval time: {2:.1f}".format(
                    epoch, train_time, eval_time
                )
            )


        return self

    def group_labels(self, labels, preds, group_keys):
        '''Devide labels and preds into several group according to values in group keys.

        Args:
            labels (list): ground truth label list.
            preds (list): prediction score list.
            group_keys (list): group key list.

        Returns:
            all_labels: labels after group.
            all_preds: preds after group.

        '''

        all_keys = list(set(group_keys))
        group_labels = {k: [] for k in all_keys}
        group_preds = {k: [] for k in all_keys}

        for l, p, k in zip(labels, preds, group_keys):
            group_labels[k].append(l)
            group_preds[k].append(p)

        all_labels = []
        all_preds = []
        for k in all_keys:
            all_labels.append(group_labels[k])
            all_preds.append(group_preds[k])

        return all_labels, all_preds


    def run_eval(self, filename):
        """Evaluate the given file and returns some evaluation metrics.
        
        Args:
            filename (str): A file name that will be evaluated.

        Returns:
            dict: A dictionary contains evaluation metrics.
        """
        preds = []
        labels = []
        imp_indexes = []

        for batch_data_input in self.test_iterator.load_data_from_file(filename):
            step_pred, step_labels, step_imp_index = self.eval(batch_data_input)
            preds.extend(np.reshape(step_pred, -1))
            labels.extend(np.reshape(step_labels, -1))
            imp_indexes.extend(np.reshape(step_imp_index, -1))
        
        group_labels, group_preds = self.group_labels(labels, preds, imp_indexes)
        res = cal_metric(group_labels, group_preds, self.hparams.metrics)
        return res
