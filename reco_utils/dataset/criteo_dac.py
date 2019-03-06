# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import atexit
import tarfile
try:
    from pyspark.sql.types import (
        StructType,
        StructField,
        IntegerType,
        StringType,
    )
except ImportError:
    pass  # so the environment without spark doesn't break

from reco_utils.dataset.url_utils import maybe_download, remove_filepath
from reco_utils.common.notebook_utils import is_databricks


CRITEO_URL_FULL = "https://s3-eu-west-1.amazonaws.com/kaggle-display-advertising-challenge-dataset/dac.tar.gz"
CRITEO_URL_SAMPLE = "http://labs.criteo.com/wp-content/uploads/2015/04/dac_sample.tar.gz"


def load_spark_df(
    spark,
    size="sample",
    type="train",
    local_cache_path="dac.tar.gz",
    dbfs_datapath="dbfs:/FileStore/dac", 
    dbutils=None,
):
  """Loads the Criteo DAC dataset as pySpark.DataFrame.

  Download the dataset from https://s3-eu-west-1.amazonaws.com/kaggle-display-advertising-challenge-dataset/dac.tar.gz, untar, and load

  Args:
      spark (pySpark.SparkSession)
      type (str): which dataset to load. 2 options: 'train' or 'test'
      local_cache_path (str): Path where to cache the tar.gz file locally (not dbfs)
      dbfs_datapath: where to store the extracted files
      dbutils (Databricks.dbutils): Databricks utility object
  
  Returns:
      pySpark.DataFrame: Criteo DAC training dataset.
  """
  ## download and untar the train and test files
  extracted_tar_dir_path = _load_datafile(size=size, local_cache_path=local_cache_path, dbutils=dbutils)
  
  if is_databricks():
    try:
        # Driver node's file path
        tar_datapath = "file:" + extracted_tar_dir_path
        ## needs to be on dbfs to load
        dbutils.fs.cp(tar_datapath, dbfs_datapath, recurse=True)
        path = dbfs_datapath
    except:
        raise ValueError("To use on a Databricks notebook, dbutils object should be passed as an argument")
  else:
    path = extracted_tar_dir_path

  datapath, include_label = _manage_data_sizes(size, path, type)
  schema = _get_schema(include_label)
  return spark.read.csv(
       datapath, schema=schema, sep="\t", header=False
  )


def _manage_data_sizes(size, path, type):
  if size == "sample":
    include_label = True
    datapath = os.path.join(path, "dac_sample.txt")
  elif size == "full":
    if type is 'train':
        include_label = True
        datapath = os.path.join(path,'train.txt')
    elif type is 'test':
        include_label = False
        datapath = os.path.join(path,'test.txt')
    else:
        raise ValueError('Unknown type. Only "train" or "test" is allowed.')
  return datapath, include_label


def _get_schema(include_label=True):
  """Create the schema.
  
  For the training data, the schema is:
  
  <label> <integer feature 1> ... <integer feature 13> <categorical feature 1> ... <categorical feature 26>
  
  For the test data, the schema is missing <label>
  
  Run as _get_schema() to create the schema for the training data.
  Run as _get_schema(False) to create the schema for the testing data.
  """
  ## construct the variable names
  if include_label:
    header = ['label']
  else:
    header = []
  header.extend(['int{0:02d}'.format(i) for i in range(13)])
  header.extend(['cat{0:02d}'.format(i) for i in range(26)])
  ## create schema
  schema = StructType()
  ## do label + ints
  n_ints = 14 - (not include_label)
  for i in range(n_ints):
    schema.add(
      StructField(header[i], IntegerType())
    )
  ## do categoricals
  for i in range(26):
    schema.add(
      StructField(header[i+n_ints], StringType())
    )
  return schema


def criteo_urls(size):
  """Return the url of criteo based on the input size

  Args:
    size (str): Size of criteo dataset. It can be "full" or "sample".

  Returns:
    str: url of Criteo dataset.

  """
  url = {
    "full": CRITEO_URL_FULL,
    "sample": CRITEO_URL_SAMPLE
  }
  return url[size]


def download_criteo(size="full", filename="dac.tar.gz", work_directory="."):
    """Download criteo dataset as a compressed file.

    Args:
        size (str): Size of criteo dataset. It can be "full" or "sample".
        filename (str): Filename.
        work_directory (str): Working directory.

    Returns:
        str: Path of the downloaded file.

    """
    url = criteo_urls(size)
    return maybe_download(url, filename, work_directory)


def _load_datafile(size, local_cache_path="dac.tar.gz", dbutils=None):
    """ Download and extract file """

    path, filename = os.path.split(os.path.realpath(local_cache_path))

    # Make sure the temporal tar file gets cleaned up no matter what
    atexit.register(remove_filepath, local_cache_path)

    ## download if it doesn't already exist locally
    download_criteo(size, filename, path)

    #always extract to a subdirectory of cache_path called dac
    extracted_dir=os.path.join(path, "dac")
    print('Extracting component files from {}. This can take 3-5 minutes.'.format(local_cache_path))
    with tarfile.open(local_cache_path) as tar:
        tar.extractall(extracted_dir)
    
    #train_file = os.path.join(extracted_dir,'train.txt')
    #test_file = os.path.join(extracted_dir,'test.txt')
    
    remove_filepath(local_cache_path)

    # Make sure a temporal data file get cleaned up when done
    #atexit.register(remove_filepath, train_file)
    #atexit.register(remove_filepath, test_file)

    return extracted_dir

