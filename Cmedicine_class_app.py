# Cmedicine_class_app.py —— 中藥圖像→藥名 選擇題
# 功能：
#   顯示圖片（縮小約 1/3 大小），提供 4 個選項（正確 name + 隨機3個干擾）
#   適用手機版顯示
#
# 檔案結構：
#   Cmedicine_class_app.py
#   Cmedicine_class_app.xlsx
#   photos/
#   requirements.txt（需含：streamlit pandas openpyxl pillow xlrd）

import streamlit as st
import pandas as pd
import random
import os

# Pillow for image resizing
try:
    from PIL import Image
except ImportError:
    Image = None

EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
IMAGE_SCALE = 0.33  # 圖片縮成約 1/3 尺寸
NUM_OPTIONS = 4     # 選項數量：正解 + 3干擾

st.set_page_config(page_title="中藥圖像分類小測驗", page_icon="🌿", layout="centered")

# ===================== 載入題庫 =====================
def load_question_bank():
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到 Excel 題庫，請確認檔案與程式同層。")
        st.stop()
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

    # 嘗試對應欄位
    col_name = None
    col_file = None
    col_cat = None
    for c in df.columns:
        if str(c).strip().lower() in ["name", "名稱", "藥名", "品項"]:
            col_name = c
        elif str(c).strip().lower() in ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"]:
            col_file = c
        elif str(c).strip().lower() in ["category", "分類", "類別", "功效分類", "藥性分類"]:
            col_cat = c
    if not col_name or not col_file:
        st.error("❌ Excel 必須至少包含『藥名(name)』與『圖片檔名(filename)』欄位。")
        st.stop()

    df = df.dropna(subset=[col_name, col_file])
    bank = []
    for _, row in df.iterrows():
        bank.append({
            "name": str(row[col_name]).strip(),
            "filename": str(row[col_file]).strip(),
            "category": str(row[col_cat]).strip() if col_cat else ""
        })
    return bank

bank = load_question_bank()

# ===================== 初始化狀態 =====================
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.submitted = False
    st.session_state.selected = None
    random.shuffle(bank)

# ===================== 工具函式 =====================
def build_name_options(correct_name, all_names, k=4):
    """從所有藥名中取正解 + 隨機干擾"""
    distractors = [n for n in all_names if n != correct_name]
    random.shuffle(distractors)
    opts = distractors[:max(0, k-1)] + [correct_name]
    random.shuffle(opts)
    return opts

def render_image(img_path, caption_text):
    """顯示縮小後圖片（自動適應手機寬度）"""
    if not os.path.isfile(img_path):
        st.warning(f"⚠ 找不到圖片檔案：{img_path}")
        return
    if Image:
        try:
            img = Image.open(img_path)
            w, h = img.size
            new_size = (int(w * IMAGE_SCALE), int(h * IMAGE_SCALE))
            img = img.resize(new_size)
            st.image(img, caption=caption_text, use_container_width=True)
            return
        except Exception:
            pass
    st.image(img_path, caption=caption_text, use_container_width=True)

# ===================== 主畫面 =====================
st.title("🌿 中藥圖像分類小測驗")

progress = (st.session_state.index + 1) / len(bank)
st.progress(progress)
st.write(f"進度：{st.session_state.index + 1} / {len(bank)}　目前得分：{st.session_state.score}")

# 顯示題目
q = bank[st.session_state.index]
img_path = os.path.join(IMAGE_DIR, q["filename"])
render_image(img_path, caption_text=f"{q['name']}（{q['filename']}）")

# 建立4個選項（正確 name + 隨機3個）
all_names = [b["name"] for b in bank]
options = build_name_options(q["name"], all_names, NUM_OPTIONS)

# 顯示題目
st.markdown(f"**Q{st.session_state.index + 1}. 這個中藥的名稱是？**")
st.session_state.selected = st.radio("選項：", options, index=None, label_visibility="collapsed")

# ===================== 判斷與按鈕 =====================
btn_label = "送出答案" if not st.session_state.submitted else "下一題"

if st.button(btn_label, use_container_width=True):
    if not st.session_state.submitted:
        # 第一次按 → 判分
        if st.session_state.selected == q["name"]:
            st.session_state.score += 1
            st.success(f"✔ 答對！正確答案：{q['name']}")
        else:
            st.error(f"✘ 答錯，正確答案是：{q['name']}")
        st.session_state.submitted = True
    else:
        # 下一題
        st.session_state.index += 1
        st.session_state.submitted = False
        st.session_state.selected = None
        if st.session_state.index >= len(bank):
            st.success(f"🎉 全部完成！總得分：{st.session_state.score} / {len(bank)}")
            st.balloons()
            st.session_state.index = 0
            st.session_state.score = 0
