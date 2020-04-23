import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import lightfm
from lightfm.evaluation import precision_at_k, recall_at_k, auc_score

def model_perf_plots(df):
    """
    Function to plot model performance metrics
    Args:
        df (Pandas dataframe): Dataframe in tidy format, with ['epoch','level','value'] columns
    Returns:
        matplotlib axes
    """
    g = sns.FacetGrid(df, col="metric", hue='stage', col_wrap=3, sharey=False)
    g = g.map(sns.scatterplot, "epoch", "value").add_legend()    

def compare_metric(df_list, metric='AUC', stage='test'):
    """
    Function to combine and prepare list of dataframes into tidy format
    Args:
        df_list (list): List of dataframes 
        metrics (str): name of metric to be extracted, optional
        stage (str): name of model fitting stage to be extracted, optional
    Returns:
        Pandas dataframe
    """
    colnames = ['model'+str(x) for x in list(range(1,len(df_list)+1))]
    models = [df[(df['stage']==stage) & (df['metric']==metric)]['value'].reset_index(
        drop=True).values for df in df_list]

    output = pd.DataFrame(zip(*models), 
                          columns=colnames).stack().reset_index()
    output.columns = ['epoch','data','value']
    return output   

    
def track_model_metrics(model, train_interactions, test_interactions, k=10,
                         no_epochs=100, no_threads=8, **kwargs):
    """
    Function to record model's performance at each epoch, formats the performance into tidy format,
    plots the performance and outputs the performance data
    Args:
        model (LightFM instance): fitted LightFM model
        train_interactions (scipy sparse COO matrix): train interactions set
        test_interactions (scipy sparse COO matrix): test interaction set
        k (int): number of recommendations, optional
        no_epochs (int): no of epochs to run, optional
        no_threads (int): no of parallel threads to use, optional 
        **kwargs: other keyword arguments to be passed down
    Returns:
        Pandas dataframe: performance traces of the fitted model
        matplotlib axes: side effect of the method
    """
    # initialising temp data storage
    model_auc_train = [0]*no_epochs
    model_auc_test = [0]*no_epochs

    model_prec_train = [0]*no_epochs
    model_prec_test = [0]*no_epochs

    model_rec_train = [0]*no_epochs
    model_rec_test = [0]*no_epochs
    
    # fit model and store train/test metrics at each epoch 
    for epoch in range(no_epochs):
    #     print(f'Epoch: {epoch}/{epochs}')
        model.fit_partial(interactions=train_interactions, epochs=1,
                                   num_threads=no_threads, **kwargs)
        model_prec_train[epoch] = precision_at_k(model, train_interactions, k=k, **kwargs).mean()
        model_prec_test[epoch] = precision_at_k(model, test_interactions, k=k, **kwargs).mean()

        model_rec_train[epoch] = recall_at_k(model, train_interactions, k=k, **kwargs).mean()
        model_rec_test[epoch] = recall_at_k(model, test_interactions, k=k, **kwargs).mean()

        model_auc_train[epoch] = auc_score(model, train_interactions, **kwargs).mean()
        model_auc_test[epoch] = auc_score(model, test_interactions, **kwargs).mean()
    
    # collect the performance metrics into a dataframe
    fitting_metrics = pd.DataFrame(zip(model_auc_train, model_auc_test, model_prec_train, 
                                       model_prec_test, model_rec_train, model_rec_test),
                                   columns=['model_auc_train', 'model_auc_test', 'model_prec_train', 
                                            'model_prec_test', 'model_rec_train', 'model_rec_test'])
    # convert into tidy format
    fitting_metrics = fitting_metrics.stack().reset_index()
    fitting_metrics.columns = ['epoch','level','value']
    # exact the labels for each observation
    fitting_metrics['stage'] = fitting_metrics.level.str.split('_').str[-1]
    fitting_metrics['metric'] = fitting_metrics.level.str.split('_').str[1]
    fitting_metrics.drop(['level'], axis = 1, inplace=True)
    # replace the metric keys to improve visualisation
    metric_keys = {'auc':'AUC', 'prec':'Precision', 'rec':'Recall'}
    fitting_metrics.metric.replace(metric_keys, inplace=True)
    # plots the performance data
    model_perf_plots(fitting_metrics)
    return fitting_metrics


def similar_users(user_id, user_features, model, N=10):
    """
    Function to return top N similar users
    based on https://github.com/lyst/lightfm/issues/244#issuecomment-355305681
     Args:
        user_id (int): id of user to be used as reference
        user_features (scipy sparse CSR matrix): user feature matric
        model (LightFM instance): fitted LightFM model 
        N (int): No of top similar users to return
    Returns:
        Pandas dataframe of top N most similar users with score
    """
    _, user_representations = model.get_user_representations(features=user_features)

    # Cosine similarity
    scores = user_representations.dot(user_representations[user_id, :])
    user_norms = np.linalg.norm(user_representations, axis=1)
    user_norms[user_norms == 0] = 1e-10
    scores /= user_norms

    best = np.argpartition(scores, -(N+1))[-(N+1):]
    return pd.DataFrame(sorted(zip(best, scores[best] / user_norms[user_id]), 
                  key=lambda x: -x[1])[1:], columns = ['userID', 'score'])


def similar_items(item_id, item_features, model, N=10):
    """
    Function to return top N similar items
    based on https://github.com/lyst/lightfm/issues/244#issuecomment-355305681
    Args:
        item_id (int): id of item to be used as reference
        item_features (scipy sparse CSR matrix): item feature matric
        model (LightFM instance): fitted LightFM model 
        N (int): No of top similar items to return
    Returns:
        Pandas dataframe of top N most similar items with score
    """
    _, item_representations = model.get_item_representations(features=item_features)
    
    # Cosine similarity
    scores = item_representations.dot(item_representations[item_id, :])
    item_norms = np.linalg.norm(item_representations, axis=1)
    item_norms[item_norms == 0] = 1e-10
    scores /= item_norms

    best = np.argpartition(scores, -(N+1))[-(N+1):]
    return pd.DataFrame(sorted(zip(best, scores[best] / item_norms[item_id]), 
                  key=lambda x: -x[1])[1:], columns = ['itemID', 'score'])    