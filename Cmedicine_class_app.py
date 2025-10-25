# Cmedicine_class_app.py
# 三模式中藥測驗（+ 錯題回顧）
#   1. 全部題目（看圖選藥名）
#   2. 隨機10題測驗
#   3. 圖片選擇模式（1x2 橫向，2選1，點圖作答，彩色框+即時解析）
#
# 功能特色：
#   - 即時記錄學生的錯誤作答
#   - 頁面最底部顯示「錯題回顧」區塊，包含正解、學生選錯的名稱、參考圖
#
# 2025-10-25 更新：
#   1. 移除對 sidebar 的依賴：模式選擇改到主畫面頂端（手機也看得到）
#   2. 畫面上方顯示目前模式 + 🔄重新開始本模式 按鈕
#   3. 成績卡片加入清楚的大字 summary（本次得分 / 正確率）
#   4. 頁面最底部的「錯題回顧」區塊
#   5. 模式3改成「1x2 橫向並排、兩選一」，圖片本身就是按鈕

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
FIXED_SIZE = 300          # 模式1/2 題目圖大小
PAIR_SIZE = 200           # 模式3 (1x2) 的圖片大小
NUM_OPTIONS_MODE12 = 4    # 模式1/2 每題4個藥名選項
NUM_OPTIONS_MODE3 = 2     # 模式3 每題2張圖(2選1)
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ====== CSS：卡片樣式、間距、模式badge ======
st.markdown(
    """
    <style>
    /* 圖片卡片陰影/圓角 */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.25rem;
    }

    /* 模式標籤+重置區塊外觀 */
    .mode-banner {
        background:#f1f3f5;
        border:1px solid #dee2e6;
        border-radius:6px;
        padding:8px 12px;
        font-size:0.9rem;
        font-weight:600;
        display:flex;
        flex-wrap:wrap;
        gap:8px;
        align-items:center;
        margin-bottom:16px;
        line-height:1.4;
    }
    .mode-label {
        font-size:0.9rem;
        font-weight:600;
        color:#212529;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================= 載入題庫 =================
def load_question_bank():
    """
    從 Excel 讀取題庫 -> list[ { "name":藥名, "filename":圖片檔名 }, ... ]
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


# ================= 影像處理工具 =================
def crop_square_bottom(img, size=300):
    """
    裁成正方形並縮放到固定尺寸：
    - 高>寬：保留下半部
    - 寬>高：左右置中裁切
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
    顯示圖片卡，依需要顯示紅/綠框。
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

    # fallback
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


# ================= 出題相關 =================
def build_options(correct, pool, k):
    """
    回傳 k 個候選（含正解），隨機順序，不重複
    correct: 正確值 (name 或 filename)
    pool:    所有可能值 list
    k:       要的總數（模式1/2=4，模式3=2）
    """
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct]
    # 確保長度足夠；若資料太少就用全體再洗
    opts = list(dict.fromkeys(opts))  # 保留順序同時去重
    while len(opts) < k and len(distractors) > 0:
        extra = distractors.pop()
        if extra not in opts:
            opts.append(extra)
    random.shuffle(opts)
    return opts[:k]


def init_mode(bank, mode):
    """
    根據模式決定題目集，並清空上次作答與錯題紀錄
    """
    if mode == "隨機10題測驗":
        qset = random.sample(bank, min(10, len(bank)))
    elif mode == "圖片選擇模式（1x2）":
        qset = random.sample(bank, min(10, len(bank)))
    else:
        # 全部題目
        qset = bank[:]

    random.shuffle(qset)

    st.session_state.mode = mode
    st.session_state.questions = qset
    st.session_state.opts_cache = {}

    # 清除舊作答
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

    # 重置錯題回顧
    st.session_state.wrong_answers = []


# ================= 啟動 / 模式控制 =================
bank = load_question_bank()
filename_to_name = {item["filename"]: item["name"] for item in bank}

if "mode" not in st.session_state:
    st.session_state.mode = DEFAULT_MODE
if "questions" not in st.session_state:
    init_mode(bank, st.session_state.mode)
if "wrong_answers" not in st.session_state:
    st.session_state.wrong_answers = []

# 顯示模式選擇的 radio（主畫面）
st.markdown("#### 🌿 模式選擇")
selected_mode = st.radio(
    "請選擇測驗模式",
    ["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"],
    index=["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"].index(st.session_state.mode),
    horizontal=False,
)

# 如果radio選的模式不同，重新初始化
if selected_mode != st.session_state.mode:
    init_mode(bank, selected_mode)

questions = st.session_state.questions
all_names = [q["name"] for q in questions]

# 每題選項快取
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            # 模式1/2：四個藥名選項
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"],
                all_names,
                k=NUM_OPTIONS_MODE12
            )
        else:
            # 模式3：兩張圖片 (2選1)
            all_files = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"],
                all_files,
                k=NUM_OPTIONS_MODE3
            )

# ================== 頂部模式標籤 + 重置按鈕 ==================
col_banner_l, col_banner_r = st.columns([4,1])
with col_banner_l:
    st.markdown(
        f"""
        <div class="mode-banner">
            <div class="mode-label">目前模式：{st.session_state.mode}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_banner_r:
    if st.button("🔄 重新開始本模式"):
        init_mode(bank, st.session_state.mode)
        st.rerun()

# ========== 模式1&2：看圖選藥名 (radio) ==========
final_score = 0
final_done = 0
mode_is_12 = (st.session_state.mode in ["全部題目", "隨機10題測驗"])
mode_is_3 = (st.session_state.mode == "圖片選擇模式（1x2）")

if mode_is_12:
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")

        # 顯示題目圖片
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
                    f"<div style='color:#d00000;font-weight:600;'>解析：✘ 答錯 "
                    f"正確答案是「{q['name']}」。</div>",
                    unsafe_allow_html=True,
                )

                # 紀錄錯題
                signature = f"mode12-{i}-{chosen}"
                already_logged = any(w.get("sig") == signature for w in st.session_state.wrong_answers)
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

    # 成績卡片 summary
    progress = done / len(questions) if questions else 0
    percent = (score / len(questions) * 100) if questions else 0

    st.markdown(
        f"""
        <div style='border-radius:12px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px;
                    background:#fff;
                    border:1px solid #eee;
                    margin-top:24px;'>

            <div style='font-size:1.1rem;
                        font-weight:600;
                        margin-bottom:6px;'>
                本次得分：{score} / {len(questions)}　
                ({percent:.0f}%)
            </div>

            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）　
            <b>得分</b>：{score}

            <div style='height:8px;
                        width:100%;
                        background:#e9ecef;
                        border-radius:4px;
                        overflow:hidden;
                        margin-top:8px;'>
                <div style='height:8px;
                            width:{progress*100}% ;
                            background:#74c69d;'>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    final_score = score
    final_done = done

# ========== 模式3：圖片選擇模式（1x2 橫向 2選1） ==========
elif mode_is_3:
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 1x2：左右兩張圖
        cols = st.columns(2)
        for col_idx, opt_filename in enumerate(opts):
            img_path = os.path.join(IMAGE_DIR, opt_filename)

            with cols[col_idx]:
                # 整張圖片就是按鈕：用 form submit
                form_key = f"form_{i}_{col_idx}"
                with st.form(key=form_key, clear_on_submit=False):
                    # 邊框顏色
                    border_color = None
                    if chosen:
                        if chosen == q["filename"] and opt_filename == chosen:
                            border_color = "#2f9e44"  # 你選了正解 → 綠框
                        elif chosen == opt_filename and chosen != q["filename"]:
                            border_color = "#d00000"  # 你選了錯的 → 紅框
                        elif chosen != opt_filename and opt_filename == q["filename"]:
                            border_color = "#2f9e44"  # 正解高亮

                    # 準備圖片 HTML
                    img_html = ""
                    if os.path.isfile(img_path) and Image is not None:
                        try:
                            _img = Image.open(img_path)
                            _img = crop_square_bottom(_img, PAIR_SIZE)
                            import io, base64
                            buf = io.BytesIO()
                            _img.save(buf, format="PNG")
                            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                            border_css = (
                                f"border:4px solid {border_color};"
                                if border_color else
                                "border:4px solid transparent;"
                            )
                            img_html = f"""
                            <button type="submit"
                                style="
                                    background:none;
                                    border:none;
                                    padding:0;
                                    cursor:pointer;
                                ">
                                <div class="img-card" style="{border_css} border-radius:8px;">
                                    <img src="data:image/png;base64,{b64}"
                                         width="{PAIR_SIZE}">
                                </div>
                            </button>
                            """
                        except Exception:
                            pass

                    if img_html == "":
                        # fallback (PIL 不可用就用檔案路徑)
                        border_css = (
                            f"border:4px solid {border_color};"
                            if border_color else
                            "border:4px solid transparent;"
                        )
                        img_html = f"""
                        <button type="submit"
                            style="
                                background:none;
                                border:none;
                                padding:0;
                                cursor:pointer;
                            ">
                            <div class="img-card" style="{border_css} border-radius:8px;">
                                <img src="file://{img_path}"
                                     width="{PAIR_SIZE}">
                            </div>
                        </button>
                        """

                    # 顯示圖片按鈕
                    st.markdown(img_html, unsafe_allow_html=True)

                    submitted = st.form_submit_button(label=" ", use_container_width=False)

                    if submitted:
                        st.session_state[ans_key] = opt_filename
                        chosen = opt_filename  # 即時更新

                # 只對剛點到的那張圖顯示解析
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

                        # 紀錄錯題
                        signature = f"mode3-{i}-{chosen}"
                        already_logged = any(w.get("sig") == signature for w in st.session_state.wrong_answers)
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

        # 計分統計
        if chosen is not None:
            done += 1
            if chosen == q["filename"]:
                score += 1

    # 成績卡片 summary
    progress = done / len(questions) if questions else 0
    percent = (score / len(questions) * 100) if questions else 0

    st.markdown(
        f"""
        <div style='border-radius:12px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                    padding:16px;
                    background:#fff;
                    border:1px solid #eee;
                    margin-top:24px;'>

            <div style='font-size:1.1rem;
                        font-weight:600;
                        margin-bottom:6px;'>
                本次得分：{score} / {len(questions)}　
                ({percent:.0f}%)
            </div>

            <b>進度</b>：{done}/{len(questions)}（{progress*100:.0f}%）　
            <b>得分</b>：{score}

            <div style='height:8px;
                        width:100%;
                        background:#e9ecef;
                        border-radius:4px;
                        overflow:hidden;
                        margin-top:8px;'>
                <div style='height:8px;
                            width:{progress*100}% ;
                            background:#74c69d;'>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    final_score = score
    final_done = done
