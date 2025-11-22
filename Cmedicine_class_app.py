# Cmedicine_class_app.py
# 四模式中藥測驗（Cloud-safe, Mode 1/3/4 fixed options, show-answer-on-select）

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
DEFAULT_MODE = "模式1：隨機10題多回合"

TILE_SIZE = 200
TMP_DIR = os.path.join(os.getcwd(), "temp_images")
os.makedirs(TMP_DIR, exist_ok=True)

st.set_page_config(page_title="100題中藥跑台", page_icon="🌿", layout="centered")

# ================== CSS ==================
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
        st.error("❌ Excel 必須包含名稱 / 圖片檔名欄位。")
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
    if Image is None:
        st.image(path, width=size)
        return
    try:
        img = Image.open(path)
        img = crop_square_bottom(img, size)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        border_css = f"border:4px solid {border_color};" if border_color else "border:4px solid transparent;"
        st.markdown(
            f"<div class='img-card' style='{border_css}'>"
            f"<img src='data:image/png;base64,{b64}' width='{size}'></div>",
            unsafe_allow_html=True
        )
    except Exception:
        st.image(path, width=size)


# ================= 關鍵：固定選項（不跳動） =================
def get_fixed_options(q_index, correct_name, all_names, k=4):
    key = f"opts_{q_index}"
    if key not in st.session_state:
        others = [n for n in all_names if n != correct_name]
        random.shuffle(others)
        opts = others[: k - 1] + [correct_name]
        random.shuffle(opts)
        st.session_state[key] = opts
    return st.session_state[key]


# ================= 模式1：隨機10題多回合 =================
def init_mode1_state(total_n):
    st.session_state.m1_round = 1
    st.session_state.m1_used_idxs = []
    st.session_state.m1_scores = []
    st.session_state.m1_wrong_log = []
    st.session_state.m1_round_complete = False
    st.session_state.m1_show_summary = False
    st.session_state.m1_total_n = total_n
    st.session_state.m1_current_idxs = random.sample(list(range(total_n)), 10)


def start_next_round_mode1():
    total_n = st.session_state.m1_total_n
    used = set(st.session_state.m1_used_idxs)
    available = [i for i in range(total_n) if i not in used]
    if len(available) < 1:
        st.session_state.m1_show_summary = True
        return
    take = min(10, len(available))
    st.session_state.m1_current_idxs = random.sample(available, take)
    st.session_state.m1_round += 1
    st.session_state.m1_round_complete = False


def run_mode1(bank):
    total_n = min(len(bank), 100)
    if "m1_round" not in st.session_state:
        init_mode1_state(total_n)

    all_names = [q["name"] for q in bank]
    current_round = st.session_state.m1_round
    current_idxs = st.session_state.m1_current_idxs

    st.markdown(f"#### 🎯 模式1：隨機10題多回合（第 {current_round} 回合）")

    score_this = 0
    wrong_this_round = []

    for local_i, idx in enumerate(current_idxs):
        q = bank[idx]
        st.markdown(f"**Q{local_i+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR, q["filename"]), size=FIXED_SIZE)

        # 固定選項
        opts = get_fixed_options(f"m1_r{current_round}_q{local_i}", q["name"], all_names)
        ans_key = f"m1_ans_{current_round}_{local_i}"

        chosen = st.radio(
            "選項",
            ["請選擇"] + opts,
            index=0,
            key=ans_key,
            label_visibility="collapsed"
        )

        if chosen != "請選擇":
            if chosen == q["name"]:
                score_this += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是：{q['name']}</div>",
                    unsafe_allow_html=True
                )
                wrong_this_round.append({
                    "round": current_round,
                    "idx": idx,
                    "name": q["name"],
                    "filename": q["filename"],
                    "chosen": chosen,
                })

        st.markdown("<hr/>", unsafe_allow_html=True)

    # 按鈕：結算
    if not st.session_state.m1_round_complete:
        if st.button("✅ 結算本回合"):
            st.session_state.m1_scores.append(score_this)
            st.session_state.m1_wrong_log.extend(wrong_this_round)
            st.session_state.m1_used_idxs.extend(current_idxs)
            st.session_state.m1_round_complete = True
            st.rerun()

    else:
        st.success(f"第 {current_round} 回合得分：{st.session_state.m1_scores[-1]}/10")

        max_rounds = 10
        have_next_round = (current_round < max_rounds) and (len(st.session_state.m1_used_idxs) < total_n)

        col1, col2 = st.columns(2)
        with col1:
            if have_next_round and st.button("➡ 下一回合"):
                start_next_round_mode1()
                st.rerun()
        with col2:
            if st.button("🏁 查看總結算"):
                st.session_state.m1_show_summary = True

    if st.session_state.m1_show_summary:
        st.markdown("### 🧾 模式1總結")

        for i, s in enumerate(st.session_state.m1_scores, start=1):
            st.markdown(f"- 第 {i} 回合：**{s}/10**")

        if st.session_state.m1_wrong_log:
            st.markdown("#### ❌ 錯題總整理")
            for miss in st.session_state.m1_wrong_log:
                render_img_card(os.path.join(IMAGE_DIR, miss["filename"]), size=140)
                st.markdown(
                    f"- 回合：{miss['round']}  \n"
                    f"- 正解：{miss['name']}  \n"
                    f"- 你的答案：{miss['chosen']}"
                )
                st.markdown("<hr/>", unsafe_allow_html=True)


# ================= 模式 3/4：固定題號 =================
def run_fixed_range_mode(bank, start_idx, end_idx, mode_label):
    st.markdown(f"#### 📚 {mode_label}")

    all_names = [q["name"] for q in bank]
    score = 0
    total = 0

    for idx in range(start_idx, min(end_idx, len(bank))):
        q = bank[idx]
        total += 1
        st.markdown(f"**Q{idx+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR, q["filename"]), size=FIXED_SIZE)

        opts = get_fixed_options(f"m_fixed_{idx}", q["name"], all_names)
        ans_key = f"ans_fixed_{idx}"

        chosen = st.radio(
            "選項",
            ["請選擇"] + opts,
            index=0,
            key=ans_key,
            label_visibility="collapsed"
        )

        if chosen != "請選擇":
            if chosen == q["name"]:
                score += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是：{q['name']}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"本模式目前答對：**{score}/{total}**")


# ================= 主程式 =================
def main():
    bank = load_question_bank()
    filename_to_name = {x["filename"]: x["name"] for x in bank}

    mode_labels = [
        "模式1：隨機10題多回合",
        "模式2：圖片選擇隨機10題（最多兩回合）",
        "模式3：第1–50題（看圖選藥名）",
        "模式4：第51–100題（看圖選藥名）",
    ]

    if "current_mode" not in st.session_state:
        st.session_state.current_mode = DEFAULT_MODE

    st.markdown("### 🌿 測驗模式選擇")
    selected_mode = st.radio("請選擇模式", mode_labels,
                             index=mode_labels.index(st.session_state.current_mode))

    if selected_mode != st.session_state.current_mode:
        st.session_state.current_mode = selected_mode
        st.rerun()

    st.markdown(f"<div class='mode-banner-box'>目前模式：{selected_mode}</div>", unsafe_allow_html=True)

    if selected_mode == "模式1：隨機10題多回合":
        run_mode1(bank)
    elif selected_mode == "模式2：圖片選擇隨機10題（最多兩回合）":
        run_mode2(bank, filename_to_name)   # 原版保持
    elif selected_mode == "模式3：第1–50題（看圖選藥名）":
        run_fixed_range_mode(bank, 0, 50, "模式3：第1–50題")
    elif selected_mode == "模式4：第51–100題（看圖選藥名）":
        run_fixed_range_mode(bank, 50, 100, "模式4：第51–100題")

    st.markdown("---")
    if st.button("🔄 重置頁面"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()


if __name__ == "__main__":
    main()
