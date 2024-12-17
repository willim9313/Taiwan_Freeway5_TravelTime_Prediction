import pandas as pd
import numpy as np
import os


def p_df_formatter(target_df):
    df = target_df.copy()
    df.rename(columns={'gf_gt': 'unique_id', 
                       'TimeStamp': 'ds',\
                       'WeightedAvgTravelTime': 'y'}, inplace=True)
    df['ds'] = df['ds'].astype('datetime64[ns]')
    df.drop(columns={'GantryFrom', 'GantryTo'}, inplace=True)
    # df.drop(columns={'GantryFrom', 'GantryTo', 'TotalTraffic'}, inplace=True)

    return df