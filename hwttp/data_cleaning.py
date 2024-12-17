from lxml import etree
import pandas as pd
from tqdm import tqdm
import json
import gzip
import shutil
import os
import tarfile
import sqlite3


def unzip_file(gz_path, xml_path):
    '''
    gz_path file unzip to xml_path using copyfile
    '''
    with gzip.open(gz_path, 'rb') as f_in:
        with open(xml_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

def ensure_directory_exists(path):
    '''
    make sure there is a folder exists, if not create one
    '''
    if not os.path.exists(path):
        os.makedirs(path)


def extract_tar_gz(tar_gz_path, extract_path):
    '''
    Extract a .tar.gz file to a specified directory
    '''
    with tarfile.open(tar_gz_path, 'r:gz') as tar:
        tar.extractall(path=extract_path)

def decompress_procedure_datefolder(date_list: list[str],
                                    input_zip_dir: str,
                                    output_dir: str) -> None:
    '''
    提供vd, etag info 資料解壓縮使用的流程
    因為上述兩種在資料下載時都是依據日期資料夾分拆擺放
    '''
    for date in tqdm(date_list):
        input_dir = f'{input_zip_dir}/{date}'
        output_dir = f'{output_dir}/{date}'
        for file_name in os.listdir(input_dir):
            if file_name.endswith('.gz'):
                gz_file_path = os.path.join(input_dir, file_name)
                xml_file_name = file_name.replace('.gz', '')
                xml_file_path = os.path.join(output_dir, xml_file_name)
                try:
                    ensure_directory_exists(output_dir)
                    unzip_file(gz_file_path, xml_file_path)
                except:
                    print(f"Unzipped {gz_file_path} to {xml_file_path} ran into error!!!")



def decompress_vd_data(date_list: list[str],
                       input_zip_dir: str='../data/raw/VD',
                       output_dir: str='../data/raw/unzip_VD') -> None:
    '''
    依據輸入的日期清單，將原始儲存的VD.xml.gz解壓縮到指定的資料夾下，結構上還是會依據日期再分子資料夾
    '''
    # 這邊先以每天的VD相關資料解壓縮進行處理
    decompress_procedure_datefolder(date_list,
                                    input_zip_dir,
                                    output_dir)

def decompress_etag_info_data(date_list: list[str],
                              input_zip_dir: str='../data/raw/ETag',
                              output_dir: str='../data/raw/unzip_ETag') -> None:
    '''
    依據輸入的日期清單，將原始儲存的.xml.gz解壓縮到指定的資料夾下，結構上還是會依據日期再分子資料夾
    '''
    # 這邊先以每天的VD相關資料解壓縮進行處理
    decompress_procedure_datefolder(date_list,
                                    input_zip_dir,
                                    output_dir)

def decompress_procedure_direct(date_list: list[str],
                                input_zip_dir: str,
                                output_dir: str) -> None:
    '''
    提供etag gantry vol, speed, travel time 資料解壓縮使用的流程
    因為上述3種在資料下載時是沒有分資料夾的
    '''
    for date in tqdm(date_list):
        for file_name in os.listdir(input_zip_dir):
            if file_name.endswith(f'{date}.tar.gz'):
                gz_file_path = os.path.join(input_zip_dir, file_name)
                try:
                    ensure_directory_exists(output_dir)
                    extract_tar_gz(gz_file_path, output_dir)
                except:
                    print(f"Unzipped {gz_file_path} to {output_dir} ran into error!!!")

def decompress_etag_vol_data(date_list: list[str],
                             input_zip_dir: str='../data/raw/ETag_gantry_vol',
                             output_dir: str='../data/raw/unzip_etag_gantry_vol') -> None:
    '''
    依據輸入的日期清單，將原始儲存的M03A_YYYYMMDD.tar解壓縮到指定的資料夾下，壓縮檔中已經包含了日期與小時的分層子資料夾結構
    '''
    decompress_procedure_direct(date_list, 
                                input_zip_dir, 
                                output_dir)
    
def decompress_etag_speed_data(date_list: list[str],
                               input_zip_dir: str='../data/raw/ETag_intergantry_speed',
                               output_dir: str='../data/raw/unzip_etag_intergantry_speed') -> None:
    '''
    依據輸入的日期清單，將原始儲存的M05A_YYYYMMDD.tar解壓縮到指定的資料夾下，壓縮檔中已經包含了日期與小時的分層子資料夾結構
    '''
    decompress_procedure_direct(date_list, 
                                input_zip_dir, 
                                output_dir)


def decompress_etag_intergantry_traveltime_data(date_list: list[str],
                                                input_zip_dir: str='../data/raw/ETag_intergantry_traveltime',
                                                output_dir: str='../data/raw/unzip_etag_intergantry_traveltime') -> None:
    '''
    依據輸入的日期清單，將原始儲存的M04A_YYYYMMDD.tar解壓縮到指定的資料夾下，壓縮檔中已經包含了日期與小時的分層子資料夾結構
    '''
    decompress_procedure_direct(date_list, 
                                input_zip_dir, 
                                output_dir)
 
# 資料庫互動用的工具
class DatabaseManager:
    def __init__(self, db_path: str, table_name: str) -> None:
        """
        Initializes the DatabaseManager with a specified database path and table name.

        Parameters:
        - db_path: Path to the SQLite database file.
        - table_name: The name of the table to manage.
        """
        self.db_path = db_path
        self.table_name = table_name

    def initialize_table(self, columns_in_order: str) -> None:
        """
        Initializes a new table in the SQLite database.

        Parameters:
        - columns_in_order: String representing the columns definition 
                            (e.g., "id INTEGER PRIMARY KEY, name TEXT").
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        
        cur.execute(f'''CREATE TABLE IF NOT EXISTS {self.table_name}({columns_in_order})''')
        con.commit()
        con.close()

    def delete_table_data(self) -> None:
        """
        Deletes all data from the table.
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(f'''DELETE FROM {self.table_name}''')
        con.commit()
        con.close()

    def append_data(self, df: pd.DataFrame) -> None:
        """
        Appends a DataFrame to the table in the SQLite database.

        Parameters
        ----------
        df: A pandas DataFrame containing the data to append.
        """
        con = sqlite3.connect(self.db_path)
        df.to_sql(self.table_name, con, index=False, if_exists='append')
        con.close()

    def update_data(self, 
                    df: pd.DataFrame, 
                    key_columns: list) -> None:
        """
        Updates the table with new data. If a record with matching key_columns exists,
        it updates the row; otherwise, it inserts the row as new data.

        Parameters:
        - df: A pandas DataFrame containing the data to update.
        - key_columns: List of column names that form the unique key for identifying records.
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        for _, row in df.iterrows():
            # Convert unsupported types (e.g., datetime) to string
            row = row.apply(lambda x: str(x) if isinstance(x, pd.Timestamp) else x)
            
            # Build the WHERE clause based on the key columns
            where_clause = ' AND '.join([f"{col} = ?" for col in key_columns])
            key_values = [row[col] for col in key_columns]
            
            # Check if a record exists with the specified key columns
            cur.execute(f"SELECT 1 FROM {self.table_name} WHERE {where_clause}", key_values)
            exists = cur.fetchone()
            
            if exists:
                # If record exists, update the row
                update_clause = ', '.join([f"{col} = ?" for col in df.columns if col not in key_columns])
                update_values = [row[col] for col in df.columns if col not in key_columns]
                cur.execute(f"UPDATE {self.table_name} SET {update_clause} WHERE {where_clause}", update_values + key_values)
            else:
                # If record doesn't exist, insert the row
                placeholders = ', '.join(['?' for _ in df.columns])
                cur.execute(f"INSERT INTO {self.table_name} ({', '.join(df.columns)}) VALUES ({placeholders})", row.values)
        
        con.commit()
        con.close()

   
def strip_ns_prefix(tree):
    for elem in tree.getiterator():
        if not hasattr(elem.tag, 'find'):
            continue
        i = elem.tag.find('}')
        if i >= 0:
            elem.tag = elem.tag[i+1:]

def xml_to_dict(element):
    if len(element) == 0:  # if element is a leaf node
        return element.text
    result = {}
    for child in element:
        child_result = xml_to_dict(child)
        if child.tag not in result:
            result[child.tag] = child_result
        else:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_result)
    return result

def convert_xml_to_dict(xml_file_path):
    # 解析XML文件
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(xml_file_path, parser)
    root = tree.getroot()

    # 移除命名空間
    strip_ns_prefix(tree)
    
    # Convert the XML to a dictionary
    data_dict = {root.tag: xml_to_dict(root)}
    return data_dict


# 這段會因每種檔案不同要改寫
def vd_static_dict_to_df(vd_static_dict):
    # extract shared columns
    shared_cols = ['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'LinkVersion']
    shared_info = {key: vd_static_dict['VDList'][key] for key in shared_cols}
    
    # dict to df, append shared columns
    df = pd.json_normalize(vd_static_dict['VDList']['VDs']['VD'])
    for key in shared_info.keys():
        df[key] = shared_info[key]
    
    df.rename(columns={'DetectionLinks.DetectionLink.LinkID': 'LinkID',
                   'DetectionLinks.DetectionLink.Bearing': 'Bearing',
                   'DetectionLinks.DetectionLink.RoadDirection': 'RoadDirection',
                   'DetectionLinks.DetectionLink.LaneNum': 'Lane',
                   'DetectionLinks.DetectionLink.ActualLaneNum': 'ActualLaneNum', 
                   'RoadSection.Start': 'Start',
                   'RoadSection.End': 'End'
                  }, inplace=True)

    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'])
    df = df[['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'VDID', 'SubAuthorityCode', 
         'BiDirectional', 'LinkID', 'Bearing', 'RoadDirection', 'Lane',
         'ActualLaneNum', 'VDType', 'LocationType', 'DetectionType', 'PositionLon',
         'PositionLat', 'RoadID', 'RoadName', 'RoadClass', 'Start', 
         'End', 'LocationMile']]
    return df

# 這段會因每種檔案不同要改寫
def vd_dynamic_dict_to_df(vd_dynamic_dict):
    # extract shared columns
    shared_cols = ['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'LinkVersion']
    shared_info = {key: vd_dynamic_dict['VDLiveList'][key] for key in shared_cols}
    
    # dict to df, append shared columns

    # 這邊結構很醜，沒有chatgpt幫忙要花很長時間去解
    df = pd.json_normalize(
        vd_dynamic_dict['VDLiveList']['VDLives']['VDLive'],
        record_path=['LinkFlows', 'LinkFlow', 'Lanes', 'Lane', 'Vehicles', 'Vehicle'],
        meta=[
            'VDID', 'Status', 'DataCollectTime',
            ['LinkFlows', 'LinkFlow', 'LinkID'],
            ['LinkFlows', 'LinkFlow', 'Lanes', 'Lane', 'LaneID'],
            ['LinkFlows', 'LinkFlow', 'Lanes', 'Lane', 'LaneType'],
            ['LinkFlows', 'LinkFlow', 'Lanes', 'Lane', 'Speed'],
            ['LinkFlows', 'LinkFlow', 'Lanes', 'Lane', 'Occupancy']
        ],
        meta_prefix='meta_',
        record_prefix='vehicle_'
    )
    
    # Rename columns for better readability
    df.columns = df.columns.str.replace('meta_LinkFlows.LinkFlow.Lanes.Lane.', 'lane_')
    df.columns = df.columns.str.replace('meta_LinkFlows.LinkFlow.', 'link_')
    df.columns = df.columns.str.replace('meta_', '')
    
    df.rename(columns = {'vehicle_VehicleType': 'VehicleType', 
                         'vehicle_Volume': 'Volume', 
                         'vehicle_Speed': 'Speed2',
                         'link_LinkID': 'LinkID', 
                         'lane_LaneID': 'LaneID',
                         'lane_LaneType': 'LaneType', 
                         'lane_Speed': 'Speed', 
                         'lane_Occupancy': 'Occupancy'}, inplace=True)
        
    for key in shared_info.keys():
        df[key] = shared_info[key]

    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'])
    df['DataCollectTime'] = pd.to_datetime(df['DataCollectTime'])
    df = df[['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'VDID', 'LinkID', 
         'LaneID', 'LaneType', 'Speed', 'Occupancy', 'VehicleType',
         'Volume', 'Speed2', 'Status', 'DataCollectTime']]
    return df

# 這段會因每種檔案不同要改寫
def etag_static_dict_to_df(etag_static_dict):
    # Flatten the nested structure
    df = pd.json_normalize(
        etag_static_dict['ETagList']['ETags']['ETag'],
        sep='_'
    )
    
    # Add metadata fields to the DataFrame
    df['UpdateTime'] = etag_static_dict['ETagList']['UpdateTime']
    df['UpdateInterval'] = etag_static_dict['ETagList']['UpdateInterval']
    df['AuthorityCode'] = etag_static_dict['ETagList']['AuthorityCode']
    df['LinkVersion'] = etag_static_dict['ETagList']['LinkVersion']
    
    df.rename(columns={'RoadSection_Start': 'Start',
                       'RoadSection_End': 'End'}, inplace=True)
    
    df = df[['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'LinkVersion',
             'ETagGantryID', 'LinkID', 'LocationType', 'PositionLon', 'PositionLat',
             'RoadID', 'RoadName', 'RoadClass', 'RoadDirection', 'Start', 
             'End', 'LocationMile']]
    return df

# 這段會因每種檔案不同要改寫
def etagpair_dict_to_df(etagpair_dict):
    # Flatten the nested structure
    df = pd.json_normalize(
        etagpair_dict['ETagPairList']['ETagPairs']['ETagPair'],
        sep='_'
    )
    
    # Add metadata fields to the DataFrame
    df['UpdateTime'] = etagpair_dict['ETagPairList']['UpdateTime']
    df['UpdateInterval'] = etagpair_dict['ETagPairList']['UpdateInterval']
    df['AuthorityCode'] = etagpair_dict['ETagPairList']['AuthorityCode']
    df['LinkVersion'] = etagpair_dict['ETagPairList']['LinkVersion']
    
    df = df[['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'ETagPairID', 'StartETagGantryID', 
             'EndETagGantryID', 'Description', 'Distance', 'StartLinkID', 'EndLinkID', 
             'Geometry']]
    return df

# 這段會因每種檔案不同要改寫
def etagpairlive_dict_to_df(etagpair_dict):
    # Flatten the nested structure
    df = pd.json_normalize(
        etagpair_dict['ETagPairLiveList']['ETagPairLives']['ETagPairLive'],
        record_path=['Flows', 'Flow'],
        meta=[
            'ETagPairID', 'StartETagStatus', 'EndETagStatus', 'StartTime', 'EndTime', 'DataCollectTime'
        ],
        meta_prefix='meta_',
        record_prefix='flow_'
    )
    
    # Add metadata fields from the root level to the DataFrame
    df['UpdateTime'] = etagpair_dict['ETagPairLiveList']['UpdateTime']
    df['UpdateInterval'] = etagpair_dict['ETagPairLiveList']['UpdateInterval']
    df['AuthorityCode'] = etagpair_dict['ETagPairLiveList']['AuthorityCode']
   
    df.rename(columns={'flow_VehicleType':'VehicleType',
                       'flow_TravelTime':'TravelTime',
                       'flow_StandardDeviation':'StandardDeviation',
                       'flow_SpaceMeanSpeed':'SpaceMeanSpeed',
                       'flow_VehicleCount':'VehicleCount', 
                       'meta_ETagPairID':'ETagPairID',
                       'meta_StartETagStatus':'StartETagStatus',
                       'meta_EndETagStatus':'EndETagStatus', 
                       'meta_StartTime':'StartTime',
                       'meta_EndTime':'EndTime', 
                       'meta_DataCollectTime':'DataCollectTime'}, inplace=True)
    df = df[['UpdateTime', 'UpdateInterval', 'AuthorityCode', 'ETagPairID', 'StartETagStatus', 
             'EndETagStatus', 'VehicleType', 'TravelTime', 'StandardDeviation', 'SpaceMeanSpeed', 
             'VehicleCount', 'StartTime', 'EndTime', 'DataCollectTime']]
    time_cols = ['UpdateTime', 'StartTime', 'EndTime', 'DataCollectTime']
    for col in time_cols:
        df[col]=pd.to_datetime(df[col])
    return df

def generate_daterange_combinations(start_year: int, 
                                    start_month: int, 
                                    end_year: int, 
                                    end_month: int) -> list[list[str]]:
    '''
    根據輸入的起訖年、月來組成一個list of list，list中會以年月為基本單位去包裝每個月的頭尾，方便後續使用

    Parameters
    ----------
    start_year: int
    start_month: int
    end_year: int
    end_month: int
    
    Return
    ------
    list: 
    '''
    date_combinations = []
    start_date = pd.Timestamp(start_year, start_month, 1)
    end_date = pd.Timestamp(end_year, end_month, 1) + pd.offsets.MonthEnd(1)
    
    current_date = start_date
    while current_date <= end_date:
        start_of_month = current_date.strftime('%Y%m%d')
        end_of_month = (current_date + pd.offsets.MonthEnd(1)).strftime('%Y%m%d')
        date_combinations.append([start_of_month, end_of_month])
        current_date += pd.offsets.MonthBegin(1)
        
    return date_combinations