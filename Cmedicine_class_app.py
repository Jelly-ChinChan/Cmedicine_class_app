# Cmedicine_class_app.py —— 中藥圖像分類小測驗（完整版）
# 功能：
#  - 模式三為主：給藥名 → 選正確圖片（2×2）
#  - 手機版強制兩欄顯示
#  - 點圖片即作答，立即顯示解析
#  - 錯題回顧無外框、簡潔呈現

import streamlit as st
import pandas as pd
import random, os
from PIL import Image
import io, base64

# ======================== 基本設定 ========================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
IMAGE_SIZE = 200

st.set_page_config(page_title="中藥圖像測驗", page_icon="🌿", layout="centered")

# ======================== CSS 修正手機 2x2 ========================
st.markdown("""
<style>
[data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 0.75rem !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"] {
  flex: 0 0 calc(50% - 0.75rem) !important;
  width: calc(50% - 0.75rem) !important;
  max-width: calc(50% - 0.75rem) !important;
}
@media (max-width: 768px) {
  [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 0 0 calc(50% - 0.75rem) !important;
    width: calc(50% - 0.75rem) !important;
  }
}
.img-card {
  display: inline-block;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# ======================== 題庫載入 ========================
def load_question_bank():
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    name_col, file_col = None, None
    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name", "名稱", "藥名"]:
            name_col = c
        elif cname in ["filename", "圖片檔名", "檔名"]:
            file_col = c
    if not name_col or not file_col:
        st.error("Excel 必須有「名稱 / 圖片檔名」欄位")
        st.stop()
    return [{"name": str(r[name_col]), "filename": str(r[file_col])} for _, r in df.iterrows()]

# ======================== 圖片處理 ========================
def crop_square_bottom(img, size=IMAGE_SIZE):
    w, h = img.size
    if h > w: img = img.crop((0, h - w, w, h))
    elif w > h: img = img.crop(((w - h)//2, 0, (w - h)//2 + h, h))
    return img.resize((size, size))

def image_to_base64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def render_img(path, border=None):
    if not os.path.exists(path): return
    img = crop_square_bottom(Image.open(path))
    b64 = image_to_base64(img)
    border_style = f"border:4px solid {border};" if border else "border:4px solid transparent;"
    st.markdown(f"""
    <div class="img-card" style="{border_style}">
        <img src="data:image/png;base64,{b64}" width="{IMAGE_SIZE}">
    </div>
    """, unsafe_allow_html=True)

# ======================== 主程式 ========================
bank = load_question_bank()
filename_to_name = {b["filename"]: b["name"] for b in bank}
questions = random.sample(bank, min(10, len(bank)))
score, done = 0, 0

st.markdown("### 🔬 點擊圖片選出正確的中藥")

for i, q in enumerate(questions):
    st.markdown(f"**Q{i+1}. {q['name']}**")

    # 四個隨機選項（1 正確 + 3 干擾）
    all_files = [b["filename"] for b in bank]
    opts = random.sample([f for f in all_files if f != q["filename"]], 3) + [q["filename"]]
    random.shuffle(opts)

    rows = [opts[:2], opts[2:]]
    ans_key = f"ans_{i}"
    chosen = st.session_state.get(ans_key)

    for row in rows:
        cols = st.columns(2)
        for j, opt in enumerate(row):
            img_path = os.path.join(IMAGE_DIR, opt)
            with cols[j]:
                btn_key = f"btn_{i}_{j}"
                if st.button("", key=btn_key):
                    st.session_state[ans_key] = opt
                    chosen = opt

                border = None
                if chosen:
                    if opt == q["filename"]:
                        border = "#2f9e44"
                    if opt == chosen and chosen != q["filename"]:
                        border = "#d00000"

                render_img(img_path, border)

                # 答案顯示
                if chosen == opt:
                    if chosen == q["filename"]:
                        st.markdown("<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>", unsafe_allow_html=True)
                    else:
                        cname = filename_to_name.get(chosen, "未知")
                        st.markdown(f"<div style='color:#d00000;font-weight:600;'>✘ 答錯<br>此為：{cname}</div>", unsafe_allow_html=True)
                        st.session_state.setdefault("wrong", []).append({
                            "question": q["name"],
                            "correct": q["name"],
                            "chosen_name": cname,
                            "img": chosen
                        })
    st.markdown("<hr/>", unsafe_allow_html=True)

    if chosen:
        done += 1
        if chosen == q["filename"]:
            score += 1

# ======================== 結果進度條 ========================
if done:
    progress = done / len(questions)
    st.markdown(f"""
    <div style='margin-top:16px;border:1px solid #ccc;border-radius:8px;padding:10px;'>
        <b>進度：</b>{done}/{len(questions)}（{progress*100:.0f}%）
        <b>得分：</b>{score}
        <div style='height:8px;background:#eee;border-radius:4px;margin-top:4px;'>
            <div style='height:8px;background:#74c69d;width:{progress*100}%'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ======================== 錯題回顧 ========================
if "wrong" in st.session_state and st.session_state["wrong"]:
    st.markdown("## 🔁 錯題回顧")
    for miss in st.session_state["wrong"]:
        st.markdown(f"""
        <div style='font-size:15px;font-weight:600;color:#d00000;'>✘ 曾經答錯</div>
        <div style='font-size:14px;line-height:1.4;margin-bottom:8px;'>
            <b>題目：</b>{miss["question"]}<br>
            <b>正確：</b>{miss["correct"]}<br>
            <b>你當時選了：</b>{miss["chosen_name"]}
        </div>
        """, unsafe_allow_html=True)
        img_path = os.path.join(IMAGE_DIR, miss["img"])
        render_img(img_path, border="#d00000")
