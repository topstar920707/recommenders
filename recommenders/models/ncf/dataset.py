import sys
import os # DELETE
sys.path.append("/home/anta/notebooks/recommenders") # DELETE
from collections import OrderedDict
import random
import numpy as np
import pandas as pd
import warnings
import math # DELETE?
import csv

from recommenders.utils.constants import (
    DEFAULT_ITEM_COL,
    DEFAULT_USER_COL,
    DEFAULT_RATING_COL
)


class DataFile():

    def __init__(
        self, filename, col_user, col_item, col_rating, col_test_batch=None,
        binary=True, index_data=True, batch_indices=None
    ):
        self.filename = filename
        self.col_user = col_user
        self.col_item = col_item
        self.col_rating = col_rating
        self.col_test_batch = col_test_batch
        self.expected_fields = [self.col_user, self.col_item, self.col_rating]
        if self.col_test_batch is not None:
            self.expected_fields.append(self.col_test_batch)
        self.binary = binary
        self.batch_indices = batch_indices
        if index_data:
            self._index_data()


    def _index_data(self):

        print("Indexing file {} ...".format(self.filename))

        with self:
            current_user = None
            current_user_items = []
            user_line_start = 1
            self.users = OrderedDict()
            self.items = []
            self.item2id, self.user2id = {}, {}
            for user, item, _, _ in self:
                if self.line_num == 1:
                    current_user = user
                if item not in self.items:
                    self.items.append(item)
                    self.item2id[item] = len(self.item2id)

                current_user_items.append(item)

                if (user != current_user) or self.EOF:
                    user_line_end = self.line_num - 1
                    
                    if self.EOF:
                        current_user = user
                        user_line_end = self.line_num
                        
                    if current_user in self.users:
                        raise ValueError("File {} is not sorted by user".format(self.filename))

                    self.users[current_user] = (user_line_start, user_line_end)
                    self.user2id[current_user] = len(self.user2id)
                    
                    current_user = user
                    current_user_items = []
                    user_line_start = self.line_num
                        
                self.data_len = self.line_num - 1


    def _check_for_missing_fields(self, fields_to_check):
        missing_fields = set(fields_to_check).difference(set(self.reader.fieldnames))
        if len(missing_fields):
            raise ValueError("Columns {} not in header of file {}".format(missing_fields, self.filename))
    def __enter__(self, *args):
        self.file = open(self.filename, 'r', encoding='UTF8')
        self.reader = csv.DictReader(self.file)
        self._check_for_missing_fields(self.expected_fields)
        self.EOF = False
        self.line_num = 0
        return self


    def __exit__(self, *args):
        self.file.close()
        self.reader = None


    def __iter__(self):
        return self
    

    def __next__(self):
        if self.EOF:
            raise StopIteration
        if self.line_num == 0:
            self.last_row = next(self.reader, None)
            if self.last_row is None:
                raise Exception("{} is empty.".format(self.filename))
        else:
            self.last_row = self.current_row
        self.current_row = next(self.reader, None)
        self.line_num += 1
        if self.current_row is None:
            self.EOF = True

        return self._extract_row_data(self.last_row)


    def _extract_row_data(self, row):
        user = int(row[self.col_user])
        item = int(row[self.col_item])
        rating = float(row[self.col_rating])
        if self.binary:
            rating = float(rating > 0)
        test_batch = None
        if self.col_test_batch:
            test_batch = int(row[self.col_test_batch])
        return user, item, rating, test_batch


    def _load_data(self, line_start, line_end):
        records = []
        while self.line_num < line_end:
            user, item, rating, test_batch = next(self)
            if self.line_num >= line_start:
                record = {self.col_user: user, self.col_item: item, self.col_rating: rating}
                if test_batch is not None:
                    record[self.col_test_batch] = test_batch
                records.append(record)
            
        return pd.DataFrame.from_records(records)


    def load_user_data(self, user):
        try:
            line_start, line_end = self.users[user]
        except:
            raise Exception("User {} not in dataset".format(user))

        user_data = self._load_data(line_start, line_end)
        if not user_data.shape[0] or not all(x == user for x in user_data[self.col_user]):
            raise Exception("User {} not found in expected location in file. Perhaps the file has changed.".format(user))
        
        return user_data

    
    def load_batch_index(self, batch_index):
        try:
            line_start, line_end = self.batch_indices[batch_index]
        except:
            raise Exception("Batch index {} not in dataset".format(batch_index))

        batch_data = self._load_data(line_start, line_end)
        if not batch_data.shape[0] or not all(x == batch_index for x in batch_data[self.col_test_batch]):
            raise Exception("Batch index {} not found in expected location in file. Perhaps the file has changed.".format(batch_index))

        del batch_data[self.col_test_batch]
        
        return batch_data


class Dataset(object):
    """Dataset class for NCF"""

    def __init__(
        self,
        train_file,
        test_file=None,
        test_file_full=None,
        overwrite_test_file_full=False,
        n_neg=4,
        n_neg_test=100,
        col_user=DEFAULT_USER_COL,
        col_item=DEFAULT_ITEM_COL,
        col_rating=DEFAULT_RATING_COL,
        binary=True,
        seed=None,
        sample_with_replacement=False,
        print_warnings=True
    ):
        """Constructor
        Args:
            train_file (str): Path to training dataset file.
            test_file (str): Path to test dataset file.
            test_file_full (str): Path to full test dataset file including negative samples.
            overwrite_test_file_full (bool): If true, recreate and overwrite test_file_full.
            n_neg (int): Number of negative samples per positive example for training set.
            n_neg_test (int): Number of negative samples per positive example for test set.
            col_user (str): User column name.
            col_item (str): Item column name.
            col_rating (str): Rating column name.
            binary (bool): If true, set rating > 0 to rating = 1.
            seed (int): Seed.
            sample_with_replacement (bool): If true, sample negative examples with replacement,
                otherwise without replacement.
            print_warnings (bool): If true, prints warnings if sampling without replacement and
                there are not enough items to sample from to satisfy n_neg or n_neg_test.
        """
        self.train_file = train_file
        self.test_file = test_file
        self.test_file_full = test_file_full
        self.overwrite_test_file_full = overwrite_test_file_full
        self.n_neg = n_neg
        self.n_neg_test = n_neg_test
        self.col_user = col_user
        self.col_item = col_item
        self.col_rating = col_rating
        self.binary = binary
        self.sample_with_replacement = sample_with_replacement
        self.print_warnings = print_warnings

        self.col_test_batch = "test_batch"
        
        # set sampling method to use
        if self.sample_with_replacement:
            self._sample = self._sample_negatives_with_replacement
        else:
            self._sample = self._sample_negatives_without_replacement

        self.train_datafile = DataFile(
            filename=self.train_file,
            col_user=self.col_user,
            col_item=self.col_item,
            col_rating=self.col_rating,
            binary=self.binary
        )

        self.n_users = len(self.train_datafile.users)
        self.n_items = len(self.train_datafile.items)
        self.user2id = self.train_datafile.user2id
        self.item2id = self.train_datafile.item2id
        self.id2user = {self.user2id[k]: k for k in self.user2id}
        self.id2item = {self.item2id[k]: k for k in self.item2id}
        self.train_len = self.train_datafile.data_len
            
        if self.test_file is not None:
            self.test_datafile = DataFile(
                filename=self.test_file,
                col_user=self.col_user,
                col_item=self.col_item,
                col_rating=self.col_rating,
                binary=self.binary
            )
            if self.test_file_full is None:
                self.test_file_full = os.path.splitext(self.test_file)[0] + "_full.csv"
            if os.path.isfile(self.test_file_full) and not self.overwrite_test_file_full:
                self._load_test_file()
            else:
                self._create_test_file()
        
        # set random seed
        random.seed(seed)


    def _load_test_file(self):

        print("Loading existing test file full {} ...".format(self.test_file_full))
        self.test_full_datafile = DataFile(
            filename=self.test_file_full,
            col_user=self.col_user,
            col_item=self.col_item,
            col_rating=self.col_rating,
            col_test_batch=self.col_test_batch,
            binary=self.binary,
            index_data=False
        )

        current_test_batch = 0
        batch_line_start = 1
        batch_line_end = 0
        batch_indices = OrderedDict()
        with self.test_full_datafile as test_full_datafile:
            for user, item, _, test_batch in self.test_full_datafile:
                if user not in self.train_datafile.users:
                    raise ValueError("User {} in test set but not in training set".format(user))
                if item not in self.train_datafile.items:
                    raise ValueError("Item {} in test set but not in training set".format(item))
                if (test_batch != current_test_batch) or test_full_datafile.EOF:
                    if not (test_batch == current_test_batch + 1) and not test_full_datafile.EOF:
                        raise ValueError("Test file full not sorted by batch number")
                    batch_line_end = test_full_datafile.line_num - 1
                    batch_indices[current_test_batch] = (batch_line_start, batch_line_end)
                    batch_line_start = test_full_datafile.line_num
                    current_test_batch = test_batch
            
            test_full_datafile.batch_indices = batch_indices


    def _sample_negatives_with_replacement(self, user_negative_item_pool, n_samples):
        return random.choices(user_negative_item_pool, k=n_samples)


    def _sample_negatives_without_replacement(self, user_negative_item_pool, n_samples):
        return random.sample(user_negative_item_pool, k=n_samples)


    def _get_user_negatives_pool(self, user_positive_item_pool):
        # get list of items user has not interacted with
        return list(set(self.train_datafile.items) - user_positive_item_pool)


    def _get_negative_examples(self, user, user_negative_item_pool, n_samples):
        # create dataframe containing negative examples for user assigned zero rating
        user_negative_samples = self._sample(user_negative_item_pool, n_samples)
        return pd.DataFrame({
            self.col_user: [user] * n_samples,
            self.col_item: user_negative_samples,
            self.col_rating: [0.0] * n_samples
        })

    
    def _check_sample_size(self, n_samples, population_size, user, max_n_neg, train_set=True):
        if n_samples > population_size:
            n_samples = min(n_samples, population_size)
            if self.print_warnings:
                n_neg_var = "n_neg" if train_set else "n_neg_test"
                dataset_name = "training" if train_set else "test"
                warnings.warn(
                    "The population of negative items to sample from is too small for user {}. \
                    Reducing {} for this user to {}. \
                    The number of negative samples in the {} set will not be equal for all users. \
                    If an equal number of negative samples for each user is required, \
                    sample with replacement or reduce {}. \
                    This warning can be turned off by setting print_warnings=False" \
                    .format(user, n_neg_var, max_n_neg, dataset_name, n_neg_var)
                )
        
        return n_samples
        
    
    def _create_test_file(self):

        print("Creating full test set file {} ...".format(self.test_file_full))

        # create empty test_file_full
        pd.DataFrame(
            columns=[self.col_user, self.col_item, self.col_rating, self.col_test_batch]
        ).to_csv(self.test_file_full, index=False)
            
        batch_idx = 0
        batch_line_start = 1
        batch_line_end = 0
        batch_indices = OrderedDict()

        with self.train_datafile as train_datafile:
            with self.test_datafile as test_datafile:
                for user in test_datafile.users.keys():
                    if user in train_datafile.users:
                        user_test_data = test_datafile.load_user_data(user)
                        user_train_data = train_datafile.load_user_data(user)
                        user_positive_item_pool = set(
                            user_test_data[self.col_item].unique()).union(user_train_data[self.col_item].unique()
                        )
                        user_negative_item_pool = self._get_user_negatives_pool(user_positive_item_pool)
                        n_samples = self.n_neg_test

                        # reduce n_samples if sample pool is not large enough
                        if not self.sample_with_replacement:
                            population_size = len(user_negative_item_pool)
                            max_n_neg_test = population_size
                            n_samples = self._check_sample_size(
                                n_samples, population_size, user, max_n_neg_test, train_set=False
                            )
                        
                        user_examples_dfs = []
                        for positive_example in np.array_split(user_test_data, user_test_data.shape[0]):
                            negative_examples = self._get_negative_examples(user, user_negative_item_pool, n_samples)
                            examples = pd.concat([positive_example, negative_examples])
                            examples[self.col_test_batch] = batch_idx
                            user_examples_dfs.append(examples)
                            batch_line_end = batch_line_start + examples.shape[0] - 1
                            batch_indices[batch_idx] = (batch_line_start, batch_line_end)
                            batch_idx += 1
                            batch_line_start = batch_line_end + 1
                            
                        user_examples = pd.concat(user_examples_dfs)
                        
                        user_examples.to_csv(self.test_file_full, mode='a', index=False, header=False)
   
        self.test_full_datafile = DataFile(
            filename=self.test_file_full,
            col_user=self.col_user,
            col_item=self.col_item,
            col_rating=self.col_rating,
            col_test_batch=self.col_test_batch,
            binary=self.binary,
            batch_indices=batch_indices,
            index_data=False
        )


    def _split_into_batches(self, shuffle_buffer, batch_size):
        for i in range(0, len(shuffle_buffer), batch_size): 
            yield shuffle_buffer[i:i + batch_size]


    def _prepare_batch_with_id(self, batch):
        return [
            [self.user2id[user] for user in batch[self.col_user].values],
            [self.item2id[item] for item in batch[self.col_item].values],
            batch[self.col_rating].values.tolist()
        ]
    

    def _prepare_batch_without_id(self, batch):
        return [
            batch[self.col_user].values.tolist(),
            batch[self.col_item].values.tolist(),
            batch[self.col_rating].values.tolist()
        ]


    def _release_shuffle_buffer(self, shuffle_buffer, batch_size, yield_id, write_to = None):
        prepare_batch = self._prepare_batch_with_id if yield_id else self._prepare_batch_without_id
        shuffle_buffer_df = pd.concat(shuffle_buffer)
        shuffle_buffer_df = shuffle_buffer_df.sample(shuffle_buffer_df.shape[0])
        for batch in self._split_into_batches(shuffle_buffer_df, batch_size):
            if batch.shape[0] == batch_size:
                if write_to:
                    batch.to_csv(write_to, mode='a', header=False, index=False)
                yield prepare_batch(batch)
            else:
                return batch


    def train_loader(self, batch_size, shuffle_size=None, yield_id=False, write_to=None):
        """
        Generator for serving batches of training data. Positive examples are loaded from the
        original training file, to which negative samples are added. Data is loaded in memory into a
        shuffle buffer up to a maximum of shuffle_size rows, before the data is shuffled and released.
        If out-of-memory errors are encountered, try reducing shuffle_size.

        Args:
            batch_size (int): Number of examples in each batch.
            shuffle_size (int): Maximum Number of examples in shuffle buffer.
            yield_id (bool): If true, return assigned user and item IDs, else return original values.
            write_to (str): Path of file to write full dataset (including negative examples) to. 
        """

        # if shuffle_size not supplied, use (estimated) full data size i.e. complete in-memory shuffle
        if shuffle_size is None:
            shuffle_size = (self.train_len * (self.n_neg + 1))
        
        if write_to:
            pd.DataFrame(columns=[self.col_user, self.col_item, self.col_rating]) \
                .to_csv(write_to, header=True, index=False)
        
        shuffle_buffer = []
        
        with self.train_datafile as train_datafile:
            for user in train_datafile.users:
                user_positive_examples = train_datafile.load_user_data(user)
                user_positive_item_pool = set(user_positive_examples[self.col_item].unique())
                user_negative_item_pool = self._get_user_negatives_pool(user_positive_item_pool)
                n_samples = self.n_neg * user_positive_examples.shape[0]

                # reduce n_samples if sample pool is not large enough
                if not self.sample_with_replacement:
                    population_size = len(user_negative_item_pool)
                    max_n_neg = population_size // user_positive_examples.shape[0]
                    n_samples = self._check_sample_size(
                        n_samples, population_size, user, max_n_neg, train_set=True
                    )

                user_negative_examples = self._get_negative_examples(
                    user, user_negative_item_pool, n_samples
                )
                user_examples = pd.concat([user_positive_examples, user_negative_examples])
                shuffle_buffer.append(user_examples)
                shuffle_buffer_len = sum([df.shape[0] for df in shuffle_buffer])
                if (shuffle_buffer_len >= shuffle_size):
                    buffer_remainder = yield from self._release_shuffle_buffer(
                        shuffle_buffer, batch_size, yield_id, write_to
                    )
                    shuffle_buffer = [buffer_remainder] if buffer_remainder is not None else []
            
            # yield remaining buffer
            yield from self._release_shuffle_buffer(shuffle_buffer, batch_size, yield_id, write_to)


    def test_loader(self, yield_id=False):
        """
        Generator for serving batches of test data. Data is loaded from test_file_full.

        Args:
            yield_id (bool): If true, return assigned user and item IDs, else return original values.
        """
        prepare_batch = self._prepare_batch_with_id if yield_id else self._prepare_batch_without_id

        with self.test_full_datafile as test_full_datafile:
            for test_batch_idx in test_full_datafile.batch_indices:
                test_batch_data = test_full_datafile.load_batch_index(test_batch_idx)
                yield prepare_batch(test_batch_data)


if __name__ == "__main__":

    dirname = "/home/anta/notebooks/recommenders/examples/02_model_hybrid/"
    train_file = os.path.join(dirname, "train.csv")
    test_file = os.path.join(dirname, "test.csv")
    test_file_full = os.path.join(dirname, "test_full.csv")

    data = Dataset(train_file, test_file, test_file_full=test_file_full, overwrite_test_file_full=True)
    # data = Dataset(train_file)

    with data.train_datafile as f:
        x = f.load_user_data(1)
        print(x.head(1))  # should have item 168
        print(x.tail(1)) # should have item 21
        x = f.load_user_data(943)
        print(x.head(1))  # should have item 64
        print(x.tail(1)) # should have item 27

    if not data.train_datafile.file.closed:
        raise Exception("Not closed")

    # with data.test_datafile as f:
    #     x = f.load_user_data(1)
    #     print(x.head(1))  # should have item 149
    #     print(x.tail(1)) # should have item 74
    #     x = f.load_user_data(943)
    #     print(x.head(1))  # should have item 54
    #     print(x.tail(1)) # should have item 234

    # with data.test_full_datafile as f:
    #     x = f.load_batch_index(0)
    #     print(x.head(1)) # 149
    #     x = f.load_batch_index(24890)
    #     print(x.head(1)) # 234

    # data = Dataset(train_file, test_file, test_file_full=test_file_full, overwrite_test_file_full=False)

    # with data.test_full_datafile as f:
    #     x = f.load_batch_index(0)
    #     print(x.head(1)) # 149
    #     x = f.load_batch_index(24890)
    #     print(x.head(1)) # 234

    for i, x in enumerate(data.train_loader(32, shuffle_size=None, yield_id=True, write_to="./train_full.csv")):
        if i % 1000 == 0:
            print(i)
            print(x)
            print(" ")

    print("test loader")
    for i, x in enumerate(data.test_loader(yield_id=True)):
        if i % 1000 == 0:
            print(i)
            print(x)
            print(" ")

    # reader = CsvReader(test_file, expected_fields=["userID", "itemID", "rating"])
    # print(reader.line_num)
    # row = next(reader)
    # print(reader.line_num, reader.EOF, row)
    # for row in reader:
    #     print(reader.line_num, reader.EOF, row)

    # test_datafile = DataFile(
    #     test_file, expected_fields=["userID", "itemID", "rating"],
    #     col_user="userID", col_item="itemID", col_rating="rating",
    #     binary=True
    # )


    # test_datafile.open()

    # print(test_datafile.load_user_data(943))
    # user, item, rating, _ = next(test_datafile)
    # print(user, item, rating)

    # test_datafile.close()

    # for user, item, rating, _ in test_datafile:
    #     print(test_datafile.reader.line_num, user, item, rating)

    # test_datafile.close()

    # row = next(reader)
    # print(reader.line_num, reader.EOF, row)

    # data = Dataset(train_file=train_file, test_file=test_file)