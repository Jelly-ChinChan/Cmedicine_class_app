# Cmedicine_class_app.py
# 模式：
#   1. 全部題目（看圖選藥名）
#   2. 隨機10題測驗
#   3. 圖片選擇模式（2x2，手機兩欄，點圖作答，答對/答錯顯示框與解析）
#
# 需求重點：
#   - 答錯時顯示「✘ 答錯 此為：<你選到的那張圖片的真實藥名>」

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
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 300         # 每張圖統一 300x300
NUM_OPTIONS = 4          # 每題 4 個選項
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# 🔧 CSS：確保模式三 2x2 圖片在手機也兩欄並排，縮小間距
st.markdown(
    """
    <style>
    /* 讓 st.columns(2) 在手機上也保持兩欄並排 */
    div.stColumns {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    div.stColumns > div[data-testid="column"] {
        flex: 0 0 calc(50% - 0.5rem) !important;
        max-width: calc(50% - 0.5rem) !important;
    }

    /* 卡片陰影/圓角 */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================= 載入題庫 =================
def load_question_bank():
    """
    從 Excel 讀取題庫並回傳：
    bank = [
      {"name": 藥名, "filename": 圖片檔名},
      ...
    ]
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
            "name": str(row[name_col]).strip(),        # 中藥名稱（答案用）
            "filename": str(row[file_col]).strip(),    # 對應圖片檔案
        })

    if not bank:
        st.error("❌ 題庫為空，請檢查 Excel 內容。")
        st.stop()

    return bank


# ================= 圖片處理 =================
def crop_square_bottom(img, size=300):
    """
    裁成正方形並縮放到固定尺寸：
    - 太高：從上方切掉，保留底部
    - 太寬：左右置中裁切
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
    顯示一張圖片卡（300x300），可加上綠/紅邊框。
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
                if border_color else
                "border:4px solid transparent;"
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

    # 備援：如果沒 PIL 或出錯
    border_css = (
        f"border:4px solid {border_color};"
        if border_color else
        "border:4px solid transparent;"
    )
    st.markdown(
        f"""
        <div class="img-card" style="{border_css} border-radius:8px;">
            <img src="file://{path}" width="{size}">
        </div>
        """,
        unsafe_allow_html=True
    )


# ================= 選項生成 =================
def build_options(correct, pool, k=4):
    """
    回傳 4 個候選（正解 + 干擾），隨機順序，不重複
    correct: 正確值 (name 或 filename)
    pool:    所有可能值的 list
    """
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts


# ================= 模式初始化 =================
def init_mode(bank, mode):
    """
    - 全部題目：全部題庫
    - 隨機10題測驗：抽10題
    - 圖片選擇模式（2x2）：抽10題
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

    # 清除舊的作答紀錄
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]


# ================= App 啟動邏輯 =================
bank = load_question_bank()

# 方便模式3用：從檔名查藥名
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

# 幫每一題準備固定的4個選項 (避免畫面refresh時變動)
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            # 模式1/2：四個「藥名」選項
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"],
                all_names,
                k=NUM_OPTIONS
            )
        else:
            # 模式3：四張「圖片檔名」選項
            all_filenames = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"],
                all_filenames,
                k=NUM_OPTIONS
            )


# =================== 模式1 & 模式2 ===================
# 題型：看圖→選藥名，radio一選就判分
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
                    f"<div style='color:#d00000;font-weight:600;'>解析：✘ 答錯，正確答案是「{q['name']}」。</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<hr style='margin:20px 0;' />", unsafe_allow_html=True)

    # 進度＆得分顯示在所有題目後面
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


# =================== 模式3 ===================
# 題型：給藥名，出4張圖片(2x2)，點其中一張。
# 回饋：
#   - 你按下去的那張 → 如果正確：綠框 + ✔ 正確！
#                       如果錯誤：紅框 + ✘ 答錯 此為：<該圖片真正的藥名>
#   - 正確圖同時亮綠框（幫學生看答案）
elif st.session_state.mode == "圖片選擇模式（2x2）":
    score = 0
    done = 0

    for i, q in enumerate(questions):
        # 不顯示整頁大標，只顯示題號+正解藥名
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 用兩行，每行兩欄 -> 2x2
        rows = [opts[:2], opts[2:]]
        for row_idx, row_opts in enumerate(rows):
            cols = st.columns(2)  # 我們用上面 CSS 強制它在手機仍保持兩欄

            for col_idx, opt_filename in enumerate(row_opts):
                img_path = os.path.join(IMAGE_DIR, opt_filename)
                with cols[col_idx]:
                    # 這顆按鈕負責「我選了這張圖」
                    btn_key = f"btn_{i}_{row_idx}_{col_idx}"
                    if st.button("", key=btn_key, help="點這張圖作答"):
                        st.session_state[ans_key] = opt_filename
                        chosen = opt_filename  # 立刻更新畫面用的變數

                    # 判斷邊框顏色
                    border_color = None
                    if chosen:
                        if chosen == q["filename"] and opt_filename == chosen:
                            # 我選了正確的
                            border_color = "#2f9e44"  # 綠框
                        elif chosen == opt_filename and chosen != q["filename"]:
                            # 我選了這張，但它是錯的
                            border_color = "#d00000"  # 紅框
                        elif chosen != opt_filename and opt_filename == q["filename"]:
                            # 不是我選的，但它其實是正解 → 幫我標綠框
                            border_color = "#2f9e44"

                    # 顯示圖片卡（含彩色邊框）
                    render_img_card(
                        path=img_path,
                        size=150,
                        border_color=border_color
                    )

                    # 解析文字：只針對「我按到的那張」顯示
                    if chosen == opt_filename:
                        if chosen == q["filename"]:
                            # 答對
                            st.markdown(
                                "<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            # 答錯 -> 顯示「此為：<選到的圖片實際藥名>」
                            picked_name = filename_to_name.get(chosen, "（未知）")
                            st.markdown(
                                f"<div style='color:#d00000;font-weight:600;'>"
                                f"✘ 答錯<br>此為：{picked_name}"
                                f"</div>",
                                unsafe_allow_html=True
                            )

        st.markdown("<hr style='margin:16px 0;' />", unsafe_allow_html=True)

        # 累計進度/分數
        if chosen is not None:
            done += 1
            if chosen == q["filename"]:
                score += 1

    # 全部題目走完後顯示進度＆得分
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
