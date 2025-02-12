from __future__ import division
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.cluster import KMeans
import pyspark


def ohe_columns(series, name):
    ohe = OneHotEncoder(categories='auto')
    ohe.fit(series)
    cols = ohe.get_feature_names(name)
    ohe = ohe.transform(series)
    final_df = pd.DataFrame(ohe.toarray(), columns=cols)
    return final_df

def add_clusters_to_users(n_clusters=8):
    """
    parameters:number of clusters
    
    return: user dataframe
    """
    
    # Get the user data
    user_df = pd.read_csv('data/users.dat', sep='::', header=None
                          , names=['id', 'gender', 'age', 'occupation', 'zip'])
    
    # OHE for clustering
    my_cols = ['gender', 'age', 'occupation']

    ohe_multi = OneHotEncoder(categories='auto')
    ohe_multi.fit(user_df[my_cols])
    ohe_mat = ohe_multi.transform(user_df[my_cols])

    # Then KMeans cluster
    k_clusters = KMeans(n_clusters=8, random_state=42)
    k_clusters.fit(ohe_mat)

    preds = k_clusters.predict(ohe_mat)
    
    # Add clusters to user df
    user_df['cluster'] = preds
    
    return user_df


def add_cluster_to_ratings(user_df):
    """
    given user_df with clusters, add clusters to ratings data
    parameters
    ---------
    user_df: df with user data

    returns
    -------
    ratings_df: ratings_df with cluster column
    """
    # Read in ratings file
    #Get ratings file - create Spark instance for loading JSON
    spark = pyspark.sql.SparkSession.builder.getOrCreate()
    sc = spark.sparkContext
    ratings_df = spark.read.json('data/ratings.json').toPandas()
    
    # Set up clusters
    cluster_dict = {}
    for k, v in zip(user_df['id'].tolist(), user_df['cluster'].tolist()):
        cluster_dict[k] = v
        
    # Add cluster to ratings
    ratings_df['cluster'] = ratings_df['user_id'].apply(lambda x: cluster_dict[x])
    
    return ratings_df



def get_cold_start_rating(user_id, movie_id):
    """
    Given user_id and movie_id, return a predicted rating
    
    parameters
    ----------
    user_id, movie_id
    
    returns
    -------
    movie rating (float)
    If current user, current movie = average rating of movie by cluster
    If current user, NOT current movie = average rating for cluster
    If NOT current user, and current movie = average for the movie
    If NOT current user, and NOT current movie = average for all ratings
    """
        
    if user_id in u_info['id'].tolist():
        if movie_id in ratings_df['movie_id'].tolist():
            cluster = u_info.loc[u_info['id'] == user_id]['cluster'].tolist()[0]
            cluster_df = ratings_df.loc[(ratings_df['cluster'] == cluster)]['rating']
            cluster_avg = cluster_df.mean()
        else:
            cluster = u_info.loc[u_info['id'] == user_id]['cluster'].tolist()[0]
            cluster_rating = ratings_df.loc[ratings_df['cluster'] == cluster]['rating'].tolist()
            if len(cluster_rating) > 1:
                cluster_avg = sum(cluster_rating)/len(cluster_rating)
            else:
                cluster_avg = cluster_rating[0]
                
        return cluster_avg 

    else:
        if movie_id in ratings_df['movie_id'].tolist():

            movie_rating = ratings_df.loc[ratings_df['movie_id'] == movie_id]['rating'].tolist()

            if len(movie_rating) > 1:
                movie_avg = sum(movie_rating)/len(movie_rating)
            else:
                movie_avg = movie_rating[0]

            return movie_avg

        else:

            return ratings_df['rating'].mean()