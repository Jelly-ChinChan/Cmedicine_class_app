# Cmedicine_class_app.py
# 中藥圖像→藥名選擇測驗（統一300x300底部裁切、即時解析）

import streamlit as st
import pandas as pd
import random
import os

# Pillow 縮圖與裁切
try:
    from PIL import Image
except ImportError:
    Image = None

# openpyxl 讀 Excel
try:
    import openpyxl  # noqa
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl 套件，無法讀取 Excel 題庫。\n\n"
        "請在 requirements.txt 中加入：\n"
        "streamlit\npandas\nopenpyxl\npillow"
    )
    st.stop()

# ================= 設定 =================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 300  # 統一圖片大小（300x300）
NUM_OPTIONS = 4   # 每題選項數量（正解1 + 干擾3）

st.set_page_config(page_title="中藥圖像測驗", page_icon="🌿", layout="centered")

# ================= 題庫載入 =================
def load_question_bank():
    """從 Excel 載入題庫"""
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到 Excel 題庫。請確認 Cmedicine_class_app.xlsx 與程式在同一層。")
        st.stop()

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

    # 對應欄位名稱
    name_col, file_col = None, None
    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name", "名稱", "藥名", "品項"]:
            name_col = c
        elif cname in ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"]:
            file_col = c

    if not name_col or not file_col:
        st.error("❌ Excel 缺少『藥名(name)』或『圖片檔名(filename)』欄位。")
        st.stop()

    df = df.dropna(subset=[name_col, file_col])
    bank = []
    for _, row in df.iterrows():
        bank.append({
            "name": str(row[name_col]).strip(),
            "filename": str(row[file_col]).strip()
        })

    if not bank:
        st.error("❌ 題庫為空。請確認 Excel 內有資料。")
        st.stop()
    return bank

bank = load_question_bank()

# ================= 初始化狀態 =================
if "questions" not in st.session_state:
    random.shuffle(bank)
    st.session_state.questions = bank
if "options_cache" not in st.session_state:
    st.session_state.options_cache = {}

questions = st.session_state.questions
all_names = [q["name"] for q in questions]

# ================= 工具函式 =================
def build_options(correct_name, all_names, k=4):
    """建立四個選項（正解 + 3個干擾）"""
    distractors = [n for n in all_names if n != correct_name]
    random.shuffle(distractors)
    opts = distractors[:max(0, k - 1)] + [correct_name]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

def render_square_image(path):
    """裁切為正方形（以底部為基準）並統一大小"""
    if not os.path.isfile(path):
        st.warning(f"⚠ 找不到圖片檔案：{path}")
        return

    try:
        img = Image.open(path)
        w, h = img.size

        # 高圖 -> 從上裁切，保留底部
        if h > w:
            top_crop = h - w
            img = img.crop((0, top_crop, w, h))
        # 寬圖 -> 置中裁切
        elif w > h:
            left_crop = (w - h) // 2
            img = img.crop((left_crop, 0, left_crop + h, h))

        # 統一成300x300
        img = img.resize((FIXED_SIZE, FIXED_SIZE))
        st.image(img)
    except Exception:
        st.image(path, width=FIXED_SIZE)

# ================= 計算即時得分 =================
score_now = 0
answered = 0
for idx, q in enumerate(questions):
    key = f"ans_{idx}"
    val = st.session_state.get(key)
    if val is not None:
        answered += 1
        if val == q["name"]:
            score_now += 1

total_q = len(questions)
progress = answered / total_q if total_q > 0 else 0

# ================= 進度條 =================
st.markdown(
    f"""
    <div style='border-radius:16px;
                box-shadow:0 4px 12px rgba(0,0,0,0.08);
                padding:16px;
                background:#ffffff;
                border:1px solid rgba(0,0,0,0.07);
                margin-bottom:16px;'>
        <div style='font-weight:600; font-size:16px; margin-bottom:4px;'>
            進度 {answered}/{total_q}（{progress*100:.0f}%）
        </div>
        <div style='font-size:14px; color:#444; margin-bottom:8px;'>
            目前得分：<b>{score_now}</b>
        </div>
        <div style='height:8px; width:100%;
                    background:#e9ecef;
                    border-radius:4px;
                    overflow:hidden;'>
            <div style='height:8px;
                        width:{progress*100}%;
                        background:#74c69d;'>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ================= 主體內容 =================
for idx, q in enumerate(questions):
    st.markdown(f"**Q{idx+1}. 這個中藥的名稱是？**")
    img_path = os.path.join(IMAGE_DIR, q["filename"])
    render_square_image(img_path)

    # 四選項（固定亂序）
    key_opts = f"opts_{idx}"
    if key_opts not in st.session_state.options_cache:
        st.session_state.options_cache[key_opts] = build_options(q["name"], all_names, NUM_OPTIONS)
    options = st.session_state.options_cache[key_opts]

    key_ans = f"ans_{idx}"
    selected = st.radio("選項：", options, index=None, label_visibility="collapsed", key=key_ans)

    # 顯示解析
    if selected is not None:
        if selected == q["name"]:
            st.markdown(
                "<div style='color:#2f9e44; font-weight:600;'>解析：✔ 答對！</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='color:#d00000; font-weight:600;'>解析：✘ 答錯，正確答案是「{q['name']}」。</div>",
                unsafe_allow_html=True
            )

    st.markdown("<hr style='border:0;border-top:1px solid rgba(0,0,0,0.08);margin:20px 0;' />", unsafe_allow_html=True)
