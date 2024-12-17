import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
import time
from datetime import datetime, timedelta

def create_directory_if_not_exists(path: str) -> None:
    """
    Check if the specified path exists, and create the directory if it does not exist.

    Parameters:
    path (str): The directory path to check and create if necessary.
    
    Returns:
    None
    """
    # Check if the directory exists
    if not os.path.exists(path):
        # Create the directory if it doesn't exist
        os.makedirs(path)
        print(f"Directory '{path}' created.")
    else:
        print(f"Directory '{path}' already exists.")
    return None

def download_file(url: str, 
                  save_path: str) -> None:
    '''
    單一文件下載處理

    Parameters
    ----------
    url: str
        目標文件的url
    save_path: str
        文件下載後儲存的路徑
    
    Return
    -----
    None
    '''
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kilobyte
    
    if response.status_code != 200:
        print(f"Failed to download {url}")
        return

    with open(save_path, 'wb') as file:
        for data in response.iter_content(block_size):
            file.write(data)

def download_files(base_url: str, 
                   file_names: list[str], 
                   save_dir: str) -> None:
    '''
    一次性下載多個文件用途，會根據url與file_name組出下載的目標
    並存放到save_dir中

    Parameters
    ----------
    base_url: str
        目標文件的主要路徑url
    file_names: list[str]
        使用list去包多個文件的名稱，['a1', 'a2', 'a3']
    save_dir: str
        儲存的目標資料夾路徑

    Return
    ------
    None

    '''
    os.makedirs(save_dir, exist_ok=True)
    for file_name in file_names:
        try:
            url = f"{base_url}{file_name}"
            save_path = os.path.join(save_dir, file_name)
            # print(f"Downloading {url} to {save_path}")
            download_file(url, save_path)
            # print(f"Downloaded {file_name} to {save_path}")
        except:
            print(f"Downloading {url} to {save_path} facing errors")


def generate_date_strings(start_date: str, 
                          end_date: str) -> list:
    '''
    datetime range generator

    Parameters
    ----------
    start_date : str
        e.g. '20230101'
    end_date : str
        e.g. '20230201'

    Returns
    -------
    date_list : list
        包含一連串像是'20230101'格式的日期

    '''
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    date_list = []
    
    current_date = start
    while current_date <= end:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    
    return date_list

def scrape_vd_data(date_list: list[str],
                   save_dir_upper: str='../data/raw/VD/',
                   select_data: str='all') -> None:
    '''
    可指定一連串的時間資訊下進行VD資料的爬取，原始VD資料有區分動態與靜態資訊，可透過指定參數來決定下載目標

    Parameters
    ----------
    date_list: list[str]
        輸入日期串，像是['20230101', '20230102']
    save_dir_upper: str
        資料爬取存放的上層路徑，其下日期的子資料夾會自動生成
    select_data: str
        原始資料有區分靜態、動態，'both'= 全數下載, 'static'=下載靜態, 'dynamic'= 下載動態
    
    Return
    ------
    None
    '''
    if select_data not in ['all', 'static', 'dynamic']:
        return 'select_data need to specify, please check the docstring.'

    create_directory_if_not_exists(save_dir_upper)

    for exact_date in tqdm(date_list):
        # 基本爬取的日期，以及預計要存放的路徑 
        base_url = f"https://tisvcloud.freeway.gov.tw/history/motc20/VD/{exact_date}/"
        save_dir = f'{save_dir_upper}{exact_date}'
        
        # 爬取該日期頁面下所有合理的
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        file_paths = []
        for i in soup.find_all('a'):
            if i.get('href').endswith('.xml.gz'):
                file_paths.append(i.get('href'))
        
        # 這種抓法會有名稱重複，因此要去重、排序
        # 裡面會有靜態、動態的VD資訊
        # VD 動態資訊(v2.0)	= YYYYMMDD/VDLive_HHmm.xml.gz
        # VD 靜態資訊(v2.0)	= YYYYMMDD/VD_0000.xml.gz
        
        file_paths = list(set(file_paths))
        file_paths.sort()

        # 排除或保留指定的資料類型
        if select_data =='static':
            file_paths = [file_path for file_path in file_paths if 'VD_' in file_path]
        elif select_data == 'dynamic':
            file_paths = [file_path for file_path in file_paths if 'VDLive_' in file_path]
        else:
            pass
            
        # file_names = [f"VDLive_{i:04d}.xml.gz" for i in range(1, 2359)]  # 根据你需要的文件名生成列表
        for file_name in file_paths:
            if os.path.exists(save_dir+'/'+file_name): # 跳過已經有檔案的部分
                continue
            download_files(base_url, [file_name], save_dir)
            time.sleep(1.5)
        # time.sleep(3)


def scrape_etag_info(date_list: list[str],
                     save_dir_upper: str='../data/raw/ETag/',
                     select_data: str='all') -> None:
    '''
    可指定一連串的時間資訊下進行VD資料的爬取，原始VD資料有區分動態與靜態資訊，可透過指定參數來決定下載目標

    Parameters
    ----------
    date_list: list[str]
        輸入日期串，像是['20230101', '20230102']
    save_dir_upper: str
        資料爬取存放的上層路徑，其下日期的子資料夾會自動生成
    select_data: str
        原始資料有區分靜態、動態，'all'= 全數下載, 'info'=靜態資訊下載, 'pair_static'= 配對靜態下載, 'pair_dynamic' = 配對動態下載  
        eTag 靜態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETag_0000.xml.gz  
        eTag 配對路徑靜態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETagPair_0000.xml.gz  
        eTag 配對路徑動態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETagPairLive_HHmm.xml.gz  
    
    Return
    ------
    None
    '''
    if select_data not in ['all', 'info', 'pair_static', 'pair_dynamic']:
        return 'select_data need to specify, please check the docstring.'
    
    for exact_date in tqdm(date_list):
        # 基本爬取的日期，以及預計要存放的路徑 
        base_url = f"https://tisvcloud.freeway.gov.tw/history/motc20/ETag/{exact_date}/"
        save_dir = f'{save_dir_upper}{exact_date}'
        
        create_directory_if_not_exists(save_dir)
        
        # 爬取該日期頁面下所有合理的
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        file_paths = []
        for i in soup.find_all('a'):
            if i.get('href').endswith('.xml.gz'):
                file_paths.append(i.get('href'))
        
        # 這種抓法會有名稱重複，因此要去重、排序
        # 裡面會有3種的ETag資訊
        # eTag 靜態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETag_0000.xml.gz	
        # eTag 配對路徑靜態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETagPair_0000.xml.gz
        # eTag 配對路徑動態資訊(v2.0) = ./history/motc20/ETag/YYYYMMDD/ETagPairLive_HHmm.xml.gz
        
        file_paths = list(set(file_paths))
        file_paths.sort()

        # 排除或保留指定的資料類型
        if select_data =='info':
            file_paths = [file_path for file_path in file_paths if 'ETag_' in file_path]
        elif select_data == 'pair_static':
            file_paths = [file_path for file_path in file_paths if 'ETagPair_' in file_path]
        elif select_data == 'pair_dynamic':
            file_paths = [file_path for file_path in file_paths if 'ETagPairLive_' in file_path]
        else:
            pass

        for file_name in file_paths:
            if os.path.exists(save_dir+'/'+file_name): # 跳過已經有檔案的部分
                continue
            download_files(base_url, [file_name], save_dir)
            time.sleep(1)
        # time.sleep(3)

def scrape_etag_intergantry_traveltime(date_list: list[str],
                                       save_dir: str='../data/raw/ETag_intergantry_traveltime') -> None:
    '''
    可指定一連串的時間資訊下進行ETag gantry間通過所花費的旅行時間為主資料的爬取

    Parameters
    ----------
    date_list: list[str]
        輸入日期串，像是['20230101', '20230102']
    save_dir: str
        資料下載後儲存的路徑，如果不存在會自動建立folder
    
    Return
    ------
    None
    '''

    base_url = f"https://tisvcloud.freeway.gov.tw/history/TDCS/M04A/"
    
    create_directory_if_not_exists(save_dir)


    for date in tqdm(date_list):
        file_name = f'M04A_{date}.tar.gz'
        if os.path.exists(save_dir+'/'+file_name): # 跳過已經有檔案的部分
            continue
        download_files(base_url, [file_name], save_dir)
        time.sleep(1) 

def scrape_etag_gantry_volume(date_list: list[str],
                              save_dir: str='../data/raw/ETag_gantry_vol') -> None:
    '''
    可指定一連串的時間資訊下進行ETag gantry通過車流量為主資料的爬取

    Parameters
    ----------
    date_list: list[str]
        輸入日期串，像是['20230101', '20230102']
    save_dir: str
        資料下載後儲存的路徑，如果不存在會自動建立folder
    
    Return
    ------
    None
    '''
    base_url = f"https://tisvcloud.freeway.gov.tw/history/TDCS/M03A/"

    create_directory_if_not_exists(save_dir)

    for date in tqdm(date_list):
        file_name = f'M03A_{date}.tar.gz'   
        if os.path.exists(save_dir+'/'+file_name): # 跳過已經有檔案的部分
            continue
        download_files(base_url, [file_name], save_dir)
        time.sleep(1) 

def scrape_etag_intergantry_speed(date_list: list[str],
                                  save_dir: str='../data/raw/ETag_intergantry_speed') -> None:
    '''
    可指定一連串的時間資訊下進行ETag gantry間通過車速為主資料的爬取

    Parameters
    ----------
    date_list: list[str]
        輸入日期串，像是['20230101', '20230102']
    save_dir: str
        資料下載後儲存的路徑，如果不存在會自動建立folder
    
    Return
    ------
    None
    '''
    
    base_url = f"https://tisvcloud.freeway.gov.tw/history/TDCS/M05A/"

    create_directory_if_not_exists(save_dir)

    for date in tqdm(date_list):
        file_name = f'M05A_{date}.tar.gz'
        if os.path.exists(save_dir+'/'+file_name): # 跳過已經有檔案的部分
            continue
        download_files(base_url, [file_name], save_dir)
        time.sleep(1) 
    
    return None