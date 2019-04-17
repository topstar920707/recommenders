import json
import os
import requests
import time

NNI_REST_ENDPOINT = 'http://localhost:8080/api/v1/nni'
NNI_STATUS_URL = NNI_REST_ENDPOINT + '/check-status'
NNI_TRIAL_JOBS_URL = NNI_REST_ENDPOINT + '/trial-jobs'
WAITING_TIME = 20
MAX_RETRIES = 5


def get_experiment_status(status_url):
    """
    Helper method. Gets the experiment status from the REST endpoint

    Args:
        status_url (str): URL for the REST endpoint

    Returns:
        str: status of the experiment
    """
    nni_status = requests.get(status_url).json()
    return nni_status['status']


def check_experiment_status(waiting_time=WAITING_TIME * MAX_RETRIES):
    """ Checks the status of the current experiment on the NNI REST endpoint
    Waits until the tuning has completed

    Args:
        waiting_time (int) : time to wait in seconds
    """
    i = 0
    max_retries = int(waiting_time / WAITING_TIME) + 1
    while i < max_retries:
        status = get_experiment_status(NNI_STATUS_URL)
        if status in ['DONE', 'TUNER_NO_MORE_TRIAL']:
            break
        elif status not in ['RUNNING', 'NO_MORE_TRIAL']:
            raise RuntimeError("NNI experiment failed to complete with status {}".format(status))
        time.sleep(WAITING_TIME)
        i += 1
    if i == max_retries:
        raise TimeoutError("check_experiment_status() timed out")


def check_stopped(wait=WAITING_TIME, max_retries=MAX_RETRIES):
    """
    Checks that there is no NNI experiment active (the URL is not accessible)
    This method should be called after 'nnictl stop' for verification
    """
    i = 0
    while i < max_retries:
        try:
            get_experiment_status(NNI_STATUS_URL)
        except:
            break
        time.sleep(wait)
        i += 1
    if i == max_retries:
        raise TimeoutError("check_stopped() timed out")


def check_metrics_written(wait=WAITING_TIME, max_retries=MAX_RETRIES):
    """
    Waits until the metrics have been written to the trial logs
    """
    i = 0
    while i < max_retries:
        all_trials = requests.get(NNI_TRIAL_JOBS_URL).json()
        if all(['finalMetricData' in trial for trial in all_trials]):
            break
        time.sleep(wait)
        i += 1
    if i == max_retries:
        raise TimeoutError("check_metrics_written() timed out")


def get_trials(optimize_mode):
    """    Obtain information about the trials of the current experiment via the REST endpoint

    Args:
        optimize_mode (str): One of 'minimize', 'maximize'. Determines how to obtain the best default metric.

    Returns:
         list: Trials info, list of (metrics, log path)
         dict: Metrics for the best choice of hyperparameters
         dict: Best hyperparameters
         str: Log path for the best trial
    """

    if optimize_mode not in ['minimize', 'maximize']:
        raise ValueError("optimize_mode should equal either 'minimize' or 'maximize'")
    all_trials = requests.get(NNI_TRIAL_JOBS_URL).json()
    trials = [(eval(trial['finalMetricData'][0]['data']), trial['logPath'].split(':', 1)[-1]) for trial in all_trials]
    sorted_trials = sorted(trials, key=lambda x: x[0]['default'], reverse=(optimize_mode == 'maximize'))
    best_trial_path = sorted_trials[0][1]
    # Read the metrics from the trial directory in order to get the name of the default metric
    with open(os.path.join(best_trial_path, "metrics.json"), "r") as fp:
        best_metrics = json.load(fp)
    with open(os.path.join(best_trial_path, "parameter.cfg"), "r") as fp:
        best_params = json.load(fp)
    return trials, best_metrics, best_params, best_trial_path
