# Taiwan Freeway5 Travel Time Anlysis Project (hw5_ts_project)

**作者:** William Huang   
**描述:**  
本專案旨在分析國道五號北向的旅行時間，探索相關影響因子並生成視覺化報告。透過數據處理和分析讓我們得以檢視應用當前新穎的神經網路模型預測下的成效

---

## 目錄 (Table of Contents)

1. [專案背景 (Project Background)](#專案背景-project-background)
2. [使用技術 (Technologies)](#使用技術-technologies)
3. [文件結構 (Folder Structure)](#文件結構-folder-structure)
4. [聯絡方式 (Contact)](#聯絡方式-contact)

---

## 專案背景 (Project Background)

在學習時間序列分析相關的技術跟模型上，需要題目來驗證技術跟手法，本專案是在參考 ”113年國道智慧交通管理創意競賽-時間預測分析與探討” 採納的資料與場景後訂定的，利用國道事故、道路施工等相關資料進行時間序列分析與預測，建構出適合各路段的旅行時間預測的神經網路模型  

選定國道五號北向作為專案目標的範圍:
- 幾何型態單純，無複雜的交流道存在，大大縮減了影響車流旅行時間的變因  
- 範圍小，適合快速實驗，序列總數較少，觀測上比較能收斂  

時間序列資料範圍:

- 2023年一整年的旅行時間為主，進行建模與交叉驗證
- 以完成模型的交叉驗證作為專案成果

---

## 使用技術 (Technologies)
這邊僅列核心的套件，詳細部分請參考requirements:
- **程式語言:** python 3.10.14
- **數據處理:** pandas, numpy
- **數據可視化:** matplotlib, seaborn
- **機器學習、深度學習、時間序列:** statsforecast, neuralforecast

---

## 文件結構 (Folder Structure)

```plaintext
travel-time-analysis-project/
├── data/                     # 原始數據與處理後數據
│   ├── raw/                  # 原始數據
│   ├── cleaned/            # 清理與轉換後的數據
│   ├── features/            # 處理後並附加上特徵的資料
├── hwttp/                    # 存放專案使用到的相關python file
├── notebooks/                # Jupyter Notebook 文件，本專案所有處理、分析的操作過程
├── outputs/                  # 建模生成的所有成果
│   ├── best/                 # 建模後最佳成果
│   ├── multi_w_nn/            # 多變量神經網路成果
│   ├── uni_w_nn/              # 單變量神經網路成果
├── requirements.txt          # 依賴庫清單
├── README.md                 # 專案說明文件
```

---

## 問題回饋與聯絡方式 (Feedback and Contact)
對於repo有任何問題或建議  
歡迎聯繫：wh49hng@outlook.com 或通過 GitHub 提交 issue。

