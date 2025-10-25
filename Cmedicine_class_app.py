# Cmedicine_class_app.py
#
# 中藥圖像小測驗（手機 2x2 強制版，保留 sidebar 切模式）
#
# 模式：
#   1. 全部題目：看圖片 → 選藥名 (radio)
#   2. 隨機10題測驗：同上，抽10題
#   3. 圖片選擇模式（2x2）：看藥名 → 點對的那張圖
#      - 顯示成兩排，每排兩張（columns(2) * 2）
#      - CSS 強制手機也並排兩欄
#
# 特性：
#   - 點即作答；正確=綠框，錯誤=紅框並顯示「此為：○○」
#   - 題圖統一裁成正方形（保留底部）
#   - 題尾顯示進度+得分
#   - 錯題寫入 st.session_state.wrong_answers（目前不顯示回顧）
#
# UI：
#   - 我們不再隱藏整個 header，讓 sidebar 切換模式可用
#   - 我們仍隱藏 footer / 右下角 feedback 徽章，畫面乾淨很多
#
# requirements.txt 需要：
#   streamlit
#   pandas
#   openpyxl
#   pillow

import streamlit as st
import pandas as pd
import random
import os

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import openpyxl  # noqa: F401
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl 套件，請在 requirements.txt 中加入：\n"
        "streamlit\npandas\nopenpyxl\npillow"
    )
    st.stop()

# ========= 基本參數 =========
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"

FIXED_SIZE = 300   # 模式1/2 題目大圖尺寸
GRID_SIZE  = 150   # 模式3 小圖尺寸
NUM_OPTIONS = 4    # 每題4選1
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ========= CSS =========
# 1. 讓手機上的 st.columns(2) 也保持兩欄 (50% / 50%)
# 2. 移除頁面底部的 footer / badge / feedback 按鈕
# 3. 圖片卡的外觀（陰影+圓角）
#
# 重要：我們這版「不隱藏 header、也不碰 stToolbar」，避免 sidebar toggle 也被紅掉
st.markdown(
    """
    <style>
    /* 手機上也強制 columns(2) 兩欄並排 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        justify-content: space-between !important;
        align-items: flex-start !important;
        column-gap: 0.75rem !important;
        row-gap: 0.75rem !important;
        margin-bottom: 0.75rem !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 0 0 calc(50% - 0.75rem) !important;
        width: calc(50% - 0.75rem) !important;
        max-width: calc(50% - 0.75rem) !important;
        min-width: calc(50% - 0.75rem) !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            justify-content: space-between !important;
            column-gap: 0.75rem !important;
            row-gap: 0.75rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 0 0 calc(50% - 0.75rem) !important;
            width: calc(50% - 0.75rem) !important;
            max-width: calc(50% - 0.75rem) !important;
            min-width: calc(50% - 0.75rem) !important;
        }
    }

    /* 圖片卡片：陰影 + 圓角 */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.5rem;
    }

    /* 隱藏頁面底部的 "Made with Streamlit" 、feedback badge、右下小工具 */
    footer,
    iframe[title="feedback-widget"],
    .viewerBadge_container__2wLQm,
    .stDeployButton,
    [data-testid="stStatusWidget"],
    [data-testid="stActionButtonIcon"] {
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
        max-height: 0 !important;
        pointer-events: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ========= 題庫載入 =========
def load_question_bank():
    """
    從 Excel 讀入題庫
    回傳 list[{"name":藥名, "filename":圖片檔名}, ...]
    """
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到 Excel 題庫，請確認 Cmedicine_class_app.xlsx 與程式在同層。")
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
        st.error(
            "❌ Excel 必須包含：\n"
            "  - 藥名欄位：name / 名稱 / 藥名 / 品項\n"
            "  - 圖片欄位：filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔"
        )
        st.stop()

    df = df.dropna(subset=[name_col, file_col])

    bank = []
    for _, row in df.iterrows():
        bank.append({
            "name": str(row[name_col]).strip(),
            "filename": str(row[file_col]).strip(),
        })

    if not bank:
        st.error("❌ 題庫為空，請檢查 Excel 內容。")
        st.stop()

    return bank

# ========= 圖片處理 =========
def crop_square_bottom(img, size=300):
    """
    把圖片裁成正方形：
    - 如果太高：從上方裁掉多的，保留底部
    - 如果太寬：左右置中裁
    然後縮成 size x size
    """
    w, h = img.size
    if h > w:
        img = img.crop((0, h - w, w, h))  # 從上方切掉，保留下方
    elif w > h:
        left = (w - h) // 2
        img = img.crop((left, 0, left + h, h))  # 左右平均切
    return img.resize((size, size))

def image_to_base64(image):
    import io, base64
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def render_img_card(path, size=300, border_color=None):
    """
    顯示圖片卡，可帶紅/綠框
    """
    if not os.path.isfile(path):
        st.warning(f"⚠ 找不到圖片：{path}")
        return

    if Image is not None:
        try:
            img = Image.open(path)
            img = crop_square_bottom(img, size)
            b64 = image_to_base64(img)

            border_css = (
                f"border:4px solid {border_color};"
                if border_color
                else "border:4px solid transparent;"
            )

            st.markdown(
                f"""
                <div class="img-card" style="{border_css} border-radius:8px;">
                    <img src="data:image/png;base64,{b64}" width="{size}">
                </div>
                """,
                unsafe_allow_html=True
            )
            return
        except Exception:
            pass

    # 後備方案（理論上不常用）
    border_css = (
        f"border:4px solid {border_color};"
        if border_color
        else "border:4px solid transparent;"
    )
    st.markdown(
        f"""
        <div class="img-card" style="{border_css} border-radius:8px;">
            <img src="file://{path}" width="{size}">
        </div>
        """,
        unsafe_allow_html=True
    )

# ========= 出題/狀態 =========
def build_options(correct, pool, k=4):
    """
    產生4個選項(1正確+干擾)，隨機打散，去重
    correct: 正解 (藥名或檔名)
    pool:    候選全集
    """
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

def init_mode(bank, mode):
    """
    根據模式建立題組，並清除上一輪的作答與錯題
    """
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

    # 清掉舊回答 ans_*
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

    # 清掉錯題
    st.session_state.wrong_answers = []

# ========= 啟動 & 模式選擇 =========
bank = load_question_bank()
filename_to_name = {item["filename"]: item["name"] for item in bank}

sidebar_mode = st.sidebar.radio(
    "選擇測驗模式",
    ["全部題目", "隨機10題測驗", "圖片選擇模式（2x2）"],
    index=0 if DEFAULT_MODE == "全部題目" else 1,
)

if "mode" not in st.session_state or sidebar_mode != st.session_state.mode:
    init_mode(bank, sidebar_mode)

questions = st.session_state.questions
all_names = [q["name"] for q in questions]

if "wrong_answers" not in st.session_state:
    st.session_state.wrong_answers = []

# 每題固定一組4個選項
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            # 模式1/2：看圖選藥名
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"],
                all_names,
                k=NUM_OPTIONS
            )
        else:
            # 模式3：看藥名選正確圖片
            all_files = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"],
                all_files,
                k=NUM_OPTIONS
            )

# ========= 模式1 & 模式2：看圖選藥名 =========
if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")

        img_path = os.path.join(IMAGE_DIR, q["filename"])
        render_img_card(img_path, size=FIXED_SIZE, border_color=None)

        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        current_choice = st.session_state.get(ans_key, None)

        st.radio(
            "選項：",
            opts,
            index=(opts.index(current_choice) if current_choice in opts else None),
            key=ans_key,
            label_visibility="collapsed",
        )

        chosen = st.session_state.get(ans_key, None)
        if chosen is not None:
            done += 1
            if chosen == q["name"]:
                score += 1
                st.markdown(
                    "<div style='color:#2f9e44;font-weight:600;'>解析：✔ 答對！</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='color:#d00000;font-weight:600;'>"
                    f"解析：✘ 答錯 正確答案是「{q['name']}」。"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # 錯題記錄
                signature = f"mode12-{i}-{chosen}"
                already_logged = any(
                    w.get("sig") == signature
                    for w in st.session_state.wrong_answers
                )
                if not already_logged:
                    st.session_state.wrong_answers.append({
                        "sig": signature,
                        "question": "辨識圖片屬於哪個中藥？",
                        "correct": q["name"],
                        "chosen": chosen,
                        "chosen_name": chosen,  # 在模式1/2中 chosen 就是藥名
                        "img": q["filename"],
                    })

        st.markdown("<hr style='margin:20px 0;' />", unsafe_allow_html=True)

    # 測驗總覽
    progress = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div style='border-radius:12px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px;
                    background:#fff;
                    border:1px solid #eee;
                    margin-top:24px;'>
            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）
            &nbsp;&nbsp;
            <b>得分</b>：{score}
            <div style='height:8px;
                        width:100%;
                        background:#e9ecef;
                        border-radius:4px;
                        overflow:hidden;
                        margin-top:8px;'>
                <div style='height:8px;
                            width:{progress*100}%;
                            background:#74c69d;'>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========= 模式3：圖片選擇模式（2x2） =========
elif st.session_state.mode == "圖片選擇模式（2x2）":
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]

        # 確保至少4張，不足就補
        while len(opts) < 4:
            extra = random.choice([x["filename"] for x in bank])
            if extra not in opts:
                opts.append(extra)
        opts = opts[:4]  # 只取前4個

        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 第一排：opts[0], opts[1]
        row1_cols = st.columns(2)
        row1_items = [(0, row1_cols[0]), (1, row1_cols[1])]
        for idx, col in row1_items:
            with col:
                opt_filename = opts[idx]
                img_path = os.path.join(IMAGE_DIR, opt_filename)

                btn_key = f"btn_{i}_r1_{idx}"
                if st.button("", key=btn_key, help="點這張圖作答"):
                    st.session_state[ans_key] = opt_filename
                    chosen = opt_filename

                # 框線顏色
                border_color = None
                if chosen:
                    if chosen == q["filename"] and opt_filename == chosen:
                        border_color = "#2f9e44"  # 選對
                    elif chosen == opt_filename and chosen != q["filename"]:
                        border_color = "#d00000"  # 選錯
                    elif chosen != opt_filename and opt_filename == q["filename"]:
                        border_color = "#2f9e44"  # 正解提示

                render_img_card(img_path, size=GRID_SIZE, border_color=border_color)

                # 解析顯示在被點的那張下方
                if chosen == opt_filename:
                    if chosen == q["filename"]:
                        st.markdown(
                            "<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        picked_name = filename_to_name.get(chosen, "（未知）")
                        st.markdown(
                            f"<div style='color:#d00000;font-weight:600;'>"
                            f"✘ 答錯<br>此為：{picked_name}"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        signature = f"mode3-{i}-{chosen}"
                        already_logged = any(
                            w.get("sig") == signature
                            for w in st.session_state.wrong_answers
                        )
                        if not already_logged:
                            st.session_state.wrong_answers.append({
                                "sig": signature,
                                "question": f"請找出：{q['name']}",
                                "correct": q["name"],
                                "chosen": chosen,
                                "chosen_name": picked_name,
                                "img": chosen,
                            })

        # 第二排：opts[2], opts[3]
        row2_cols = st.columns(2)
        row2_items = [(2, row2_cols[0]), (3, row2_cols[1])]
        for idx, col in row2_items:
            with col:
                opt_filename = opts[idx]
                img_path = os.path.join(IMAGE_DIR, opt_filename)

                btn_key = f"btn_{i}_r2_{idx}"
                if st.button("", key=btn_key, help="點這張圖作答"):
                    st.session_state[ans_key] = opt_filename
                    chosen = opt_filename

                border_color = None
                if chosen:
                    if chosen == q["filename"] and opt_filename == chosen:
                        border_color = "#2f9e44"
                    elif chosen == opt_filename and chosen != q["filename"]:
                        border_color = "#d00000"
                    elif chosen != opt_filename and opt_filename == q["filename"]:
                        border_color = "#2f9e44"

                render_img_card(img_path, size=GRID_SIZE, border_color=border_color)

                if chosen == opt_filename:
                    if chosen == q["filename"]:
                        st.markdown(
                            "<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        picked_name = filename_to_name.get(chosen, "（未知）")
                        st.markdown(
                            f"<div style='color:#d00000;font-weight:600;'>"
                            f"✘ 答錯<br>此為：{picked_name}"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        signature = f"mode3-{i}-{chosen}"
                        already_logged = any(
                            w.get("sig") == signature
                            for w in st.session_state.wrong_answers
                        )
                        if not already_logged:
                            st.session_state.wrong_answers.append({
                                "sig": signature,
                                "question": f"請找出：{q['name']}",
                                "correct": q["name"],
                                "chosen": chosen,
                                "chosen_name": picked_name,
                                "img": chosen,
                            })

        st.markdown("<hr style='margin:16px 0;' />", unsafe_allow_html=True)

        # 統計分數/進度
        if chosen is not None:
            done += 1
            if chosen == q["filename"]:
                score += 1

    # 測驗總覽
    progress = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div style='border-radius:12px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px;
                    background:#fff;
                    border:1px solid #eee;
                    margin-top:24px;'>
            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）
            &nbsp;&nbsp;
            <b>得分</b>：{score}
            <div style='height:8px;
                        width:100%;
                        background:#e9ecef;
                        border-radius:4px;
                        overflow:hidden;
                        margin-top:8px;'>
                <div style='height:8px;
                            width:{progress*100}%;
                            background:#74c69d;'>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# （目前不顯示錯題回顧，但 st.session_state.wrong_answers 已經累積了所有錯誤紀錄）
