# Cmedicine_class_app.py —— 圖片↔中文分類 測驗 App
# Author: Jelly + GPT-5 Thinking
#
# 專案結構（本機 / Streamlit Cloud 相同）：
#   Cmedicine_class_app.py
#   Cmedicine_class_app.xlsx
#   photos/
#       1.jpg
#       2.jpg
#       ...
#   requirements.txt  (內容建議: streamlit, pandas, openpyxl, xlrd, pillow)
#
# 欄位命名可用：
#   名稱欄: name / 名稱 / 藥名 / 品項
#   圖片欄: filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔
#   分類欄: category / 分類 / 類別 / 功效分類 / 藥性分類
#
# 遊戲流程：
#   - 顯示圖片（縮成原始大小的 1/4）
#   - 給 4 個選項（包含正確分類 + 干擾選項）
#   - 「送出答案」→顯示對錯
#   - 「下一題」→下一題
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
        "    streamlit\n    pandas\n    openpyxl\n    xlrd\n    pillow\n\n"
        "或在本機執行： pip install openpyxl pillow xlrd"
    )
    st.stop()

try:
    import xlrd  # 讀 .xls
except ImportError:
    xlrd = None

# Pillow（用來縮圖到 1/4 尺寸）
try:
    from PIL import Image
except ImportError:
    Image = None  # 沒裝 pillow 時我們會退回用 width=300 的方式顯示


# ===================== 可調參數 =====================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"

NUM_OPTIONS = 4           # 每題要出的選項數上限（含正解）。盡量湊到 4。
IMAGE_SCALE = 0.25        # 圖片縮小比例：1/4

st.set_page_config(
    page_title="中藥圖像分類小測驗",
    page_icon="🌿",
    layout="centered",
)

# ===================== 載入題庫 =====================

def safe_load_table(path: str) -> pd.DataFrame:
    """讀取題庫檔案（.xlsx / .xls / .csv），回傳 DataFrame"""
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
            # 副檔名不明時，依序試三種常見格式
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
    """
    對應欄位名稱成固定三欄：
      name      -> 藥名
      filename  -> 圖片檔名 (ex: 1.jpg)
      category  -> 分類 (ex: 補氣藥)
    """
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
    """讀題庫→標準化欄位→建題目list，並檢查圖片存在性"""
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
    """初始化整個測驗狀態"""
    random.shuffle(bank)
    st.session_state.questions = bank
    st.session_state.total = len(bank)
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.submitted = False     # 這題是否已按「送出答案」
    st.session_state.selected = None       # 目前 radio 的選擇
    st.session_state.finished = False      # 是否整份做完
    st.session_state.options_cache = {}    # 每題選項固定

def get_current_question():
    return st.session_state.questions[st.session_state.index]

def get_all_categories(bank):
    """回傳所有出現過的分類（不重複）"""
    return sorted(set(q["category"] for q in bank))

def build_options(correct_cat, all_cats, k=4):
    """
    產生選項列表：
    - 包含正確分類
    - 加入隨機干擾(不同分類)
    - 打亂順序
    想要 4 個選項（k=4），如果分類不夠多就用能湊到的。
    """
    distractors = [c for c in all_cats if c != correct_cat]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct_cat]
    # 去重後打亂
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

# ===================== UI 元件 =====================

def render_progress_card():
    """顯示進度條 / 得分"""
    cur = st.session_state.index + 1
    total = st.session_state.total
    pct = (cur / total) * 100
    score = st.session_state.score

    st.markdown(
        f"""
        <div style='border-radius:16px;
                    box-shadow:0 4px 12px rgba(0,0,0,0.08);
                    padding:16px;
                    background:#ffffff;
                    border:1px solid rgba(0,0,0,0.07);
                    margin-bottom:16px;'>
            <div style='font-weight:600; font-size:16px; margin-bottom:4px;'>
                進度 {cur}/{total} （{pct:.0f}%）
            </div>
            <div style='font-size:14px; color:#444; margin-bottom:8px;'>
                目前得分：<b>{score}</b>
            </div>
            <div style='height:8px; width:100%;
                        background:#e9ecef;
                        border-radius:4px;
                        overflow:hidden;'>
                <div style='height:8px;
                            width:{pct}%;
                            background:#74c69d;'>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_final_screen():
    """全部題目做完後的總成績 + 重新開始"""
    score, total = st.session_state.score, st.session_state.total
    st.success(f"測驗完成！總得分：{score} / {total}")
    if st.button("重新開始", use_container_width=True):
        init_session_state(st.session_state.questions)

def render_question_image(img_path, caption_text):
    """
    顯示縮小後的圖片：
    - 如果 Pillow(PIL) 可用：讀進來，縮成 1/4 寬高後用 st.image 顯示
    - 如果 Pillow 沒安裝：fallback 用 st.image(..., width=300)
    """
    if not os.path.isfile(img_path):
        st.warning(f"⚠ 找不到圖片檔：{img_path}")
        return

    if Image is not None:
        try:
            img = Image.open(img_path)
            w, h = img.size
            new_size = (max(1, int(w * IMAGE_SCALE)), max(1, int(h * IMAGE_SCALE)))
            img_resized = img.resize(new_size)
            # 這裡不用 use_container_width，因為我們自己縮好了
            st.image(img_resized, caption=caption_text)
            return
        except Exception as e:
            st.warning(f"⚠ 圖片縮放失敗，改用備援顯示。詳細：{e}")

    # 備援：如果 Pillow 沒裝或縮圖失敗，就用固定寬度顯示
    st.image(
        img_path,
        caption=caption_text,
        width=300  # 大約佔螢幕寬的一小部分
    )

# ===================== 主流程 =====================

# 載入題庫並初始化狀態
bank = load_question_bank()
if "questions" not in st.session_state:
    init_session_state(bank)

# 如果已經整份做完 -> 顯示總結畫面
if st.session_state.finished:
    st.title("🌿 中藥圖像分類小測驗")
    render_final_screen()
    st.stop()

# 取得目前題目
q = get_current_question()
all_categories = get_all_categories(bank)

# 產生 / 取出本題選項（固定 4 個上限）
qid = f"q{st.session_state.index}"
if qid not in st.session_state.options_cache:
    st.session_state.options_cache[qid] = build_options(
        q["category"], all_categories, NUM_OPTIONS
    )
options = st.session_state.options_cache[qid]

# ===================== 畫面 =====================

st.title("🌿 中藥圖像分類小測驗")

render_progress_card()

# 題目文字
st.markdown(f"**Q{st.session_state.index + 1}. 這個屬於哪一類？**")

# 縮小後顯示圖片
img_path = os.path.join(IMAGE_DIR, q["filename"])
render_question_image(
    img_path,
    caption_text=f"{q['name']}（{q['filename']}）"
)

# Radio 單選
if st.session_state.selected not in options:
    st.session_state.selected = None

st.session_state.selected = st.radio(
    "選擇分類：",
    options,
    index=options.index(st.session_state.selected)
    if st.session_state.selected in options else None,
    label_visibility="collapsed",
)

# 如果已經按過「送出答案」，顯示對錯
if st.session_state.submitted:
    if st.session_state.selected == q["category"]:
        st.markdown(
            "<div style='color:#2f9e44; font-weight:600;'>✔ 答對！</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='color:#d00000; font-weight:600;'>✘ 答錯</div>"
            f"<div style='margin-top:4px;'>正確分類：<b>{q['category']}</b></div>",
            unsafe_allow_html=True
        )

    st.caption(f"這張圖是：{q['name']}")

# 單一主按鈕：送出答案 / 下一題
button_label = "送出答案" if not st.session_state.submitted else "下一題"
if st.button(button_label, use_container_width=True):
    if not st.session_state.submitted:
        # 第一次按：送出答案 -> 判分
        st.session_state.submitted = True
        if st.session_state.selected == q["category"]:
            st.session_state.score += 1
    else:
        # 第二次按：下一題
        st.session_state.index += 1
        st.session_state.submitted = False
        st.session_state.selected = None

        if st.session_state.index >= st.session_state.total:
            st.session_state.finished = True

# 如果剛剛按完就完成所有題目，直接顯示總結
if st.session_state.finished:
    render_final_screen()
