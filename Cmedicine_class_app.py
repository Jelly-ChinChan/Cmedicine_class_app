# Cmedicine_class_app.py
# Cloud‑safe complete version with “請選擇” default option (no auto‑answer)

import streamlit as st
import pandas as pd
import random
import os
import io
import base64

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 300
DEFAULT_MODE = "全部題目"

TILE_SIZE = 160
TMP_DIR = os.path.join(os.getcwd(), "temp_images")
os.makedirs(TMP_DIR, exist_ok=True)

st.set_page_config(page_title="中藥圖像測驗", page_icon="🌿", layout="centered")

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

def load_question_bank():
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    name_col, file_col = None, None
    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name","名稱","藥名"]:
            name_col = c
        elif cname in ["filename","圖片檔名","檔名","file"]:
            file_col = c
    df = df.dropna(subset=[name_col, file_col])
    return [{"name":str(r[name_col]).strip(),"filename":str(r[file_col]).strip()} for _,r in df.iterrows()]

def crop_square_bottom(img, size=300):
    w,h = img.size
    if h > w:
        img = img.crop((0, h-w, w, h))
    elif w > h:
        left = (w-h)//2
        img = img.crop((left,0,left+h,h))
    return img.resize((size,size))

def render_img_card(path, size=300, border_color=None):
    img = Image.open(path)
    img = crop_square_bottom(img,size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    border_css = f"border:4px solid {border_color};" if border_color else "border:4px solid transparent;"
    st.markdown(f"<div class='img-card' style='{border_css}'><img src='data:image/png;base64,{b64}' width='{size}'></div>", unsafe_allow_html=True)

def build_options(correct, pool, k=4):
    opts=[p for p in pool if p!=correct]
    random.shuffle(opts)
    opts=opts[:k-1]+[correct]
    random.shuffle(opts)
    return opts

def init_mode(bank, mode):
    q = random.sample(bank, min(10,len(bank))) if mode!="全部題目" else bank[:]
    random.shuffle(q)
    st.session_state.mode = mode
    st.session_state.questions = q
    st.session_state.opts_cache = {}
    for k in list(st.session_state.keys()):
        if "_ans_" in k:
            del st.session_state[k]

bank = load_question_bank()
filename_to_name = {x["filename"]:x["name"] for x in bank}

if "mode" not in st.session_state:
    init_mode(bank, DEFAULT_MODE)
questions = st.session_state.questions

st.markdown("### 🌿 模式選擇")
selected_mode = st.radio("請選擇測驗模式",
                         ["全部題目","隨機10題測驗","圖片選擇模式（1x2）"],
                         index=["全部題目","隨機10題測驗","圖片選擇模式（1x2）"].index(st.session_state.mode))

if selected_mode != st.session_state.mode:
    init_mode(bank, selected_mode)

questions = st.session_state.questions

for i,q in enumerate(questions):
    key = f"opts_{st.session_state.mode}_{i}"
    if key not in st.session_state.opts_cache:
        if st.session_state.mode!="圖片選擇模式（1x2）":
            st.session_state.opts_cache[key] = build_options(q["name"], [x["name"] for x in bank])
        else:
            cand=build_options(q["filename"],[x["filename"] for x in bank],k=2)
            st.session_state.opts_cache[key]=cand[:2]

st.markdown(f"<div class='mode-banner-box'>目前模式：{st.session_state.mode}</div>", unsafe_allow_html=True)

# MODE 1–2
if st.session_state.mode!="圖片選擇模式（1x2）":
    score=0
    for i,q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR,q["filename"]), size=FIXED_SIZE)

        opts = st.session_state.opts_cache[f"opts_{st.session_state.mode}_{i}"]
        ans_key = f"{st.session_state.mode}_ans_{i}"

        display_opts = ["請選擇"] + opts
        raw_choice = st.radio("選項", display_opts, key=ans_key, label_visibility="collapsed")
        chosen = raw_choice if raw_choice!="請選擇" else None

        if chosen:
            if chosen==q["name"]:
                score+=1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是「{q['name']}」</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"<div>答對：{score}/{len(questions)}</div>", unsafe_allow_html=True)

# MODE 3
else:
    score=0
    TILE_SIZE=200
    GAP=8
    COMBO_W=TILE_SIZE*2+GAP

    def make_tile(path):
        try:
            return crop_square_bottom(Image.open(path),TILE_SIZE)
        except:
            return Image.new("RGB",(TILE_SIZE,TILE_SIZE),(240,240,240))

    def compose(left,right,hl_left=None,hl_right=None):
        combo=Image.new("RGB",(COMBO_W,TILE_SIZE),"white")
        combo.paste(left,(0,0))
        combo.paste(right,(TILE_SIZE+GAP,0))
        draw=ImageDraw.Draw(combo)
        def bd(x,c): draw.rectangle([x+3,3,x+TILE_SIZE-4,TILE_SIZE-4],outline=c,width=4)
        if hl_left=="correct": bd(0,(47,158,68))
        elif hl_left=="wrong": bd(0,(208,0,0))
        if hl_right=="correct": bd(TILE_SIZE+GAP,(47,158,68))
        elif hl_right=="wrong": bd(TILE_SIZE+GAP,(208,0,0))
        return combo

    for i,q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts=st.session_state.opts_cache[f"opts_{st.session_state.mode}_{i}"]
        left,right=opts[0],opts[1]
        ans_key=f"{st.session_state.mode}_ans_{i}"
        chosen=st.session_state.get(ans_key)
        correct=q["filename"]

        lt = make_tile(os.path.join(IMAGE_DIR,left))
        rt = make_tile(os.path.join(IMAGE_DIR,right))

        hl_left=hl_right=None
        if chosen:
            if chosen==left:
                hl_left="correct" if left==correct else "wrong"
                if left!=correct and right==correct: hl_right="correct"
            elif chosen==right:
                hl_right="correct" if right==correct else "wrong"
                if right!=correct and left==correct: hl_left="correct"

        combo=compose(lt,rt,hl_left,hl_right)
        path=os.path.join(TMP_DIR,f"combo_{i}.png")
        combo.save(path)

        st.image(path,width=COMBO_W)

        col1,col2=st.columns(2)
        with col1:
            if st.button("選左邊",key=f"left_{i}"):
                st.session_state[ans_key]=left
                st.rerun()
        with col2:
            if st.button("選右邊",key=f"right_{i}"):
                st.session_state[ans_key]=right
                st.rerun()

        if chosen:
            if chosen==correct:
                score+=1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='opt-result-wrong'>✘ 錯誤，此為：{filename_to_name.get(chosen,'未知')}</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"<div>答對：{score}/{len(questions)}</div>", unsafe_allow_html=True)

st.markdown("---")
if st.button("🔄 重新開始本模式"):
    init_mode(bank, st.session_state.mode)
    st.rerun()
