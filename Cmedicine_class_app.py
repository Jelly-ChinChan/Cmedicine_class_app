# Cmedicine_class_app.py
# 四模式中藥測驗（Cloud-safe）
#
# 模式1：隨機10題多回合（最多10回合、不重複）
# 模式2：圖片1x2隨機10題（最多2回合、不重複）
# 模式3：第1–50題（看圖選藥名）
# 模式4：第51–100題（看圖選藥名）

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
    if len(bank) < 100:
        st.warning(f"⚠ 題庫目前只有 {len(bank)} 題，無法完整支援 1–100 題與 10 回合隨機。請至少準備 100 題。")
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

def build_name_options(correct_name, all_names, k=4):
    others = [n for n in all_names if n != correct_name]
    random.shuffle(others)
    opts = others[: max(0, k - 1)] + [correct_name]
    random.shuffle(opts)
    return opts

# ================= 模式1：隨機10題多回合 =================
def init_mode1_state(total_n):
    st.session_state.m1_round = 1
    st.session_state.m1_used_idxs = []
    st.session_state.m1_scores = []          # list of int per round
    st.session_state.m1_wrong_log = []       # list of dicts
    st.session_state.m1_round_complete = False
    st.session_state.m1_show_summary = False
    st.session_state.m1_total_n = total_n
    # 產生第1回合
    available = list(range(total_n))
    st.session_state.m1_current_idxs = random.sample(available, min(10, len(available)))

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
    current_idxs = st.session_state.get("m1_current_idxs", [])

    st.markdown(f"#### 🎯 模式1：隨機10題多回合（目前第 {current_round} 回合）")
    st.markdown("每回合隨機 10 題，不與前回合重複，最多 10 回合（最多 100 題）。")

    score_this = 0
    wrong_this_round = []
    num_answered = 0

    for local_i, idx in enumerate(current_idxs):
        q = bank[idx]
        st.markdown(f"**Q{local_i+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR, q["filename"]), size=FIXED_SIZE)

        opts = build_name_options(q["name"], all_names, k=4)
        ans_key = f"m1_r{current_round}_q{local_i}"
        # Cloud-safe：加「請選擇」
        display_opts = ["請選擇"] + opts
        raw = st.radio("選項", display_opts, key=ans_key, label_visibility="collapsed")
        chosen = raw if raw != "請選擇" else None

        if chosen is not None:
            num_answered += 1
            if chosen == q["name"]:
                score_this += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是「{q['name']}」</div>",
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

    st.markdown(f"本回合目前答對：**{score_this}/{len(current_idxs)}**（已作答 {num_answered} 題）")

    # 回合結算區
    if not st.session_state.m1_round_complete:
        if st.button("✅ 結算本回合成績"):
            # 將本回合結果寫入總紀錄
            st.session_state.m1_scores.append(score_this)
            st.session_state.m1_wrong_log.extend(wrong_this_round)
            st.session_state.m1_used_idxs.extend(current_idxs)
            st.session_state.m1_round_complete = True
            st.rerun()
    else:
        st.success(f"第 {current_round} 回合結算完成：得分 {st.session_state.m1_scores[-1]}/{len(current_idxs)}")

        max_rounds = min(10, total_n // 10) if total_n >= 10 else 1
        have_next_round = (current_round < max_rounds) and (len(st.session_state.m1_used_idxs) < total_n)

        col1, col2 = st.columns(2)
        with col1:
            if have_next_round and st.button("➡ 進入下一回合"):
                start_next_round_mode1()
                st.rerun()
        with col2:
            if st.button("🏁 查看總結算"):
                st.session_state.m1_show_summary = True

    # 總結算畫面
    if st.session_state.m1_show_summary:
        st.markdown("### 🧾 模式1 總結算")
        total_rounds = len(st.session_state.m1_scores)
        total_correct = sum(st.session_state.m1_scores)
        total_questions = total_rounds * 10 if total_rounds > 0 else 0

        st.markdown(f"- 總回合數：**{total_rounds}**")
        st.markdown(f"- 總得分：**{total_correct}** 題")
        if total_questions:
            st.markdown(f"- 總題數：約 **{total_questions}** 題")

        st.markdown("#### 各回合成績")
        for i, s in enumerate(st.session_state.m1_scores, start=1):
            st.markdown(f"- 第 {i} 回合：**{s}/10**")

        if st.session_state.m1_wrong_log:
            st.markdown("#### ❌ 錯題總整理")
            for miss in st.session_state.m1_wrong_log:
                render_img_card(os.path.join(IMAGE_DIR, miss["filename"]), size=140)
                st.markdown(
                    f"- 回合：第 {miss['round']} 回合  \n"
                    f"- 正解：**{miss['name']}**  \n"
                    f"- 你的答案：{miss['chosen']}"
                )
                st.markdown("<hr/>", unsafe_allow_html=True)

# ================= 模式2：圖片選擇 10 題（最多2回合） =================
def init_mode2_state(total_n):
    st.session_state.m2_round = 1
    st.session_state.m2_used_idxs = []
    st.session_state.m2_scores = []
    st.session_state.m2_wrong_log = []
    st.session_state.m2_round_complete = False
    st.session_state.m2_show_summary = False
    st.session_state.m2_total_n = total_n
    available = list(range(total_n))
    st.session_state.m2_current_idxs = random.sample(available, min(10, len(available)))

def start_next_round_mode2():
    total_n = st.session_state.m2_total_n
    used = set(st.session_state.m2_used_idxs)
    available = [i for i in range(total_n) if i not in used]
    if len(available) < 1:
        st.session_state.m2_show_summary = True
        return
    take = min(10, len(available))
    st.session_state.m2_current_idxs = random.sample(available, take)
    st.session_state.m2_round += 1
    st.session_state.m2_round_complete = False

def run_mode2(bank, filename_to_name):
    total_n = min(len(bank), 100)
    if "m2_round" not in st.session_state:
        init_mode2_state(total_n)

    current_round = st.session_state.m2_round
    current_idxs = st.session_state.get("m2_current_idxs", [])

    st.markdown(f"#### 🖼 模式2：圖片 1×2 選擇（目前第 {current_round} 回合，最多 2 回合）")
    st.markdown("每回合 10 題，最多兩回合（20 題），題目不重複。")

    GAP = 8
    COMBO_W = TILE_SIZE * 2 + GAP

    def make_square_tile(path):
        if os.path.exists(path) and Image is not None:
            try:
                return crop_square_bottom(Image.open(path), TILE_SIZE)
            except Exception:
                pass
        if Image is None:
            return None
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), (240, 240, 240))

    def compose_combo(left_tile, right_tile, hl_left=None, hl_right=None):
        if Image is None:
            return None
        combo = Image.new("RGB", (COMBO_W, TILE_SIZE), "white")
        if left_tile is not None:
            combo.paste(left_tile, (0, 0))
        if right_tile is not None:
            combo.paste(right_tile, (TILE_SIZE + GAP, 0))
        draw = ImageDraw.Draw(combo)

        def draw_border(x, color):
            draw.rectangle([x + 3, 3, x + TILE_SIZE - 4, TILE_SIZE - 4], outline=color, width=4)

        if hl_left == "correct":
            draw_border(0, (47, 158, 68))
        elif hl_left == "wrong":
            draw_border(0, (208, 0, 0))

        if hl_right == "correct":
            draw_border(TILE_SIZE + GAP, (47, 158, 68))
        elif hl_right == "wrong":
            draw_border(TILE_SIZE + GAP, (208, 0, 0))

        return combo

    score_this = 0
    wrong_this_round = []

    for local_i, idx in enumerate(current_idxs):
        q = bank[idx]
        st.markdown(f"**Q{local_i+1}. {q['name']}**")

        # 兩張圖片選擇：一正一錯
        all_idxs = list(range(total_n))
        other_idxs = [i for i in all_idxs if i != idx]
        wrong_idx = random.choice(other_idxs) if other_idxs else idx
        left_is_correct = random.choice([True, False])

        left_idx = idx if left_is_correct else wrong_idx
        right_idx = wrong_idx if left_is_correct else idx

        left_file = bank[left_idx]["filename"]
        right_file = bank[right_idx]["filename"]
        correct_file = q["filename"]

        ans_key = f"m2_r{current_round}_q{local_i}"
        chosen = st.session_state.get(ans_key)

        left_tile = make_square_tile(os.path.join(IMAGE_DIR, left_file))
        right_tile = make_square_tile(os.path.join(IMAGE_DIR, right_file))

        hl_left = hl_right = None
        if chosen is not None:
            if chosen == "left":
                hl_left = "correct" if left_file == correct_file else "wrong"
                if left_file != correct_file and right_file == correct_file:
                    hl_right = "correct"
            elif chosen == "right":
                hl_right = "correct" if right_file == correct_file else "wrong"
                if right_file != correct_file and left_file == correct_file:
                    hl_left = "correct"

        if Image is not None:
            combo = compose_combo(left_tile, right_tile, hl_left, hl_right)
            if combo is not None:
                combo_path = os.path.join(TMP_DIR, f"m2_combo_r{current_round}_{local_i}.png")
                combo.save(combo_path)
                st.image(combo_path, width=COMBO_W)
        else:
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(os.path.join(IMAGE_DIR, left_file), use_column_width=True)
            with col_img2:
                st.image(os.path.join(IMAGE_DIR, right_file), use_column_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("選左邊", key=f"m2_left_{current_round}_{local_i}", use_container_width=True):
                st.session_state[ans_key] = "left"
                st.rerun()
        with col2:
            if st.button("選右邊", key=f"m2_right_{current_round}_{local_i}", use_container_width=True):
                st.session_state[ans_key] = "right"
                st.rerun()

        if chosen is not None:
            chosen_file = left_file if chosen == "left" else right_file
            if chosen_file == correct_file:
                score_this += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                wrong_name = filename_to_name.get(chosen_file, "未知")
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，此為：{wrong_name}</div>",
                    unsafe_allow_html=True
                )
                wrong_this_round.append({
                    "round": current_round,
                    "idx": idx,
                    "name": q["name"],
                    "filename": q["filename"],
                    "chosen_name": wrong_name,
                })

        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"本回合目前答對：**{score_this}/{len(current_idxs)}**")

    # 回合結算
    if not st.session_state.m2_round_complete:
        if st.button("✅ 結算本回合成績（模式2）"):
            st.session_state.m2_scores.append(score_this)
            st.session_state.m2_wrong_log.extend(wrong_this_round)
            st.session_state.m2_used_idxs.extend(current_idxs)
            st.session_state.m2_round_complete = True
            st.rerun()
    else:
        st.success(f"模式2 第 {current_round} 回合結算完成：得分 {st.session_state.m2_scores[-1]}/{len(current_idxs)}")

        max_rounds = 2
        have_next_round = (current_round < max_rounds) and (len(st.session_state.m2_used_idxs) < total_n)

        col1, col2 = st.columns(2)
        with col1:
            if have_next_round and st.button("➡ 進入下一回合（模式2）"):
                start_next_round_mode2()
                st.rerun()
        with col2:
            if st.button("🏁 查看模式2結算"):
                st.session_state.m2_show_summary = True

    if st.session_state.m2_show_summary:
        st.markdown("### 🧾 模式2 總結算")
        total_rounds = len(st.session_state.m2_scores)
        total_correct = sum(st.session_state.m2_scores)
        st.markdown(f"- 總回合數：**{total_rounds}**")
        st.markdown(f"- 總得分：**{total_correct}** 題")
        st.markdown("#### 各回合成績")
        for i, s in enumerate(st.session_state.m2_scores, start=1):
            st.markdown(f"- 第 {i} 回合：**{s}/10**")

        if st.session_state.m2_wrong_log:
            st.markdown("#### ❌ 錯題總整理")
            for miss in st.session_state.m2_wrong_log:
                render_img_card(os.path.join(IMAGE_DIR, miss["filename"]), size=140)
                st.markdown(
                    f"- 回合：第 {miss['round']} 回合  \n"
                    f"- 題目：{miss['name']}  \n"
                    f"- 你選了：{miss['chosen_name']}"
                )
                st.markdown("<hr/>", unsafe_allow_html=True)

# ================= 模式3/4：固定題號區間 =================
def run_fixed_range_mode(bank, start_idx, end_idx, mode_label):
    all_names = [q["name"] for q in bank]
    st.markdown(f"#### 📚 {mode_label}")
    st.markdown(f"本模式題號範圍：**{start_idx+1} ~ {end_idx} 題**")

    score = 0
    count = 0

    for idx in range(start_idx, min(end_idx, len(bank))):
        q = bank[idx]
        count += 1
        st.markdown(f"**Q{idx+1}. 這個中藥的名稱是？**")
        render_img_card(os.path.join(IMAGE_DIR, q["filename"]), size=FIXED_SIZE)

        opts = build_name_options(q["name"], all_names, k=4)
        ans_key = f"fixed_{mode_label}_q{idx}"
        display_opts = ["請選擇"] + opts
        raw = st.radio("選項", display_opts, key=ans_key, label_visibility="collapsed")
        chosen = raw if raw != "請選擇" else None

        if chosen is not None:
            if chosen == q["name"]:
                score += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是「{q['name']}」</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<hr/>", unsafe_allow_html=True)

    if count > 0:
        st.markdown(f"<div>本模式目前答對：{score}/{count}</div>", unsafe_allow_html=True)

# ================= 主程式 =================
def main():
    bank = load_question_bank()
    if len(bank) == 0:
        st.stop()

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
    selected_mode = st.radio("請選擇測驗模式", mode_labels,
                             index=mode_labels.index(st.session_state.current_mode))

    if selected_mode != st.session_state.current_mode:
        st.session_state.current_mode = selected_mode
        st.rerun()

    st.markdown(f"<div class='mode-banner-box'>目前模式：{st.session_state.current_mode}</div>", unsafe_allow_html=True)

    mode = st.session_state.current_mode

    if mode == "模式1：隨機10題多回合":
        run_mode1(bank)
    elif mode == "模式2：圖片選擇隨機10題（最多兩回合）":
        run_mode2(bank, filename_to_name)
    elif mode == "模式3：第1–50題（看圖選藥名）":
        run_fixed_range_mode(bank, 0, 50, "模式3：第1–50題（看圖選藥名）")
    elif mode == "模式4：第51–100題（看圖選藥名）":
        run_fixed_range_mode(bank, 50, 100, "模式4：第51–100題（看圖選藥名）")

    st.markdown("---")
    if st.button("🔄 重新整理頁面（重置狀態）"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

if __name__ == "__main__":
    main()
