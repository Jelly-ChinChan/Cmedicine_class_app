# streamlit_app.py —— 圖片↔中文分類 配對測驗
# Author: Jelly + GPT-5 Thinking
#
# 使用方式：
#   1. 把這個檔案跟 Cmedicine_class_app.xlsx 放在同一層
#   2. 解壓 file_photo.zip 成資料夾 photos/ ，裡面放 1.jpg, 2.jpg, ...
#   3. 在這個資料夾執行: streamlit run streamlit_app.py
#
# Excel 允許兩種欄位命名：
#   英文: name / filename / category
#   中文: 名稱 / 圖片檔名 / 分類
#
# 測驗流程：
#   - 顯示圖片
#   - 學生選該圖片的正確「分類」
#   - 一鍵送出答案→下一題
#   - 最後顯示總分，並可重新開始
#
# 介面風格：
#   - 進度卡 + 得分
#   - 單選題
#   - 手機友善，只有一顆主按鈕

import streamlit as st
import pandas as pd
import random
import os

# 有些環境需要明確 import 這些，才不會讀檔時被 pandas 抱怨沒 engine
try:
    import openpyxl  # for .xlsx
except ImportError:
    pass

try:
    import xlrd  # for .xls
except ImportError:
    pass

# ===================== 可調參數 =====================
EXCEL_PATH = "Cmedicine_class_app.xlsx"  # 題庫檔案
IMAGE_DIR = "photos"                     # 圖片資料夾
NUM_OPTIONS = 4                          # 每題最多幾個選項 (包含正確答案)

st.set_page_config(
    page_title="中藥圖像分類小測驗",
    page_icon="🌿",
    layout="centered"
)

# ===================== 工具函式 =====================

def safe_load_table(path):
    """
    嘗試載入題庫檔案（Excel / CSV）
    回傳 pandas.DataFrame
    如果失敗，直接 st.error(...) 然後 st.stop()
    """
    if not os.path.isfile(path):
        st.error(f"❌ 找不到題庫檔案：{path}\n請確認檔案跟 streamlit_app.py 在同一個資料夾。")
        st.stop()

    # 先看副檔名，主要是用來猜格式
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    # 嘗試依序讀檔
    # 1. xlsx 用 openpyxl
    if ext == ".xlsx":
        try:
            return pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            st.warning(f"⚠ 無法用 openpyxl 讀 .xlsx：{e}，改用其他方式嘗試")

            # fallback: 讓 pandas 自己猜
        try:
            return pd.read_excel(path)
        except Exception as e:
            st.error(f"❌ 載入 .xlsx 失敗：{e}")
            st.stop()

    # 2. xls 用 xlrd
    if ext == ".xls":
        try:
            return pd.read_excel(path, engine="xlrd")
        except Exception as e:
            st.warning(f"⚠ 無法用 xlrd 讀 .xls：{e}，改用其他方式嘗試")
        try:
            return pd.read_excel(path)
        except Exception as e:
            st.error(f"❌ 載入 .xls 失敗：{e}")
            st.stop()

    # 3. csv
    if ext == ".csv":
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"❌ 載入 .csv 失敗：{e}")
            st.stop()

    # 4. 如果副檔名不明，或上面都沒處理成功：
    #    我們最後再瘋狂嘗試：openpyxl→xlrd→csv
    #    這是保險用，避免有人把 .xlsx 改成沒有副檔名
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception:
        pass
    try:
        return pd.read_excel(path, engine="xlrd")
    except Exception:
        pass
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"❌ 最後嘗試仍無法讀入題庫：{e}\n"
                 f"請確認 {path} 是 xlsx/xls/csv 其中之一，且未被其他程式鎖住。")
        st.stop()


def normalize_columns(df):
    """
    嘗試把老師的欄位對應到固定三個鍵：
    - name      (藥名 / 名稱)
    - filename  (圖片檔名)
    - category  (分類)

    支援中英文欄名。
    失敗就 st.error + stop。
    """
    col_map_candidates = {
        "name": ["name", "名稱", "藥名", "品項"],
        "filename": ["filenam]()
