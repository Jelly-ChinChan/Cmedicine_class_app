# streamlit_app.py —— 圖片↔中文分類 配對測驗
# Author: Jelly + GPT-5 Thinking
#
# 使用方式：
#   1. 把這個檔案跟 Cmedicine_class_app.xlsx 放在同一層
#   2. 解壓 file_photo.zip 成資料夾 photos/ ，裡面放 1.jpg, 2.jpg, ...
#   3. 在該資料夾執行: streamlit run streamlit_app.py
#
# Excel/CSV 欄位允許（擇一即可）：
#   名稱欄: name / 名稱 / 藥名 / 品項
#   圖片欄: filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔
#   分類欄: category / 分類 / 類別 / 功效分類 / 藥性分類
#
# 遊戲流程：
#   - 顯示圖片
#   - 學生選圖片的正確「分類」
#   - 一鍵送出答案→下一題
#   - 結束後顯示總分，可以重新開始

import streamlit as st
import pandas as pd
import random
import os

# 嘗試 import 供 pandas 使用的引擎
try:
    import openpyxl  # for .xlsx
except ImportError:
    pass

try:
    import xlrd  # for .xls
except ImportError:
    pass

# ===================== 可調參數 =====================
EXCEL_PATH = "Cmedicine_class_app.xlsx"  # 題庫資料檔名
IMAGE_DIR = "photos"                     # 圖片資料夾 (解壓後的 1.jpg,2.jpg,...)
NUM_OPTIONS = 4                          # 每題出現幾個選項(含正解)。不足時自動縮到可用數量

st.set_page_config(
    page_title="中藥圖像分類小測驗",
    page_icon="🌿",
    layout="centered"
)

# ===================== 資料載入相關 =====================

def safe_load_table(path: str) -> pd.DataFrame:
    """
    嘗試載入題庫檔案（支援 .xlsx / .xls / .csv）
    回傳 pandas.DataFrame
    如果失敗，直接 st.error(...) 然後 st.stop()
    """
    if not os.path.isfile(path):
        st.error(f"❌ 找不到題庫檔案：{path}\n請確認檔案跟 streamlit_app.py 在同一個資料夾。")
        st.stop()

    _, ext = os.path.splitext(path)
    ext = ext.lower()

    # 根據副檔名嘗試
    if ext == ".xlsx":
        # 優先 openpyxl
        try:
            return pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            st.warning(f"⚠ 無法用 openpyxl 讀 .xlsx：{e}，改用自動引擎嘗試")
        try:
            return pd.read_excel(path)
        except Exception as e:
            st.error(f"❌ 載入 .xlsx 失敗：{e}")
            st.stop()

    if ext == ".xls":
        # 優先 xlrd
        try:
            return pd.read_excel(path, engine="xlrd")
        except Exception as e:
            st.warning(f"⚠ 無法用 xlrd 讀 .xls：{e}，改用自動引擎嘗試")
        try:
            return pd.read_excel(path)
        except Exception as e:
            st.error(f"❌ 載入 .xls 失敗：{e}")
            st.stop()

    if ext == ".csv":
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"❌ 載入 .csv 失敗：{e}")
            st.stop()

    # 如果副檔名不明，依序瘋狂嘗試三種
    for try_fn in [
        lambda: pd.read_excel(path, engine="openpyxl"),
        lambda: pd.read_excel(path, engine="xlrd"),
        lambda: pd.read_excel(path),
        lambda: pd.read_csv(path),
    ]:
        try:
            return try_fn()
        except Exception:
            pass

    st.error(
        "❌ 無法判讀題庫格式。\n"
        "請確認檔案是 .xlsx / .xls / .csv 其中之一，且沒有被其他程式鎖住。"
    )
    st.stop()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    把老師的欄位對應到固定三欄：
        name      -> 中藥名稱
        filename  -> 圖片檔名 (ex: 1.jpg)
        category  -> 分類 (ex: 補氣藥)
    支援中英文欄名。
    對不到就 st.error + stop()
    """
    col_map_candidates = {
        "name": [
            "name", "名稱", "藥名", "品項"
        ],
        "filename": [
            "filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"
        ],
        "category": [
            "category", "分類", "類別", "功效分類", "藥性分類"
        ],
    }

    col_map = {}
    for std_col, candidates in col_map_candidates.items():
        for c in candidates:
            if c in df.columns:
                col_map[std_col] = c
                break

    needed = ["name", "filename", "category"]
    missing = [n for n in needed if n not in col_map]
    if missing:
        st.error(
            "❌ 題庫欄位無法辨識，缺少：" + ", ".join(missing) +
            "\n可接受欄名示例：\n"
            "  名稱欄: name / 名稱 / 藥名 / 品項\n"
            "  圖片欄: filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔\n"
            "  分類欄: category / 分類 / 類別 / 功效分類 / 藥性分類"
        )
        st.stop()

    df_norm = pd.DataFrame({
        "name": df[col_map["name"]].astype(str).str.strip(),
        "filename": df[col_map["filename"]].astype(str).str.strip(),
        "category": df[col_map["category"]].astype(str).str.strip(),
    })

    return df_norm


def load_question_bank():
    """
    讀檔 -> 欄位正規化 -> 轉成 list[dict] 題庫
    並檢查圖片是否存在
    """
    df_raw = safe_load_table(EXCEL_PATH)
    df = normalize_columns(df_raw)

    bank = []
    for _, row in df.iterrows():
        item_name = row["name"]
        filename = row["filename"]
        category = row["category"]

        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.isfile(img_path):
            st.warning(f"⚠ 找不到圖片檔: {img_path}")

        bank.append({
            "name": item_name,
            "filename": filename,
            "category": category,
        })

    if len(bank) == 0:
        st.error("❌ 題庫是空的，請確認 Excel/CSV 內有資料列。")
        st.stop()

    return bank

# ===================== 測驗狀態管理 =====================

def init_session_state(bank):
    """
    第一次載入或重新開始時初始化狀態
    """
    random_order = bank[:]
    random.shuffle(random_order)

    st.session_state.questions = random_order        # 題目的隨機順序
    st.session_state.total = len(random_order)       # 總題數
    st.session_state.index = 0                       # 目前第幾題 (0-based)
    st.session_state.score = 0                       # 累計得分
    st.session_state.submitted = False               # 這題是否已送出
    st.session_state.selected = None                 # 學生目前選的選項
    st.session_state.finished = False                # 是否已完成所有題
    st.session_state.options_cache = {}              # 每題的選項固定住


def get_current_question():
    """
    回傳目前題目的 dict
    """
    i = st.session_state.index
    return st.session_state.questions[i]


def get_all_categories(bank):
    """
    回傳題庫中所有獨特分類的列表（排序後）
    """
    return sorted(list(set([q["category"] for q in bank])))


def build_options(correct_cat, all_cats, k=4):
    """
    產生單題的選項列表：
    - 一定包含正確答案
    - 其他選項為隨機干擾
    - 打亂順序
    """
    distractors = [c for c in all_cats if c != correct_cat]
    random.shuffle(distractors)

    opts = distractors[: max(0, k - 1)]
    opts.append(correct_cat)

    # 去重 & 打亂
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

# ===================== UI 元件 =====================

def render_progress_card():
    """
    上方進度/得分卡 + 簡單進度條
    """
    current_q_num = st.session_state.index + 1
    total_q = st.session_state.total
    pct = (current_q_num / total_q) * 100
    score_now = st.session_state.score

    card_html = f"""
    <div style="
        border-radius:16px;
        box-shadow:0 4px 12px rgba(0,0,0,0.08);
        padding:12px 16px;
        background:linear-gradient(to right, #f8f9fa, #ffffff);
        font-size:14px;
        line-height:1.4;
        border:1px solid rgba(0,0,0,0.05);
        margin-bottom:12px;
    ">
        <div style="font-weight:600; font-size:15px; margin-bottom:4px;">
            進度 {current_q_num} / {total_q}（{pct:.0f}%）
        </div>
        <div style="font-size:13px; color:#444;">
            目前得分：<span style="font-weight:600;">{score_now}</span>
        </div>
        <div style="margin-top:8px; height:8px; width:100%;
                    background:#e9ecef; border-radius:4px; overflow:hidden;">
            <div style="
                height:100%;
                width:{pct}%;
                background:#74c69d;
            "></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_final_screen():
    """
    全部題目答完後的結算畫面
    """
    total_q = st.session_state.total
    score = st.session_state.score

    st.success(f"完成測驗！總得分：{score} / {total_q}")

    if st.button("重新開始", use_container_width=True):
        # 重新洗題目並歸零
        init_session_state(st.session_state.questions)

# ===================== 主流程 =====================

# 1. 載題庫
bank = load_question_bank()

# 2. 如果 session_state 還沒準備好（第一次或剛重設）
if "questions" not in st.session_state:
    init_session_state(bank)

# 3. 如果整份測驗做完，就顯示結束畫面
if st.session_state.finished:
    st.title("🌿 中藥圖像分類小測驗")
    render_final_screen()
    st.stop()

# 4. 還沒做完：拿目前題目
q = get_current_question()
all_categories = get_all_categories(bank)

# 5. 取得或建立本題的選項，並固定住
qid_key = f"q{st.session_state.index}"
if qid_key not in st.session_state.options_cache:
    st.session_state.options_cache[qid_key] = build_options(
        correct_cat=q["category"],
        all_cats=all_categories,
        k=NUM_OPTIONS
    )
options = st.session_state.options_cache[qid_key]

# ===================== 畫面呈現 =====================

st.title("🌿 中藥圖像分類小測驗")

# 進度卡
render_progress_card()

# 題目敘述
st.markdown(
    f"**Q{st.session_state.index + 1}. 這個屬於哪一類？**",
    help="請看圖片並選正確分類"
)

# 顯示圖片
img_path = os.path.join(IMAGE_DIR, q["filename"])
st.image(
    img_path,
    caption=f"{q['name']}（{q['filename']}）",
    use_column_width=True
)

# 單選選項
if st.session_state.selected not in options:
    st.session_state.selected = None

st.session_state.selected = st.radio(
    "選擇分類：",
    options,
    index=options.index(st.session_state.selected) if st.session_state.selected in options else None,
    label_visibility="collapsed",
)

# 如果已送出，顯示對錯 feedback
if st.session_state.submitted:
    if st.session_state.selected == q["category"]:
        st.markdown(
            f"<div style='color:#2f9e44; font-weight:600;'>✔ 答對！正確分類：{q['category']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='color:#d00000; font-weight:600;'>✘ 答錯</div>"
            f"<div style='margin-top:4px;'>正確分類：<b>{q['category']}</b></div>",
            unsafe_allow_html=True
        )

    st.markdown(
        f"<div style='font-size:13px; color:#666; margin-top:6px;'>"
        f"這張圖是：{q['name']}"
        f"</div>",
        unsafe_allow_html=True
    )

# 單一按鈕：未送出→送出答案 / 已送出→下一題
button_label = "送出答案" if not st.session_state.submitted else "下一題"

if st.button(button_label, use_container_width=True):
    # 狀態一：第一次按 -> 送出答案
    if not st.session_state.submitted:
        st.session_state.submitted = True
        if st.session_state.selected == q["category"]:
            st.session_state.score += 1

    # 狀態二：已送出 -> 換下一題
    else:
        st.session_state.index += 1
        st.session_state.submitted = False
        st.session_state.selected = None  # 清掉上一題的選擇

        if st.session_state.index >= st.session_state.total:
            st.session_state.finished = True

# 如果剛剛按完就剛好做完所有題目，馬上顯示結算
if st.session_state.finished:
    st.success("測驗完成！")
    render_final_screen()
