#      highway data preparation 
from tqdm import tqdm
import pandas as pd
import numpy as np


def highway_mileage(section_info, etag_5n_loc, RoadID, RoadDirection):
    '''
    建立當前需要使用的國道里程與地點資訊

    input 
    -section_info: dataframe
    -etag_5n_loc: dataframe
    -RoadID: str, '000050'
    -RoadDirection: str, 'N'

    output
    -highway_mileage_info: dataframe
    '''
    # 交流道類型里程資訊
    query_string = f'RoadID == "{RoadID}" & RoadDirection == "{RoadDirection}"'
    sub_section_info = section_info.query(query_string).copy()
    roadsection_start = sub_section_info[['RoadSection_Start',  'SectionMile_StartKM']].rename(columns={'RoadSection_Start': 'LocationName', 
                                                                                                        'SectionMile_StartKM': 'LocationMile'}).copy()
    roadsection_end = sub_section_info[['RoadSection_End',  'SectionMile_EndKM']].rename(columns={'RoadSection_End': 'LocationName', 
                                                                                                  'SectionMile_EndKM': 'LocationMile'}).copy()
    roadsection_ = pd.concat([roadsection_start, roadsection_end])
    roadsection_['type'] = 'interchange'

    # gantry里程資訊
    sub_gantry_info = etag_5n_loc.query(query_string).copy()
    gantry_info = sub_gantry_info[['ETagGantryID', 'LocationMile']].rename(columns={'ETagGantryID':'LocationName'}).copy()
    gantry_info['type'] = 'etag_gantry'

    # concat 2 source info, deduplicates
    highway_mileage_info = pd.concat([roadsection_, gantry_info]).drop_duplicates()
    highway_mileage_info['RoadID'] = RoadID
    highway_mileage_info['RoadDirection'] = RoadDirection

    # mileage transform
    highway_mileage_info['LocationMile'] = highway_mileage_info['LocationMile'].apply(lambda x: int(x.split('+')[0].replace('K',''))*1000 + int(x.split('+')[1]))

    # exception case
    special_case = {'05FR143N': 41200}
    for LocationName in special_case.keys():
       if LocationName in list(highway_mileage_info['LocationName']):
            highway_mileage_info.loc[(highway_mileage_info['LocationName'] == LocationName), 'LocationMile'] = special_case[LocationName]
            
    # order
    highway_mileage_info.sort_values(by='LocationMile', inplace=True)

    return highway_mileage_info
    
def traveltime_aggregation(hw5_m04a_df):
    # Traffic=0時代表對應車種沒有資料，TravelTime就會=0，這邊代表他並不是真的TravelTime超快
    # 所以我可以做出計算weighted_average_travel_time(watt)，一定程度可以縮減資料的筆數
    def weighted_average(dataframe, value, weight):
        val = dataframe[value]
        wt = dataframe[weight]
    
        # 針對weight pass進來都沒有東西的話，要做額外處理
        if wt.sum() == 0:
            ans = 0
        else:
            ans = (val * wt).sum() / wt.sum()
        return ans

    # aggregation
    hw5_m04a_agg_df = hw5_m04a_df.groupby(['TimeStamp', 'GantryFrom', 'GantryTo'])\
                                 .apply(lambda x: pd.Series({'WeightedAvgTravelTime': weighted_average(x, 'TravelTime', 'Traffic'),
                                                             'TotalTraffic': sum(x['Traffic'])
                                                            }))\
                                 .reset_index()
    # columns modification
    hw5_m04a_agg_df['gf_gt'] = hw5_m04a_agg_df['GantryFrom']+'-'+hw5_m04a_agg_df['GantryTo']
    return hw5_m04a_agg_df

def get_gantry_pair_mileage(milelocation_info_df, gantry_start, gantry_end):
    '''
    取得gantry pair的里程端點位置
    gantry_start = '05F0528N'
    gantry_end = '05F0438N'
    '''
    gantry_start_mile = milelocation_info_df.loc[(milelocation_info_df['LocationName']==gantry_start), 'LocationMile'].values[0]
    gantry_end_mile = milelocation_info_df.loc[(milelocation_info_df['LocationName']==gantry_end), 'LocationMile'].values[0]
    return gantry_start_mile, gantry_end_mile

def get_downstream_gantrypair(hw5_m04a_agg_df, gantryID):
    '''
    input gantryID to get next ID pair
    return pair count, dfs
    '''
    # 這樣就可以抓到下游一段了
    query_string = f'GantryFrom == "{gantryID}"'
    temp_df = hw5_m04a_agg_df.query(query_string)#['GantryTo'].unique()
    # check multiple downstream
    gantry_pair_count = temp_df.gf_gt.nunique()
    gantry_pair_df_list = []
    for pair in list(temp_df.gf_gt.unique()):
        query_string = f'gf_gt == "{pair}"'
        gantry_pair_df_list.append(hw5_m04a_agg_df.query(query_string))
        
    return gantry_pair_count, gantry_pair_df_list

def merge_gantrypair_with_ds(target_df, downstream_gantry_pair_df):
    '''
    merge current gantry pair travel time with downstream data
    '''
    target_gantry_pair_df = target_df.copy()
    # 處理下游gantry資料，進行shift
    temp_df = downstream_gantry_pair_df.copy()

    shift_num = 5
    for i in range(shift_num):
        col_name = f'ds_prev_{i+1}_WATT'
        temp_df[col_name] = temp_df['WeightedAvgTravelTime'].shift(i+1) # 往後shift一組時間，後續須注意資料可能會漏掉一部份ds，需要給空
    temp_df.rename(columns={'gf_gt': 'ds_gf_gt'
                            },
                   inplace=True)
    temp_df.drop(columns={'GantryFrom', 'GantryTo', 'WeightedAvgTravelTime'}, inplace=True)
    current_df = target_gantry_pair_df.merge(temp_df, on='TimeStamp', how='left')

    return current_df

def add_calendar_event(target_df, calendar_event):
    '''
    current gantry pair data add on calendar holiday info
    '''
    target_gantry_pair_df = target_df.copy()
    weekday_dict = {0:1,#'Monday',
                    1:2,#'Tuseday',
                    2:3,#'Wednesday',
                    3:4,#'Thursday',
                    4:5,#'Friday',
                    5:6,#'Saturday',
                    6:7#'Sunday'
                   }
    target_gantry_pair_df['temp_date'] = target_gantry_pair_df['TimeStamp'].dt.date
    #target_gantry_pair_df.TimeStamp.dt.date
    # 使用apply和pd.date_range生成日期范围列 for calendar_event 擴增使用
    calendar_event['event_date'] = calendar_event.apply(lambda row: pd.date_range(start=row['start_date'],
                                                                                  end=row['end_date']), 
                                                        axis=1)
    # 使用explode展开日期范围列
    calendar_event_expand = calendar_event.explode('event_date')
    calendar_event_expand['event_date'] = calendar_event_expand['event_date'].dt.date
    target_gantry_pair_df = target_gantry_pair_df.merge(calendar_event_expand, 
                                                        left_on='temp_date',
                                                        right_on='event_date',
                                                        how='left')
    # add day of week
    target_gantry_pair_df['dayofweek'] = target_gantry_pair_df['TimeStamp'].dt.weekday.apply(lambda x: weekday_dict[x])


    
    # drop meta-data columns
    target_gantry_pair_df.drop(columns={'temp_date', 'event_date', 'start_date', 'end_date'}, inplace=True)

    
    target_gantry_pair_df.fillna({'continuous':'F', 
                                  'event_length':0,
                                 }, inplace=True)

    # convert boolean to numeric
    target_gantry_pair_df['continuous'] = target_gantry_pair_df['continuous'].replace({'T': 1, 'F': 0})
    # rename and onehot
    target_gantry_pair_df.rename(columns={'event_name':'holiday_name',
                                           'continuous':'holiday_continue',
                                           'event_length':'holiday_length'},
                                            inplace=True)
    target_gantry_pair_df['event_name'] = target_gantry_pair_df['holiday_name'] 
    target_gantry_pair_df = pd.get_dummies(target_gantry_pair_df, columns=['holiday_name'], dtype='int')
    target_gantry_pair_df.rename(columns={'event_name':'holiday_name'},
                                          inplace=True)
    return target_gantry_pair_df

def add_congestion_condition(target_df, congestion_table, milelocation_info_df):
    '''
    current gantry pair data add on congestion info
    '''
    df = target_df.copy()
    
    # congestion table 地點里程轉換
    transform_dict = {'南港系統': '南港系統交流道',
                  '坪林': '坪林交控交流道', 
                  '頭城': '頭城交流道',
                  '宜蘭': '宜蘭交流道',
                  '羅東': '羅東交流道'}
    weekday_dict = {0:'weekday',
                    1:'weekday',
                    2:'weekday',
                    3:'weekday',
                    4:'weekday',
                    5:'Saturday',
                    6:'Sunday'}
    
    congestion_table['LinkStart_rep'] = congestion_table['LinkStart'].apply(lambda x: transform_dict[x])
    congestion_table['LinkEnd_rep'] = congestion_table['LinkEnd'].apply(lambda x: transform_dict[x])
    congestion_table = congestion_table.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                                              left_on = 'LinkStart_rep',
                                              right_on = 'LocationName',
                                              how = 'left').rename(columns={'LocationMile': 'LinkStart_mile'})
    congestion_table.drop(columns={'LocationName'}, inplace=True)
    congestion_table = congestion_table.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                                              left_on = 'LinkEnd_rep',
                                              right_on = 'LocationName',
                                              how = 'left').rename(columns={'LocationMile': 'LinkEnd_mile'})
    congestion_table.drop(columns={'LocationName'}, inplace=True)
    
    # target df year-month
    df['temp_yearmonth'] = df['TimeStamp'].dt.strftime('%Y%m').astype('int')
    df['temp_hourminute'] = df['TimeStamp'].dt.hour * 100 + df['TimeStamp'].dt.minute
    df['temp_dayofweek'] = df['TimeStamp'].dt.weekday.apply(lambda x: weekday_dict[x])
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryFrom',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gf_mile'})
    df.drop(columns={'LocationName'}, inplace=True)
    
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryTo',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gt_mile'})
    df.drop(columns={'LocationName'}, inplace=True)

    # set direction
    direction = 'N'
    # 不同方向要分開寫，因為里程大小判斷會顛倒
    congest_index_list = []
    for idx, row in congestion_table[congestion_table.direction == 'N'].iterrows():
        test_df = df[(df.gf_mile >= row['LinkEnd_mile']) & (row['LinkStart_mile'] >= df.gt_mile)\
        & (df.temp_yearmonth >= row['StartYearMonth']) & (df.temp_yearmonth <= row['EndYearMonth'])\
        & (df.temp_dayofweek == row['dayofweek'])\
        & (df.temp_hourminute >= row['CongestStart']) & (df.temp_hourminute <= row['CongestEnd'])].copy()
    
        if test_df.shape[0] != 0:
            # print(row)
            # display(test_df)
            congest_index_list.extend(test_df.index)
            # print(test_df)
        if len(congest_index_list) != len(set(congest_index_list)):
            print('locate same df.index before')
        #     break
    
    # inspection area
    duplicates = {item: congest_index_list.count(item) for item in set(congest_index_list) if congest_index_list.count(item) > 1}
    
    # congest_index_list
    # create new columns and assign congestion situation othe new add columns
    df['congestion_syndrome'] = 0
    df.loc[df.index.isin(congest_index_list), 'congestion_syndrome'] = 1
    # remove temp columns
    df.drop(columns={'temp_yearmonth', 'temp_hourminute', 'temp_dayofweek', 'gf_mile', 'gt_mile'}, inplace=True)

    return df

def add_road_build_event(target_df, road_build_event, milelocation_info_df):
    '''
    add road build event to current pair data
    '''
    df = target_df.copy()

    # congestion table 地點里程轉換
    transform_dict = {'南港系統': '南港系統交流道',
                  '坪林': '坪林交控交流道', 
                  '頭城': '頭城交流道',
                  '宜蘭': '宜蘭交流道',
                  '羅東': '羅東交流道'}
    weekday_dict = {0:'weekday',
                    1:'weekday',
                    2:'weekday',
                    3:'weekday',
                    4:'weekday',
                    5:'Saturday',
                    6:'Sunday'}

    # load and lock road_build_event_df
    # 鎖定國五、北向
    road_build_event = road_build_event.query('incStepFreewayId==10050 & incStepDirection==2')

    # target df year-month
    df['temp_yearmonth'] = df['TimeStamp'].dt.strftime('%Y%m').astype('int')
    df['temp_hourminute'] = df['TimeStamp'].dt.hour * 100 + df['TimeStamp'].dt.minute
    df['weekofday'] = df['TimeStamp'].dt.weekday.apply(lambda x: weekday_dict[x])
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryFrom',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gf_mile'})
    df.drop(columns={'LocationName'}, inplace=True)
    
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryTo',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gt_mile'})
    df.drop(columns={'LocationName'}, inplace=True)


    # insert value
    road_build_index_list = []
    road_build_dict = {}
    for idx, row in tqdm(road_build_event.iterrows(), total=road_build_event.shape[0]):
        temp_df = df[(df.TimeStamp>=row['incStepTime']) & (df.TimeStamp<=row['incStepEndTime'])\
        & (df.gf_mile >= row['incStepEndMileage']) & (row['incStepStartMileage'] >= df.gt_mile)]
        
        if temp_df.shape[0] != 0:
            road_build_index_list.extend(temp_df.index)

            # create extra feature for road build event
            # further information pls review the original data description
            block_condition = row['incStepBlockagePattern']
            total_block_count = block_condition[0:14].count('1')
            road_block_count = block_condition[1:10].count('1')
            road_build = 1
            road_build_dict[row['incStepIncidentId']] = {'df_index': list(temp_df.index),
                                                         'total_block_count': total_block_count,
                                                         'road_block_count': road_block_count,
                                                         'road_build': road_build
                                                        }

        if len(road_build_index_list) != len(set(road_build_index_list)):
            pass
            # 是有可能重複的，變成需要額外多加一些標記進去
            # print('locate same df.index before')  
            # display(temp_df)
            # print(row)
            # return road_build_index_list
            # break
    print('Complete checking & extract road_build_event')
    # inspection area
    duplicates = {item: road_build_index_list.count(item) for item in set(road_build_index_list) if road_build_index_list.count(item) > 1}
    
    # create new columns and assign congestion situation othe new add columns
    df['road_build'] = 0
    df['total_block_count'] = 0
    df['road_block_count'] = 0
    # df.loc[df.index.isin(road_build_index_list), 'road_build'] = 1
    for ikey in tqdm(road_build_dict.keys()):
        target_index = road_build_dict[ikey]['df_index']
        total_block_count = road_build_dict[ikey]['total_block_count']
        road_block_count = road_build_dict[ikey]['road_block_count']
        road_build = road_build_dict[ikey]['road_build']
        df.loc[df.index.isin(target_index), 'total_block_count'] = total_block_count
        df.loc[df.index.isin(target_index), 'road_block_count'] = road_block_count
        df.loc[df.index.isin(target_index), 'road_build'] = road_build
    print('Complete road_build_event insertion to current df')
    print('will return 2 object: road_build_event, df')

    # remove temp columns
    df.drop(columns=['temp_yearmonth', 'temp_hourminute', 'gf_mile', 'gt_mile', 'weekofday'], inplace=True)
    return road_build_event, df

def add_traffic_event(target_df, traffic_accident_data, milelocation_info_df):
    '''
    Add traffic event to the target gantry pair df, will return located traffic accident data
    and the annotated gantry pair df
    '''
    df = target_df.copy()
    
    # 鎖定
    traffic_accident_data = traffic_accident_data.query('國道名稱=="國道5號" & 方向=="北"').copy()
    keep_cols = ['年', '月', '日', '時', '分', '國道名稱', '方向', '里程', '事件發生', '事件排除', 
             '處理分鐘', '事故類型', '死亡', '受傷', 
             '內路肩', '內車道', '中內車道', '中車道', '中外車道', '外車道', '外路肩', '匝道', 
             '簡訊內容', 
             '翻覆事故註記', '施工事故註記', '危險物品車輛註記', '車輛起火註記', '冒煙車事故註記', '主線中斷註記', 
             '肇事車輛', '車輛1', '車輛2', '車輛3', '車輛4', '車輛5', '車輛6',
                 '車輛7', '車輛8', '車輛9', '車輛10', '車輛11', '車輛12']
    traffic_accident_data = traffic_accident_data[keep_cols].copy()
    traffic_accident_data['里程'] = traffic_accident_data['里程']*1000 # 因為是xk單位
    # print(traffic_accident_data.keys())
    traffic_accident_data['start_datetime'] = pd.to_datetime(traffic_accident_data[['年', '月', '日']].astype(str).agg('-'.join, axis=1) 
                                             + ' ' 
                                             + traffic_accident_data[['時', '分']].astype(str).agg(':'.join, axis=1)
                                            )
    traffic_accident_data['end_datetime'] = traffic_accident_data['start_datetime'] + pd.to_timedelta(traffic_accident_data['處理分鐘'], unit='m')
    # 這邊要整合並擷取出我要看的事故發生車輛數
    # 擴大到其他國道、方向時需要檢驗原始通報的資料中存在哪些類型，有的地方寫得不是很標準
    car_columns_set = ['車輛1', '車輛2', '車輛3', '車輛4', 
                   '車輛5', '車輛6', '車輛7', '車輛8', 
                   '車輛9', '車輛10', '車輛11', '車輛12']
    traffic_accident_data['total_car_string'] = traffic_accident_data[car_columns_set].apply(lambda x: ','.join(x.dropna()), axis=1)
    traffic_accident_data['小貨車'] = traffic_accident_data['total_car_string'].apply(lambda x: x.count('小貨車'))
    traffic_accident_data['小客車'] = traffic_accident_data['total_car_string'].apply(lambda x: x.count('小客車'))
    traffic_accident_data['大客車'] = traffic_accident_data['total_car_string'].apply(lambda x: x.count('大客車'))
    traffic_accident_data['大貨車'] = traffic_accident_data['total_car_string'].apply(lambda x: x.count('大貨車'))
    traffic_accident_data.drop(columns=car_columns_set, inplace=True)
    traffic_accident_data.drop(columns='簡訊內容', inplace=True)

    # target df mile location
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryFrom',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gf_mile'})
    df.drop(columns={'LocationName'}, inplace=True)
    
    df = df.merge(milelocation_info_df[['LocationName', 'LocationMile']], 
                  left_on='GantryTo',
                  right_on='LocationName',
                  how='left').rename(columns={'LocationMile':'gt_mile'})
    df.drop(columns={'LocationName'}, inplace=True)
    
    # insert value
    TA_list = list()
    info = ['里程', '事件發生', '事件排除', '處理分鐘',
       '事故類型', '死亡', '受傷', '內路肩', '內車道', '中內車道', '中車道', '中外車道', '外車道', '外路肩',
       '匝道', '翻覆事故註記', '施工事故註記', '危險物品車輛註記', '車輛起火註記', '冒煙車事故註記', '主線中斷註記',
       '肇事車輛', 'total_car_string', '小貨車','小客車', '大客車', '大貨車']
    for idx, row in tqdm(traffic_accident_data.iterrows(), total=traffic_accident_data.shape[0]):
        TA_dict = dict() # initialize
        temp_df = df[(df.TimeStamp>=row['start_datetime']) & (df.TimeStamp<=row['end_datetime'])\
        & (df.gf_mile >= row['里程']) & (row['里程'] >= df.gt_mile)]
        
        if temp_df.shape[0] != 0:
            for key in info:
                TA_dict[key] = row[key]
            TA_dict['df_index'] = list(temp_df.index)
            TA_list.append(TA_dict)
    print(f'Complete checking traffic accident data, total event count = {len(TA_list)}')

    df[info] = np.nan
    # for key in info:
    #     df[key] = None
    for item in tqdm(TA_list):
        target_item = list(item.copy().keys())
        target_item.pop(target_item.index('df_index'))
        for key in target_item:
            df.loc[df.index.isin(item['df_index']), key] = item[key]
    print('Complete traffic accident data insertion')
    print('will return 2 object: target_traffic_accident_data, df')

    # drop
    drop_cols = ['gf_mile', 'gt_mile', 'total_car_string']
    df.drop(columns=drop_cols, inplace=True)
    # rename
    df.rename(columns={'里程':'accident_mileage', 
                       '事件發生':'event_occurrence',
                       '事件排除':'event_exclusion', 
                       '處理分鐘':'handling_minutes', 
                       '事故類型':'accident_type',
                       '死亡':'death_count', 
                       '受傷':'injuries_count', 
                       '內路肩':'inner_shoulder_flag', 
                       '內車道':'inner_lane_flag', 
                       '中內車道':'middle_inner_lane_flag', 
                       '中車道':'middle_lane_flag', 
                       '中外車道':'middle_outer_lane_flag', 
                       '外車道':'outer_lane_flag', 
                       '外路肩':'outer_shoulder_flag', 
                       '匝道':'ramp_flag',
                       '翻覆事故註記':'overturn_accident_flag', 
                       '施工事故註記':'construction_accident_flag',
                       '危險物品車輛註記':'hazardous_material_vehicle_flag', 
                       '車輛起火註記':'on_fire_vehicle_flag', 
                       '冒煙車事故註記':'smoking_vehicle_flag', 
                       '主線中斷註記':'mainlane_disruption_flag', 
                       '肇事車輛':'accident_vehicle_count',
                       '小貨車':'light_truck_count', 
                       '小客車':'passenger_car_count', 
                       '大客車':'bus_count', 
                       '大貨車':'heavy_truck_count'
                      }, inplace=True)


    altermeaning_fill_9 = ['accident_mileage', 'event_occurrence', 'event_exclusion'] 
    processtime_fill_0 = ['handling_minutes']
    
    flag_fill_0 = ['inner_shoulder_flag', 'inner_lane_flag', 'middle_inner_lane_flag', 
                   'middle_lane_flag', 'middle_outer_lane_flag', 'outer_lane_flag',
                   'outer_shoulder_flag', 'ramp_flag', 'overturn_accident_flag', 'construction_accident_flag',
                   'hazardous_material_vehicle_flag', 'on_fire_vehicle_flag',
                   'smoking_vehicle_flag', 'mainlane_disruption_flag']
    count_fill_0 = ['death_count', 'injuries_count', 'accident_vehicle_count', 'light_truck_count', 'passenger_car_count',
                    'bus_count', 'heavy_truck_count']
    
    df['accident_type'] = df['accident_type'].fillna('A0')
    acc_type_transform = {'A0':0,
                          'A3':1,
                          'A2':2,
                          'A1':3
                         }
    df['accident_type'] = df['accident_type'].apply(lambda x: acc_type_transform[x])
    df[altermeaning_fill_9] = df[altermeaning_fill_9].fillna(99999999)
    df[processtime_fill_0] = df[processtime_fill_0].fillna(0)
    df[flag_fill_0] = df[flag_fill_0].fillna(0)
    df[count_fill_0] = df[count_fill_0].fillna(0)
    return traffic_accident_data, df
    
def add_ds_5prev_traveltime(target_df):
    '''注意，使用上因為先天設計不佳，在多個變數組合時，這個函數要優先使用，以後有機會再改'''
    # initialization
    hw5_15watt = target_df.copy()
    final_df = pd.DataFrame()
    
    # 利用 gantry to 的端點來找下游
    for gantry_pair in hw5_15watt['gf_gt'].unique():
        target_gt = gantry_pair.split('-')[1]
        # 自己與自己匹配 但有延遲
        gantry_pair_count, gantry_pair_df_list = get_downstream_gantrypair(hw5_15watt, target_gt)
    
        try:
            for i, df in enumerate(gantry_pair_df_list):
                gantry_pair_df_list[i] = df.drop(columns='TotalTraffic').copy()
        except:
            None
            
        if gantry_pair_count==0:
            # 沒有下游的處理手法 （目前可能先跳過，因為聚焦在國五上） #不行還是要給回去，否則會漏掉資料
            # print(f'gantry_id {target_gt} has no downstream gantry !')
            result_df = hw5_15watt[hw5_15watt.gf_gt==gantry_pair].copy()
        elif gantry_pair_count==2:
            # 多下游的處理手法...... 目前用加起來除以二
            # print('2 pair gantry')
            current_df = hw5_15watt[hw5_15watt['gf_gt']==gantry_pair].copy()
            result_df = merge_gantrypair_with_ds(current_df, gantry_pair_df_list[0])
            # current_df = hw5_15watt[hw5_15watt['gf_gt']==gantry_pair].copy()
            result_df2 = merge_gantrypair_with_ds(current_df, gantry_pair_df_list[1])
            result_df.drop(columns='ds_gf_gt',inplace=True)
    
            ori_col_list = []
            tar_col_list = []
            # 因為新增多個序列輔助參考
            for i in range(5):
                ori_col = f'ds_prev_{i+1}_WATT'
                tar_col = f'ds_prev_{i+1}_WATT_2'
                result_df2.rename(columns={ori_col: tar_col},inplace=True)
                tar_col_list.append(tar_col)
                ori_col_list.append(ori_col)
            # 短暫拼湊
            result_df = pd.concat([result_df, result_df2[tar_col_list]], axis=1)
            
            # 相加除二
            for col in ori_col_list:
                result_df[col] = (result_df[col] + result_df[col+'_2'])/2
            
            # 移除輔助欄位
            for col in tar_col_list:
                result_df.drop(columns=col, inplace=True)
        else:
            # print('1 pair gantry')
            current_df = hw5_15watt[hw5_15watt['gf_gt']==gantry_pair].copy()
            result_df = merge_gantrypair_with_ds(current_df, gantry_pair_df_list[0])
            result_df.drop(columns=['ds_gf_gt'], inplace=True)

        final_df = pd.concat([final_df, result_df])
        final_df = final_df.fillna(0)

    return final_df
    
class hw_df_resource():
    def __init__(self, data_paths):
        self.data_paths = data_paths
        self.etag_5n_loc = None
        self.section_info = None
        self.hw5_m04a_df = None
        self.congestion_table = None
        self.calendar_event = None
        self.road_build_event = None
        self.traffic_accident_data = None
                                       
        # generated info
        self.milelocation_info_df = None
        self.hw5_m04a_agg_df = None
        
    def load_raw_environment_info(self):
        # enviroment and gantry info
        self.etag_5n_loc = pd.read_csv(self.data_paths['etag_5n_loc'], dtype={'RoadID': 'str'})
        self.section_info = pd.read_csv(self.data_paths['section_info'])
        print('Complete loading environment and gantry info')

    def load_raw_etag_data(self):
        self.hw5_m04a_df = pd.read_csv(self.data_paths['hw5_m04a_df'])
        self.hw5_m04a_df['TimeStamp'] = pd.to_datetime(self.hw5_m04a_df['TimeStamp'])
        print('Complete loading raw etag data')

    def load_raw_event_info(self):
        self.congestion_table = pd.read_csv(self.data_paths['congestion_table'])
        self.calendar_event = pd.read_csv(self.data_paths['calendar_event'])
        # road_build_event, with little etl
        self.road_build_event = pd.read_excel(self.data_paths['road_build_event'])
        self.road_build_event.drop(index=0,inplace=True)
        self.road_build_event['incStepTime'] = pd.to_datetime(self.road_build_event['incStepTime'])
        self.road_build_event['incStepEndTime'] = pd.to_datetime(self.road_build_event['incStepEndTime'])
        # traffic_accident_data
        self.traffic_accident_data = pd.read_excel(self.data_paths['traffic_accident_data'], dtype={'年':'int', 
                                                                                                    '月':'int',
                                                                                                    '日':'int',
                                                                                                    '時':'int',
                                                                                                    '分':'int', 
                                                                                                    '國道名稱':'string', 
                                                                                                    '方向':'string',
                                                                                                    '里程':'float',
                                                                                                    '事件發生':'string',
                                                                                                    '交控中心接獲通報':'string',
                                                                                                    'CCTV監看現場':'string',
                                                                                                    'CMS發布資訊':'string',
                                                                                                    '交控中心通報工務段':'string',
                                                                                                    '事故處理小組出發':'string', 
                                                                                                    '事故處理小組抵達':'string',
                                                                                                    '事故處理小組完成':'string',
                                                                                                    '事件排除':'string', 
                                                                                                    '處理分鐘':'int',
                                                                                                    '事故類型':'string',
                                                                                                    '簡訊內容':'string',
                                                                                                    '車輛1':'string', 
                                                                                                    '車輛2':'string', 
                                                                                                    '車輛3':'string', 
                                                                                                    '車輛4':'string', 
                                                                                                    '車輛5':'string',
                                                                                                    '車輛6':'string',
                                                                                                    '車輛7':'string',
                                                                                                    '車輛8':'string',
                                                                                                    '車輛9':'string',
                                                                                                    '車輛10':'string',
                                                                                                    '車輛11':'string',
                                                                                                    '車輛12':'string',
                                                                                                    '分局':'int'})
        print('Complete loading raw event info')

    def generate_mile_location_info(self):
        self.milelocation_info_df = highway_mileage(self.section_info, self.etag_5n_loc, '000050', 'N')
        print('Complete generating mile location info')
