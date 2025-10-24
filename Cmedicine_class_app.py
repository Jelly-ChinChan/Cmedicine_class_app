# Cmedicine_class_app.py
# 三模式中藥測驗：看圖選名 / 抽10題 / 圖片選擇模式(2x2 + 答對紅綠框)
import streamlit as st
import pandas as pd
import random
import os

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import openpyxl  # noqa
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl 套件，請在 requirements.txt 中加入：\n"
        "streamlit\npandas\nopenpyxl\npillow"
    )
    st.stop()

# ================= 設定 =================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 300
NUM_OPTIONS = 4
DEFAULT_MODE = "全部題目"

st.set_page_config(page_title="中藥圖像測驗", page_icon="🌿", layout="centered")

# ================= 題庫 =================
def load_question_bank():
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到 Excel 題庫。")
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
        st.error("❌ Excel 需包含『藥名(name)』與『圖片檔名(filename)』欄位。")
        st.stop()

    df = df.dropna(subset=[name_col, file_col])
    return [{"name": str(r[name_col]).strip(), "filename": str(r[file_col]).strip()} for _, r in df.iterrows()]

# ================= 工具函式 =================
def crop_square_bottom(img, size=300):
    """裁成正方形，從底部為基準"""
    w, h = img.size
    if h > w:
        img = img.crop((0, h - w, w, h))
    elif w > h:
        left = (w - h) // 2
        img = img.crop((left, 0, left + h, h))
    return img.resize((size, size))

def show_image(path, size=300, border_color=None):
    """顯示圖片，若有 border_color 則加框顏色"""
    if not os.path.isfile(path):
        st.warning(f"⚠ 找不到圖片：{path}")
        return
    try:
        img = Image.open(path)
        img = crop_square_bottom(img, size)
        if border_color:
            st.markdown(
                f"""
                <div style='border:4px solid {border_color};
                            border-radius:8px;
                            display:inline-block;'>
                    <img src='data:image/png;base64,{image_to_base64(img)}' width='{size}'>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.image(img, use_container_width=False)
    except Exception:
        st.image(path, width=size)

def image_to_base64(image):
    """轉 base64 方便插入 HTML"""
    import io, base64
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def build_options(correct, pool, k=4):
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[:max(0, k - 1)] + [correct]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

def init_mode(bank, mode):
    if mode == "隨機10題測驗":
        qset = random.sample(bank, min(10, len(bank)))
    elif mode == "圖片選擇模式（2x2）":
        qset = random.sample(bank, min(10, len(bank)))
    else:
        qset = bank[:]
    random.shuffle(qset)
    st.session_state.mode = mode
    st.session_state.questions = qset
    st.session_state.opts_cache = {}
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

# ================= 初始化 =================
bank = load_question_bank()
sidebar_mode = st.sidebar.radio("選擇測驗模式", ["全部題目", "隨機10題測驗", "圖片選擇模式（2x2）"])
if "mode" not in st.session_state or sidebar_mode != st.session_state.mode:
    init_mode(bank, sidebar_mode)

questions = st.session_state.questions
all_names = [q["name"] for q in questions]

# 選項快取
for i, q in enumerate(questions):
    key = f"opts_{i}"
    if key not in st.session_state.opts_cache:
        if st.session_state.mode == "圖片選擇模式（2x2）":
            st.session_state.opts_cache[key] = build_options(q["filename"], [x["filename"] for x in bank], 4)
        else:
            st.session_state.opts_cache[key] = build_options(q["name"], all_names, 4)

# ================= 模式 1 & 2：看圖選藥名 =================
if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
    score, done = 0, 0
    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")
        show_image(os.path.join(IMAGE_DIR, q["filename"]))
        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        sel = st.radio("選項：", opts, index=None, label_visibility="collapsed", key=ans_key)
        if sel is not None:
            done += 1
            if sel == q["name"]:
                score += 1
                st.markdown("<div style='color:#2f9e44;'>解析：✔ 答對！</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#d00000;'>解析：✘ 答錯，正確答案是「{q['name']}」。</div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

    progress = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div style='border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px; background:#fff; border:1px solid #eee; margin-top:24px;'>
            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）　
            <b>得分</b>：{score}
            <div style='height:8px;width:100%;background:#e9ecef;border-radius:4px;overflow:hidden;margin-top:8px;'>
                <div style='height:8px;width:{progress*100}%;background:#74c69d;'></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ================= 模式 3：圖片選擇模式（2x2 + 高亮框） =================
elif st.session_state.mode == "圖片選擇模式（2x2）":
    score, done = 0, 0
    st.markdown("### 🧪 點擊圖片選出正確的中藥")

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")
        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"

        rows = [opts[:2], opts[2:]]
        for r in rows:
            cols = st.columns(2, gap="small")
            for j, opt in enumerate(r):
                img_path = os.path.join(IMAGE_DIR, opt)
                with cols[j]:
                    btn_key = f"btn_{i}_{opt}"
                    if st.button("", key=btn_key):
                        st.session_state[ans_key] = opt

                    chosen = st.session_state.get(ans_key)
                    border = None
                    # 判斷邊框顏色
                    if chosen:
                        if chosen == q["filename"] and opt == chosen:
                            border = "#2f9e44"  # 綠框（答對）
                        elif chosen == opt and chosen != q["filename"]:
                            border = "#d00000"  # 紅框（錯誤選）
                        elif chosen != opt and opt == q["filename"]:
                            border = "#2f9e44"  # 正確答案圖也標綠
                    show_image(img_path, size=150, border_color=border)

                    # 下方文字提示
                    if chosen:
                        if chosen == q["filename"] and opt == chosen:
                            st.markdown("<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>", unsafe_allow_html=True)
                        elif chosen == opt and chosen != q["filename"]:
                            st.markdown(f"<div style='color:#d00000;font-weight:600;'>✘ 答錯<br>正解：{q['name']}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
        if st.session_state.get(ans_key):
            done += 1
            if st.session_state[ans_key] == q["filename"]:
                score += 1

    progress = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div style='border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px; background:#fff; border:1px solid #eee; margin-top:24px;'>
            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）　
            <b>得分</b>：{score}
            <div style='height:8px;width:100%;background:#e9ecef;border-radius:4px;overflow:hidden;margin-top:8px;'>
                <div style='height:8px;width:{progress*100}%;background:#74c69d;'></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
