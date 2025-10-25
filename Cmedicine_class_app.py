# Cmedicine_class_app.py
#
# 中藥圖像小測驗（手機版2x2 fallback + 測驗模式外觀強化）
#
# 模式：
#   1. 全部題目：看「圖片」選「藥名」
#   2. 隨機10題測驗：同上，但隨機抽 10 題
#   3. 圖片選擇模式（2x2）：看「藥名」選「正確圖片」
#      - 使用 fallback 2x2 版：
#        → 每題只產生一組 columns(2)
#        → 左欄顯示2張圖(上/下)，右欄顯示2張圖(上/下)
#        → 即使在某些手機上 columns 最後變單欄，也只會「左欄整組」後「右欄整組」，視覺上仍成對
#
# 共同特性：
#   - 圖片裁成正方形（從下往上保留）
#   - 點圖即可作答；馬上顯示綠/紅框、解析
#   - 底部顯示進度＆得分
#   - 錯題會記錄在 st.session_state.wrong_answers（目前不顯示，但你可以再加回回顧）
#
# 強化：
#   - 隱藏 Streamlit header / footer / 菜單 → 更像正式考試畫面
#
# requirements.txt 請至少包含：
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

# ================= 基本設定 =================
EXCEL_PATH = "Cmedicine_class_app.xlsx"  # 題庫
IMAGE_DIR = "photos"                     # 圖片資料夾
FIXED_SIZE = 300                         # 模式1/2題目用大圖(px)
GRID_SIZE = 150                          # 模式3小圖(px)
NUM_OPTIONS = 4                          # 4選1
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ================== CSS ==================
# 1. 隱藏 Streamlit header / footer / 主功能列
# 2. 圖片卡片的樣式（陰影、圓角）
# 3. 基礎 columns spacing（保留一點間距，不再強行覆蓋成兩欄，因為我們自己做 fallback）
st.markdown(
    """
    <style>
    /* 移除 Streamlit 頁面預設頁首與選單 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    /* 移除底部的 footer (例如 "Made with Streamlit") */
    footer {
        visibility: hidden !important;
        height: 0px !important;
    }
    /* 移除右上角 hamburger / deploy 等浮動按鈕容器 */
    .stApp [data-testid="stToolbar"] {
        display: none !important;
    }

    /* columns 間距微調：避免太擠 */
    div.stColumns {
        gap: 0.75rem !important;
        margin-bottom: 0.75rem !important;
    }

    /* 圖片卡：陰影+圓角 */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================= 載入題庫 =================
def load_question_bank():
    """
    從 Excel 讀入題庫：
    回傳 list[ { "name":藥名, "filename":圖片檔名 }, ... ]
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


# ================= 影像處理 =================
def crop_square_bottom(img, size=300):
    """
    1. 裁成正方形
       - 如果圖太高：從上面裁掉，保留底部
       - 如果圖太寬：左右置中裁
    2. 再縮成指定的 size x size
    """
    w, h = img.size
    if h > w:
        img = img.crop((0, h - w, w, h))
    elif w > h:
        left = (w - h) // 2
        img = img.crop((left, 0, left + h, h))
    return img.resize((size, size))


def image_to_base64(image):
    import io, base64
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def render_img_card(path, size=300, border_color=None):
    """
    顯示一張圖片卡片，可帶紅/綠框
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

    # fallback（理論上不太會用到）
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


# ================= 出題 & 狀態 =================
def build_options(correct, pool, k=4):
    """
    建立該題的4個選項 (1正確 + 3干擾)；亂序、去重
    correct: 正確答案 (name 或 filename)
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
    根據模式挑題：
      - 全部題目：所有題
      - 隨機10題測驗：抽10題
      - 圖片選擇模式（2x2）：抽10題
    同時清除舊作答與錯題紀錄
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

    # 清之前答過的
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

    # 清錯題回顧資料
    st.session_state.wrong_answers = []


# ================= 啟動 / 模式切換 =================
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

# 預先為每題固定4個選項，避免重整洗牌
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"],
                all_names,
                k=NUM_OPTIONS
            )
        else:
            all_files = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"],
                all_files,
                k=NUM_OPTIONS
            )

# ================= 模式1 & 模式2：看圖片 → 選藥名 =================
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

                # 紀錄錯題
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
                        "chosen_name": chosen,
                        "img": q["filename"],
                    })

        st.markdown("<hr style='margin:20px 0;' />", unsafe_allow_html=True)

    # 全題後顯示成績
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

# ================= 模式3：圖片選擇模式（2x2 fallback） =================
#
# 結構重點：
#   - 我們取該題4張圖片 -> opts[0], opts[1], opts[2], opts[3]
#   - 用 st.columns(2) 只建立左右兩欄 cols_left, cols_right
#   - 左欄放 opts[0]、opts[1]（上下各一張）
#   - 右欄放 opts[2]、opts[3]（上下各一張）
#
#   這樣即使在極小手機上 columns 被壓成單欄，也會先整組顯示左欄(兩張)，再整組顯示右欄(兩張)。
#   視覺上仍像成對對比，而不是4張圖一長串排下去。
#
elif st.session_state.mode == "圖片選擇模式（2x2）":
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]
        # 如果剛好不足4張（極端狀況），補到4
        while len(opts) < 4:
            extra = random.choice([x["filename"] for x in bank])
            if extra not in opts:
                opts.append(extra)

        # 保證順序長度4
        opts = (opts + opts[:4])[:4]

        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 分成左右兩欄
        col_left, col_right = st.columns(2)

        # 左欄顯示 opts[0], opts[1]
        with col_left:
            for sub_idx in [0, 1]:
                opt_filename = opts[sub_idx]
                img_path = os.path.join(IMAGE_DIR, opt_filename)

                btn_key = f"btn_{i}_L_{sub_idx}"
                if st.button("", key=btn_key, help="點這張圖作答"):
                    st.session_state[ans_key] = opt_filename
                    chosen = opt_filename

                # 邊框顏色
                border_color = None
                if chosen:
                    if chosen == q["filename"] and opt_filename == chosen:
                        border_color = "#2f9e44"  # 你選到正確
                    elif chosen == opt_filename and chosen != q["filename"]:
                        border_color = "#d00000"  # 你選到錯的
                    elif chosen != opt_filename and opt_filename == q["filename"]:
                        border_color = "#2f9e44"  # 正解高亮

                render_img_card(img_path, size=GRID_SIZE, border_color=border_color)

                # 解析提示（只對剛選的那張說話）
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

        # 右欄顯示 opts[2], opts[3]
        with col_right:
            for sub_idx in [2, 3]:
                opt_filename = opts[sub_idx]
                img_path = os.path.join(IMAGE_DIR, opt_filename)

                btn_key = f"btn_{i}_R_{sub_idx}"
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

        # 計分
        if chosen is not None:
            done += 1
            if chosen == q["filename"]:
                score += 1

    # 題組結束後顯示 進度+得分
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

# ===== 目前我們沒有重新顯示「錯題回顧」區塊 =====
# 但 st.session_state.wrong_answers 仍在收集，可以之後加回來或匯出 CSV。
