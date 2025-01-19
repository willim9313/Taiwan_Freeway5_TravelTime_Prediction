import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def setup_plot(title: str, 
               xlabel: str, 
               ylabel: str, 
               figsize: tuple=(15, 6)) -> plt.Axes:
    """
    設置圖表的基本屬性

    Parameters
    -----
    title: 圖表標題
    xlabel: x 軸標籤
    ylabel: y 軸標籤
    figsize: 圖表的大小，預設為 (15, 6)
    
    Returns
    -----
    Axes: plt.Axes 返回 Axes 對象，用於後續的圖表繪製。
    """
    plt.figure(figsize=figsize)
    plt.style.use('default')
    ax = plt.gca() # 獲取當前 Axes對象
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_facecolor('whitesmoke') # 設定背景顏色
    return ax


def customize_xaxis(ax: plt.Axes, 
                    start_datetime: str, 
                    end_datetime: str) -> None:
    """
    根據時間範圍調整 x-axis 的定位器和格式化器
    
    Parameters
    -----
    ax: Matplotlib Axes 對象
    start_datetime: 起始時間，字串或 datetime 對象，格式為 'YYYY-MM-DD HH:MM'
    end_datetime: 結束時間，字串或 datetime 對象，格式為 'YYYY-MM-DD HH:MM'

    Returns
    -----
    None，而是直接修改傳入的 Axes 對象

    """
    delta = pd.to_datetime(end_datetime) - pd.to_datetime(start_datetime)
    
    if delta.days <= 2:  # in 48 hours, provide hourly formats
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H\n%d\n%b'))
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H'))
        
    elif delta.days <= 3:  # below 3 days, provide 12 hours interval labels
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d\n%b'))
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
        
    elif delta.days <= 14:  # below 2 weeks
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d\n%b\n%Y'))
        ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
        
    elif delta.days <= 31:  # over 2 weeks and below a month
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d\n%b\n%Y'))
        ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
        
    else:  # Over a month, show date label after 7 days
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d\n%b\n%Y'))
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=1))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
        
    # 調整圖表邊距以提供額外空間
    plt.subplots_adjust(bottom=0.2)
    # 防止標籤重疊，旋轉主要標籤
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha="center")
    plt.setp(ax.xaxis.get_minorticklabels(), rotation=0)


def label_weekends(df: pd.DataFrame, 
                   ax: plt.Axes) -> None:
    """
    在時間序列圖表上標註周末區域。
    
    Parameters
    -----
    df: 包含時間序列數據的 DataFrame，其中需包含 'dayofweek' 欄位（1-7 表示星期一到星期日）。
    ax: Matplotlib 的 Axes 對象，用於繪製圖表。

    Returns
    -----
    None，直接在傳入的 Axes 對象上繪製周末區域。

    """
    df['is_weekend'] = df['dayofweek'].apply(lambda x: True if x in [6, 7] else False)
    df['weekend_start'] = (df['is_weekend'] != df['is_weekend'].shift()).cumsum()
    weekend_ranges = df[df['is_weekend']].groupby('weekend_start')['ds'].agg(['min', 'max'])
    for _, row in weekend_ranges.iterrows():
        ax.axvspan(row['min'], row['max'], color='yellow', alpha=0.1)


def label_holidays(df: pd.DataFrame, 
                   ax: plt.Axes) -> None:
    """
    在時間序列圖表上標註假期區域。

    Parameters
    ----------
    df : 包含時間序列數據的 DataFrame，其中需包含 'holiday_length' 列，表示每個日期的假期長度。
    ax : Matplotlib 的 Axes 對象，用於繪製圖表。

    Returns
    -------
    None，直接在傳入的 Axes 對象上繪製假期區域。
    """
    # 添加 'is_holiday' 列標註是否為假期，假期長度大於或等於 1 則為假期
    df['is_holiday'] = df['holiday_length'].apply(lambda x: True if x >= 1 else False)
    # 根據 'is_holiday' 的變化情況創建 'holiday_start' 標籤，用於分組
    df['holiday_start'] = (df['is_holiday'] != df['is_holiday'].shift()).cumsum()
    
    # 分組計算每個假期的起始和結束日期
    holiday_ranges = df[df['is_holiday']].groupby('holiday_start')['ds'].agg(['min', 'max'])
    
    # 在圖表中標註每個假期的區域
    for _, row in holiday_ranges.iterrows():
        ax.axvspan(row['min'], row['max'], color='red', alpha=0.1)


def label_accidents(df: pd.DataFrame, 
                    ax: plt.Axes) -> None:
    """
    在時間序列圖表上標註不同類型的事故。

    Parameters
    ----------
    df : pd.DataFrame
        包含時間序列數據的 DataFrame，其中需包含 'accident_type' 和 'WeightedAvgTravelTime' 列。
        - 'accident_type': 1, 2, 3 分別表示不同類型的事故(A1, A2, A3)。
        - 'WeightedAvgTravelTime': 加權平均旅行時間。
    ax : plt.Axes
        Matplotlib 的 Axes 對象，用於繪製圖表。

    Returns
    -------
    None
        此函數無返回值，直接在傳入的 Axes 對象上繪製事故標註。
    """
    # 標註不同類型的事故
    ax.scatter(df[df['accident_type'] == 1]['ds'], 
               df[df['accident_type'] == 1]['WeightedAvgTravelTime'], 
               color='red', marker='X', label='A1 Accident')
    
    ax.scatter(df[df['accident_type'] == 2]['ds'], 
               df[df['accident_type'] == 2]['WeightedAvgTravelTime'], 
               color='red', marker='x', label='A2 Accident')
    
    ax.scatter(df[df['accident_type'] == 3]['ds'], 
               df[df['accident_type'] == 3]['WeightedAvgTravelTime'], 
               color='red', marker='2', label='A3 Accident')


def label_congestion(df: pd.DataFrame, 
                     ax: plt.Axes) -> None:
    """
    在時間序列圖表上標註擁堵區域。

    Parameters
    ----------
    df : pd.DataFrame
        包含時間序列數據的 DataFrame，其中需包含 'congestion_syndrome' 列，
        該列表示每個日期的擁堵情況，數值大於或等於 1 則表示擁堵。
    ax : plt.Axes
        Matplotlib 的 Axes 對象，用於繪製圖表。

    Returns
    -------
    None
        此函數無返回值，直接在傳入的 Axes 對象上繪製擁堵區域。
    """
    # 添加 'is_congested' 列標註是否為擁堵區域，擁堵症狀指數大於等於 1 即為擁堵
    df['is_congested'] = df['congestion_syndrome'].apply(lambda x: True if x >= 1 else False)
    
    # 根據 'is_congested' 的變化情況創建 'congestion_start' 標籤，用於分組
    df['congestion_start'] = (df['is_congested'] != df['is_congested'].shift()).cumsum()
    
    # 分組計算每個擁堵區間的起始和結束日期
    congestion_ranges = df[df['is_congested']].groupby('congestion_start')['ds'].agg(['min', 'max'])
    
    # 在圖表中標註每個擁堵區域
    for _, row in congestion_ranges.iterrows():
        ax.axvspan(row['min'], row['max'], color='grey', alpha=0.3)

def label_roadbuild(df: pd.DataFrame, 
                    ax: plt.Axes) -> None:
    """
    在時間序列圖表上標註道路施工時間段。

    Parameters
    ----------
    df : pd.DataFrame
        包含時間序列數據的 DataFrame，其中需包含 'road_build' 列，
        該列表示每個日期的擁堵情況，數值大於或等於 1 則表示施工中。
    ax : plt.Axes
        Matplotlib 的 Axes 對象，用於繪製圖表。

    Returns
    -------
    None
        此函數無返回值，直接在傳入的 Axes 對象上繪製擁堵區域。
    """
    # 添加 'is_congested' 列標註是否為擁堵區域，擁堵症狀指數大於等於 1 即為擁堵
    df['is_roadbuild'] = df['road_build'].apply(lambda x: True if x >= 1 else False)
    
    # 根據 'is_congested' 的變化情況創建 'congestion_start' 標籤，用於分組
    df['roadbuild_start'] = (df['is_roadbuild'] != df['is_roadbuild'].shift()).cumsum()
    
    # 分組計算每個擁堵區間的起始和結束日期
    roadbuild_ranges = df[df['is_roadbuild']].groupby('roadbuild_start')['ds'].agg(['min', 'max'])
    
    # 在圖表中標註每個擁堵區域
    for _, row in roadbuild_ranges.iterrows():
        ax.axvspan(row['min'], row['max'], color='gray', alpha=0.3, hatch='/')



def extra_plot_ds_prev(df: pd.DataFrame) -> None:
    '''
    在時間序列圖表上繪製下游旅行時間數據。

    Parameters
    ----------
    df : pd.DataFrame
        包含時間序列數據的 DataFrame，其中需包含 'ds' 和以下列名的數據:
        - 'ds_prev_1_WATT' 至 'ds_prev_5_WATT' 表示不同下游時間點的加權平均旅行時間。

    Returns
    -------
    None
        此函數無返回值，直接在當前的圖表上繪製多條下游旅行時間線。
    '''
    plt.plot(df['ds'], df['ds_prev_1_WATT'], color='#89C2D9', label='ds_prev_1_WATT')
    plt.plot(df['ds'], df['ds_prev_2_WATT'], color='#61A5C2', label='ds_prev_2_WATT')
    plt.plot(df['ds'], df['ds_prev_3_WATT'], color='#468FAF', label='ds_prev_3_WATT')
    plt.plot(df['ds'], df['ds_prev_4_WATT'], color='#2C7DA0', label='ds_prev_4_WATT')
    plt.plot(df['ds'], df['ds_prev_5_WATT'], color='#2A6F97', label='ds_prev_5_WATT')


def plot_pred(cv_df: pd.DataFrame, 
              pred_col: str, 
              start_datetime: str, 
              end_datetime: str, 
              enable_prev: bool=False, 
              enable_cong_label: bool=False, 
              enable_roadbuild_label: bool=True) -> None:
    """
    在給定的時間範圍內繪製預測結果與實際旅行時間，並根據需求顯示下游數據。

    Parameters
    ----------
    cv_df : pd.DataFrame
        包含預測與實際數據的 DataFrame，其中需包含 'ds', 'WeightedAvgTravelTime', 
        'gf_gt' 列和預測結果列。
    pred_col : str
        預測結果列的名稱。
    start_datetime : str
        要繪製的時間範圍起始日期，格式為 'YYYY-MM-DD'。
    end_datetime : str
        要繪製的時間範圍結束日期，格式為 'YYYY-MM-DD'。
    enable_prev : bool, optional
        是否顯示下游旅行時間資料，默認為 False。
    enable_cong_label: bool, optional
        是否打開壅塞時段的標註，莫認為 True

    Returns
    -------
    None
        此函數無返回值，直接繪製完整的時間序列圖表。
    """
    # 設定圖表標題為唯一的 'gf_gt' 值
    title = cv_df['gf_gt'].unique()[0]
    # 過濾時間範圍內的數據
    df = cv_df[cv_df['ds'].between(start_datetime, end_datetime)].copy()
    
    # 使用通用函數設置圖表屬性
    ax = setup_plot(title, 'Datetime', 'Travel Time')
    
    # 繪製實際加權平均旅行時間與預測結果
    plt.plot(df['ds'], df['WeightedAvgTravelTime'], color='royalblue', label='WeightedAvgTravelTime')
    plt.plot(df['ds'], df[pred_col], linestyle='dashed', color='darkorange', label='predictions')
    
    # 判斷是否需要繪製下游旅行時間數據
    if enable_prev:
        extra_plot_ds_prev(df)

    # Apply labeling and customization
    label_weekends(df, ax)
    label_holidays(df, ax)
    label_accidents(df, ax)

    if enable_roadbuild_label:
        label_roadbuild(df, ax)
    # 判斷是否要加標註壅塞時段
    if enable_cong_label:
        label_congestion(df, ax)
    customize_xaxis(ax, start_datetime, end_datetime)
    
    # 設置 x 軸的顯示範圍
    plt.xlim(df['ds'].min(), df['ds'].max())
    # 添加圖例和網格
    plt.legend()
    plt.grid(True, which='both') # 顯示主要和次要的網格線
    # 顯示圖表
    plt.show()

def plot_check_holiday(cv_df: pd.DataFrame, 
                       pred_col: str, 
                       holiday_name: str, 
                       ext_time: int = 1) -> None:
    """
    在指定的假期期間檢查並繪製實際和預測的旅行時間。

    Parameters
    ----------
    cv_df : pd.DataFrame
        包含預測與實際數據的 DataFrame，其中需包含 'ds', 'WeightedAvgTravelTime', 
        'gf_gt' 列和表示假期的標記列。
    pred_col : str
        預測結果列的名稱。
    holiday_name : str
        要檢查的假期名稱，需要與 DataFrame 中的列名部分匹配。
    ext_time : int, optional
        在假期開始和結束時延長繪圖範圍的倍數，每個單位代表 6 小時。默認為 1。

    Returns
    -------
    None
        此函數無返回值，直接繪製包含假期範圍的時間序列圖表。
    """
    # 設置圖表標題
    title = cv_df['gf_gt'].unique()[0]
    df = cv_df.copy()

    # 使用通用函數設置圖表屬性
    ax = setup_plot(title, 'Datetime', 'Travel Time')

    # 尋找符合假期名稱的列名
    target_col = None
    for col in df.columns:
        if holiday_name in col:
            target_col = col
            break  # 找到後提前結束循環

    # 如果沒有找到相應的假期列，則返回並提示錯誤
    if target_col is None:
        print(f"Holiday '{holiday_name}' 不存在於資料中。")
        return

    # 獲取假期標記的起始和結束索引
    ta_start_idx = df[df[target_col] == 1].index.min()
    ta_end_idx = df[df[target_col] == 1].index.max()

    # 確保索引延伸範圍不超過 DataFrame 的邊界
    ta_start_idx_ext = max(ta_start_idx - 24 * 4 * ext_time, 0)
    ta_end_idx_ext = min(ta_end_idx + 24 * 4 * ext_time + 1, len(df))

    # 根據擴展範圍過濾數據
    df = df.iloc[ta_start_idx_ext:ta_end_idx_ext].copy()
    start_datetime = df['ds'].min()
    end_datetime = df['ds'].max()

    # 繪製實際加權平均旅行時間與預測結果
    plt.plot(df['ds'], df['WeightedAvgTravelTime'], color='royalblue', label='WeightedAvgTravelTime')
    plt.plot(df['ds'], df[pred_col], linestyle='dashed', color='darkorange', label='predictions')
    
    # Apply labeling and customization
    label_weekends(df, ax)
    label_holidays(df, ax)
    label_accidents(df, ax)
    label_roadbuild(df, ax)
    customize_xaxis(ax, start_datetime, end_datetime)

    # 設置 x 軸的顯示範圍
    plt.xlim(df['ds'].min(), df['ds'].max())
    # 添加圖例和網格
    plt.legend()
    plt.grid(True, which='both')  # 顯示主要和次要的網格線
    # 顯示圖表
    plt.show()
