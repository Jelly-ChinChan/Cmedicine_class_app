# Cmedicine_class_app.py —— 圖片↔中文分類 測驗 App
# Author: Jelly + GPT-5 Thinking
#
# 資料夾結構（本機或 Streamlit Cloud 均適用）：
#   Cmedicine_class_app.py
#   Cmedicine_class_app.xlsx
#   photos/
#       1.jpg
#       2.jpg
#       ...
#
# Excel/CSV 欄位允許（任一稱呼即可）：
#   名稱欄: name / 名稱 / 藥名 / 品項
#   圖片欄: filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔
#   分類欄: category / 分類 / 類別 / 功效分類 / 藥性分類
#
# 流程：
#   - 顯示圖片
#   - 學生選該圖片的「分類」
#   - 按「送出答案」檢查 → 再按「下一題」
#   - 做完後顯示總分，可重新開始

import streamlit as st
import pandas as pd
import random
import os

# ===================== 套件檢查 =====================
try:
    import openpyxl  # 讀 .xlsx
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl 套件，無法讀取 Excel 題庫。\n\n"
        "📦 請確認 requirements.txt 內容包含：\n"
        "    streamlit\n    pandas\n    openpyxl\n    xlrd\n\n"
        "或在本機執行： pip install openpyxl"
    )
    st.stop()

try:
    import xlrd  # 讀 .xls
except ImportError:
    xlrd = None

# ===================== 可調參數 =====================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
NUM_OPTIONS = 4

st.set_page_config(
    page_title="中藥圖像分類小測驗",
    page_icon="🌿",
    layout="centered",
)

# ===================== 載入題庫 =====================

def safe_load_table(path: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        st.error(f"❌ 找不到題庫檔案：{path}\n請確認與 Cmedicine_class_app.py 同層。")
        st.stop()

    _, ext = os.path.splitext(path)
    ext = ext.lower()

    try:
        if ext == ".xlsx":
            return pd.read_excel(path, engine="openpyxl")
        elif ext == ".xls" and xlrd is not None:
            return pd.read_excel(path, engine="xlrd")
        elif ext == ".csv":
            return pd.read_csv(path)
        else:
            # 若副檔名不明，依序嘗試三種
            try:
                return pd.read_excel(path, engine="openpyxl")
            except Exception:
                pass
            if xlrd is not None:
                try:
                    return pd.read_excel(path, engine="xlrd")
                except Exception:
                    pass
            return pd.read_csv(path)
    except Exception as e:
        st.error(f"❌ 題庫載入失敗：{e}")
        st.stop()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map_candidates = {
        "name": ["name", "名稱", "藥名", "品項"],
        "filename": ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"],
        "category": ["category", "分類", "類別", "功效分類", "藥性分類"],
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
            f"❌ 題庫欄位對不到：{', '.join(missing)}\n\n"
            "允許名稱：\n"
            "  名稱欄: name / 名稱 / 藥名 / 品項\n"
            "  圖片欄: filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔\n"
            "  分類欄: category / 分類 / 類別 / 功效分類 / 藥性分類"
        )
        st.stop()

    return pd.DataFrame({
        "name": df[col_map["name"]].astype(str).str.strip(),
        "filename": df[col_map["filename"]].astype(str).str.strip(),
        "category": df[col_map["category"]].astype(str).str.strip(),
    })


def load_question_bank():
    df_raw = safe_load_table(EXCEL_PATH)
    df = normalize_columns(df_raw)

    bank = []
    for _, row in df.iterrows():
        item_name, filename, category = row["name"], row["filename"], row["category"]
        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.isfile(img_path):
            st.warning(f"⚠ 找不到圖片檔：{img_path}")
        bank.append({"name": item_name, "filename": filename, "category": category})

    if not bank:
        st.error("❌ 題庫是空的，請確認 Excel 內有資料。")
        st.stop()

    return bank

# ===================== 狀態控制 =====================

def init_session_state(bank):
    random.shuffle(bank)
    st.session_state.questions = bank
    st.session_state.total = len(bank)
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.submitted = False
    st.session_state.selected = None
    st.session_state.finished = False
    st.session_state.options_cache = {}

def get_current_question():
    return st.session_state.questions[st.session_state.index]

def get_all_categories(bank):
    return sorted(set(q["category"] for q in bank))

def build_options(correct_cat, all_cats, k=4):
    distractors = [c for c in all_cats if c != correct_cat]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct_cat]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

# ===================== UI 元件 =====================

def render_progress_card():
    cur = st.session_state.index + 1
    total = st.session_state.total
    pct = (cur / total) * 100
    score = st.session_state.score

    st.markdown(
        f"""
        <div style='border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.08);
        padding:12px 16px;background:linear-gradient(to right,#f8f9fa,#ffffff);
        border:1px solid rgba(0,0,0,0.05);margin-bottom:12px;'>
        <b>進度</b> {cur}/{total}（{pct:.0f}%）
        <br>目前得分：<b>{score}</b>
        <div style='margin-top:8px;height:8px;width:100%;background:#e9ecef;border-radius:4px;'>
        <div style='height:100%;width:{pct}%;background:#74c69d;'></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )

def render_final_screen():
    score, total = st.session_state.score, st.session_state.total
    st.success(f"測驗完成！總得分：{score} / {total}")
    if st.button("重新開始", use_container_width=True):
        init_session_state(st.session_state.questions)

# ===================== 主流程 =====================

bank = load_question_bank()
if "questions" not in st.session_state:
    init_session_state(bank)

if st.session_state.finished:
    st.title("🌿 中藥圖像分類小測驗")
    render_final_screen()
    st.stop()

q = get_current_question()
all_categories = get_all_categories(bank)

qid = f"q{st.session_state.index}"
if qid not in st.session_state.options_cache:
    st.session_state.options_cache[qid] = build_options(
        q["category"], all_categories, NUM_OPTIONS
    )
options = st.session_state.options_cache[qid]

# ===================== 畫面 =====================

st.title("🌿 中藥圖像分類小測驗")
render_progress_card()

st.markdown(f"**Q{st.session_state.index + 1}. 這個屬於哪一類？**")
img_path = os.path.join(IMAGE_DIR, q["filename"])
st.image(img_path, caption=f"{q['name']}（{q['filename']}）", use_column_width=True)

if st.session_state.selected not in options:
    st.session_state.selected = None

st.session_state.selected = st.radio(
    "選擇分類：", options,
    index=options.index(st.session_state.selected)
    if st.session_state.selected in options else None,
    label_visibility="collapsed",
)

if st.session_state.submitted:
    if st.session_state.selected == q["category"]:
        st.markdown(f"<span style='color:#2f9e44;font-weight:600;'>✔ 答對！</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color:#d00000;font-weight:600;'>✘ 答錯</span> 正確分類：**{q['category']}**", unsafe_allow_html=True)
    st.caption(f"這張圖是：{q['name']}")

button_label = "送出答案" if not st.session_state.submitted else "下一題"
if st.button(button_label, use_container_width=True):
    if not st.session_state.submitted:
        st.session_state.submitted = True
        if st.session_state.selected == q["category"]:
            st.session_state.score += 1
    else:
        st.session_state.index += 1
        st.session_state.submitted = False
        st.session_state.selected = None
        if st.session_state.index >= st.session_state.total:
            st.session_state.finished = True

if st.session_state.finished:
    render_final_screen()
