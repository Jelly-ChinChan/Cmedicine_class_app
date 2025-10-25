# Cmedicine_class_app.py
# 三模式中藥測驗（+ 錯題回顧）
#   1. 全部題目（看圖選藥名）
#   2. 隨機10題測驗
#   3. 圖片選擇模式（1x2）：兩張圖並列，按圖下方按鈕作答，紅綠框回饋
#
# 2025-10-25 版本修正：
#   ✅ 修正 mode_is_3 錯誤
#   ✅ 修正 /tmp 儲存錯誤
#   ✅ 手機上「選左邊」「選右邊」按鈕對齊圖片正下方

import streamlit as st
import pandas as pd
import random
import os

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

# ================= 基本設定 =================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 300
NUM_OPTIONS = 4
DEFAULT_MODE = "全部題目"

# 模式3設定
TILE_SIZE = 160
TMP_DIR = os.path.join(os.getcwd(), "temp_images")
os.makedirs(TMP_DIR, exist_ok=True)

st.set_page_config(page_title="中藥圖像測驗", page_icon="🌿", layout="centered")

# ================= 全域樣式 =================
st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
.block-container {padding-top: 1rem; max-width: 700px;}
.img-card {
    display: inline-block; border-radius: 8px; overflow: hidden;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 0.25rem; border:4px solid transparent;
}
.mode-banner-box {
    background:#f1f3f5; border:1px solid #dee2e6; border-radius:6px;
    padding:8px 12px; font-size:0.9rem; font-weight:600; display:inline-block; margin-top:0.5rem;
}
.opt-result-correct {color:#2f9e44;font-weight:600;margin:8px 0;}
.opt-result-wrong {color:#d00000;font-weight:600;margin:8px 0;}
hr {border:none;border-top:1px solid #dee2e6;}
button[kind="primary"] {width:95%;margin-top:6px;}
</style>
""", unsafe_allow_html=True)

# ================= 題庫載入 =================
def load_question_bank():
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到 Excel 題庫，請確認檔案存在。")
        st.stop()

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    name_col, file_col = None, None
    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name", "名稱", "藥名", "品項"]:
            name_col = c
        elif cname in ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"]:
            file_col = c

    if not name_col or not file_col:
        st.error("❌ Excel 必須包含「名稱/圖片檔名」欄位。")
        st.stop()

    df = df.dropna(subset=[name_col, file_col])
    bank = [{"name": str(r[name_col]).strip(), "filename": str(r[file_col]).strip()} for _, r in df.iterrows()]
    return bank

# ================= 工具 =================
def crop_square_bottom(img, size=300):
    w, h = img.size
    if h > w:
        img = img.crop((0, h - w, w, h))
    elif w > h:
        left = (w - h) // 2
        img = img.crop((left, 0, left + h, h))
    return img.resize((size, size))

def render_img_card(path, size=300, border_color=None):
    if not os.path.isfile(path):
        st.warning(f"⚠ 找不到圖片：{path}")
        return
    try:
        img = Image.open(path)
        img = crop_square_bottom(img, size)
        import io, base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        border_css = f"border:4px solid {border_color};" if border_color else "border:4px solid transparent;"
        st.markdown(f"<div class='img-card' style='{border_css}'><img src='data:image/png;base64,{b64}' width='{size}'></div>", unsafe_allow_html=True)
    except Exception:
        st.image(path, width=size)

def build_options(correct, pool, k=4):
    opts = [p for p in pool if p != correct]
    random.shuffle(opts)
    opts = opts[:k-1] + [correct]
    random.shuffle(opts)
    return opts

def init_mode(bank, mode):
    if mode == "隨機10題測驗" or mode == "圖片選擇模式（1x2）":
        qset = random.sample(bank, min(10, len(bank)))
    else:
        qset = bank[:]
    random.shuffle(qset)
    st.session_state.mode = mode
    st.session_state.questions = qset
    st.session_state.opts_cache = {}
    st.session_state.wrong_answers = []
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

# ================= 初始化 =================
bank = load_question_bank()
filename_to_name = {x["filename"]: x["name"] for x in bank}
if "mode" not in st.session_state: st.session_state.mode = DEFAULT_MODE
if "questions" not in st.session_state: init_mode(bank, st.session_state.mode)
if "wrong_answers" not in st.session_state: st.session_state.wrong_answers = []

# ================= 模式選擇 =================
st.markdown("### 🌿 模式選擇")
selected_mode = st.radio("請選擇測驗模式", ["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"],
                         index=["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"].index(st.session_state.mode))
if selected_mode != st.session_state.mode:
    init_mode(bank, selected_mode)
questions = st.session_state.questions

# 緩存選項
for i, q in enumerate(questions):
    key = f"opts_{i}"
    if key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            st.session_state.opts_cache[key] = build_options(q["name"], [x["name"] for x in bank])
        else:
            cand = build_options(q["filename"], [x["filename"] for x in bank], k=2)
            while len(cand) < 2:
                extra = random.choice([x["filename"] for x in bank])
                if extra not in cand: cand.append(extra)
            st.session_state.opts_cache[key] = cand[:2]

st.markdown(f"<div class='mode-banner-box'>目前模式：{st.session_state.mode}</div>", unsafe_allow_html=True)

# ================= 模式1/2 =================
if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
    score = done = 0
    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR, q["filename"]), size=FIXED_SIZE)
        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        st.radio("選項", opts, key=ans_key, label_visibility="collapsed")
        chosen = st.session_state[ans_key]
        done += 1
        if chosen == q["name"]:
            score += 1
            st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是「{q['name']}」</div>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"<div>進度：{done}/{len(questions)}　|　答對：{score}</div>", unsafe_allow_html=True)

# ================= 模式3：圖片選擇（1x2） =================
elif st.session_state.mode == "圖片選擇模式（1x2）":
    score = done = 0

    # 🔧 圖片放大尺寸
    TILE_SIZE = 200   # ← 可改 180~200 視你手機螢幕寬度
    GAP = 8
    COMBO_W = TILE_SIZE * 2 + GAP

    # CSS 調整：圖片外框靠齊兩側
    st.markdown("""
    <style>
    .combo-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin: 0 auto;
    }
    .stImage img {
        display: block;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)

    def make_square_tile(path):
        if os.path.exists(path) and Image is not None:
            try:
                return crop_square_bottom(Image.open(path), TILE_SIZE)
            except Exception:
                pass
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), (240, 240, 240))

    def compose_combo(left_tile, right_tile, hl_left=None, hl_right=None):
        combo = Image.new("RGB", (COMBO_W, TILE_SIZE), "white")
        combo.paste(left_tile, (0, 0))
        combo.paste(right_tile, (TILE_SIZE + GAP, 0))
        draw = ImageDraw.Draw(combo)
        def draw_border(x, color): draw.rectangle([x+3, 3, x+TILE_SIZE-4, TILE_SIZE-4], outline=color, width=4)
        if hl_left == "correct": draw_border(0, (47,158,68))
        elif hl_left == "wrong": draw_border(0, (208,0,0))
        if hl_right == "correct": draw_border(TILE_SIZE+GAP, (47,158,68))
        elif hl_right == "wrong": draw_border(TILE_SIZE+GAP, (208,0,0))
        return combo

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]
        left, right = opts[0], opts[1]
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key)
        correct = q["filename"]

        left_tile = make_square_tile(os.path.join(IMAGE_DIR, left))
        right_tile = make_square_tile(os.path.join(IMAGE_DIR, right))

        hl_left = hl_right = None
        if chosen:
            if chosen == left:
                hl_left = "correct" if left == correct else "wrong"
                if left != correct and right == correct: hl_right = "correct"
            elif chosen == right:
                hl_right = "correct" if right == correct else "wrong"
                if right != correct and left == correct: hl_left = "correct"

        combo = compose_combo(left_tile, right_tile, hl_left, hl_right)
        combo_path = os.path.join(TMP_DIR, f"combo_{i}.png")
        combo.save(combo_path)

        # ✅ 外層加 div 包裝，讓圖片整體靠齊按鈕區
        st.markdown("<div class='combo-wrapper'>", unsafe_allow_html=True)
        st.image(combo_path, width=COMBO_W)
        st.markdown("</div>", unsafe_allow_html=True)

        # ✅ 改用 columns，讓左右按鈕正好對齊
        col1, col2 = st.columns(2)
        with col1:
            if st.button("選左邊", key=f"left_{i}", use_container_width=True):
                st.session_state[ans_key] = left
                st.rerun()
        with col2:
            if st.button("選右邊", key=f"right_{i}", use_container_width=True):
                st.session_state[ans_key] = right
                st.rerun()

        # 回饋區
        if chosen:
            if chosen == correct:
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                wrong_name = filename_to_name.get(chosen, "未知")
                st.markdown(f"<div class='opt-result-wrong'>✘ 錯誤，此為：{wrong_name}</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)
        done += 1
        if chosen == correct: score += 1

    st.markdown(f"<div>進度：{done}/{len(questions)}　|　答對：{score}</div>", unsafe_allow_html=True)

# ================= 錯題回顧 =================
if st.session_state.wrong_answers:
    st.markdown("### ❌ 錯題回顧")
    for miss in st.session_state.wrong_answers:
        render_img_card(os.path.join(IMAGE_DIR, miss["img"]), size=140)
        st.markdown(f"- 題目：{miss['question']}  \n- 正解：**{miss['correct']}**  \n- 你選了：{miss['chosen_name']}")
        st.markdown("<hr/>", unsafe_allow_html=True)

# ================= 重新開始 =================
st.markdown("---")
if st.button("🔄 重新開始本模式"):
    init_mode(bank, st.session_state.mode)
    st.rerun()
