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
FIXED_SIZE = 300           # 模式1/2 題目圖大小
PAIR_SIZE = 200           # 模式3 (1x2) 的圖片大小
NUM_OPTIONS_MODE12 = 4    # 模式1/2 每題4個藥名選項
NUM_OPTIONS_MODE3 = 2     # 模式3 兩張圖(2選1)
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ====== CSS：壓掉頂部空白 + 隱藏 header/footer + 強制圖片橫列 ======
st.markdown(
    """
    <style>
    /* 隱藏 Streamlit header/footer/toolbar 等 */
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    footer {display: none !important;}
    div[data-testid="stStatusWidget"] {display:none !important;}
    .viewerBadge_container__1QSob,
    .viewerBadge_container__1QSob iframe,
    .stAppDeployButton,
    .stAppToolbar {
        display: none !important;
    }

    /* 把主容器整個往上貼齊，拿掉預設 padding-top */
    .block-container {
        padding-top: 0rem !important;
    }
    section.main > div {
        padding-top: 0rem !important;
    }

    /* 標題區塊不要額外上邊距 */
    .top-section-tight {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }

    /* 灰底模式標示小卡 */
    .mode-banner-inline {
        background:#f1f3f5;
        border:1px solid #dee2e6;
        border-radius:6px;
        padding:8px 12px;
        font-size:0.9rem;
        font-weight:600;
        line-height:1.4;
        margin-bottom:16px;
        display:inline-block;
    }

    /* 圖片卡片陰影/圓角 */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.25rem;
    }

    /* 模式3：橫向兩張圖(2選1)的flex容器 */
    .choice-row {
        display:flex;
        flex-wrap:nowrap;           /* 不換行！手機也維持橫向 */
        justify-content:space-between;
        align-items:flex-start;
        gap:8px;
        width:100%;
        margin-bottom:0.5rem;
    }
    .choice-cell {
        flex:1 1 0;
        max-width:50%;
        text-align:center;
    }
    .choice-btn {
        background:none;
        border:none;
        padding:0;
        cursor:pointer;
        width:100%;
    }
    .choice-frame {
        border-radius:8px;
        box-shadow:0 2px 6px rgba(0,0,0,0.08);
        overflow:hidden;
        border:4px solid transparent;
    }
    .choice-frame.correct {
        border-color:#2f9e44 !important; /* 綠框 */
    }
    .choice-frame.wrong {
        border-color:#d00000 !important; /* 紅框 */
    }
    .choice-img {
        width:100%;
        height:auto;
        display:block;
    }

    /* 進度條 */
    .progress-wrapper {
        margin-top:8px;
        font-size:0.9rem;
    }
    .progress-bar-bg {
        height:8px;
        width:100%;
        background:#e9ecef;
        border-radius:4px;
        overflow:hidden;
        margin-top:4px;
        margin-bottom:24px;
    }
    .progress-bar-fill {
        height:8px;
        background:#74c69d;
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
    模式1/2單張題目圖用。依需要顯示紅/綠框。
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
    opts = list(dict.fromkeys(opts))
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
        qset = bank[:]  # 全部題目

    random.shuffle(qset)

    st.session_state.mode = mode
    st.session_state.questions = qset
    st.session_state.opts_cache = {}
    # 清掉舊答案
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]
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

# --- 處理網址參數 (給模式3點圖用) ---
# 我們用 query_params 來記錄使用者剛剛選了哪張圖
qp = st.query_params
if "q" in qp and "pick" in qp:
    try:
        q_idx = int(qp["q"])
        picked_file = qp["pick"]
        st.session_state[f"ans_{q_idx}"] = picked_file
    except:
        pass
    # 清掉 query 參數，避免一直卡URL狀態
    st.query_params.clear()

# ====== 頂部：模式選擇（貼齊最上方） ======
st.markdown(
    "#### 🌿 模式選擇",
    unsafe_allow_html=False,
)

selected_mode = st.radio(
    "請選擇測驗模式",
    ["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"],
    index=["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"].index(st.session_state.mode),
    horizontal=False,
)

if selected_mode != st.session_state.mode:
    init_mode(bank, selected_mode)

questions = st.session_state.questions
all_names = [q["name"] for q in questions]

# 每題選項快取
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"], all_names, k=NUM_OPTIONS_MODE12
            )
        else:
            all_files = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"], all_files, k=NUM_OPTIONS_MODE3
            )

# 顯示目前模式的小灰條（緊貼 radio，沒有大間距）
st.markdown(
    f"""
    <div class="mode-banner-inline">目前模式：{st.session_state.mode}</div>
    """,
    unsafe_allow_html=True
)

mode_is_12 = (st.session_state.mode in ["全部題目", "隨機10題測驗"])
mode_is_3 = (st.session_state.mode == "圖片選擇模式（1x2）")

final_score = 0
final_done = 0

# ========== 模式1&2：看圖選藥名 ==========
if mode_is_12:
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
                    f"<div style='color:#d00000;font-weight:600;'>解析：✘ 答錯 "
                    f"正確答案是「{q['name']}」。</div>",
                    unsafe_allow_html=True,
                )

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

    progress_ratio = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div class="progress-wrapper">
            進度：{done}/{len(questions)}　|　答對：{score}
        </div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width:{progress_ratio*100}%;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    final_score = score
    final_done = done

# ========== 模式3：圖片選擇模式（1x2，手機也橫向） ==========
elif mode_is_3:
    score = 0
    done = 0

    # CSS：兩欄並排（手機也盡量保持橫排）＋ 透明按鈕
    st.markdown("""
    <style>
    /* 不要讓兩個 columns 自己斷行成直式 */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }

    /* 兩欄都稍微縮一下，避免爆滿 */
    div[data-testid="column"] {
        flex: 0 0 48% !important;
        max-width: 48% !important;
        padding-left: 2px !important;
        padding-right: 2px !important;
    }

    /* 框容器：我們自己畫紅/綠框用 */
    .border-box {
        border: 3px solid transparent;
        border-radius: 8px;
        display: inline-block;
        padding: 0;
        margin: 0 auto;
    }
    .border-correct {
        border-color: #2f9e44;
    }
    .border-wrong {
        border-color: #d00000;
    }

    /* 把按鈕本體變透明、零padding、零邊框、零高度 */
    div.stButton > button[kind="secondary"],
    div.stButton > button[kind="primary"],
    div.stButton > button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        min-height: 0 !important;
        height: auto !important;
        line-height: 0 !important;
        color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts_files = st.session_state.opts_cache[f"opts_{i}"]  # 應該是2個檔名
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 2欄排
        colA, colB = st.columns(2)

        for col_idx, (col, opt_file) in enumerate(zip([colA, colB], opts_files)):
            img_path = os.path.join(IMAGE_DIR, opt_file)

            # 決定這個選項應該用什麼框
            border_class = "border-box"
            if chosen:
                if chosen == q["filename"] and opt_file == chosen:
                    border_class = "border-box border-correct"
                elif chosen == opt_file and chosen != q["filename"]:
                    border_class = "border-box border-wrong"
                elif chosen != opt_file and opt_file == q["filename"]:
                    border_class = "border-box border-correct"

            with col:
                # 先畫框的開頭
                st.markdown(f"<div class='{border_class}'>", unsafe_allow_html=True)

                # 畫圖片（固定寬度 110px，不用 use_container_width，避免撐滿整欄）
                if os.path.exists(img_path):
                    st.image(img_path, width=110)

                # 框的結尾
                st.markdown("</div>", unsafe_allow_html=True)

                # 這顆圖片的「按鈕」
                btn_key = f"btn_{i}_{col_idx}"
                clicked = st.button(
                    " ",  # label空白
                    key=btn_key,
                    type="secondary",
                    use_container_width=False,
                )

                if clicked:
                    st.session_state[ans_key] = opt_file
                    st.rerun()

        # 答案解析文字
        if chosen:
            if chosen == q["filename"]:
                st.markdown(
                    "<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>",
                    unsafe_allow_html=True
                )
            else:
                picked_name = filename_to_name.get(chosen, "（未知）")
                st.markdown(
                    f"<div style='color:#d00000;font-weight:600;'>✘ 答錯<br>此為：{picked_name}</div>",
                    unsafe_allow_html=True
                )

                signature = f"mode3-{i}-{chosen}"
                if not any(w.get("sig") == signature for w in st.session_state.wrong_answers):
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

    # 進度條 & 答對題數
    progress_ratio = done / len(questions) if questions else 0
    st.markdown(
        f"""
        <div style='margin-top:8px;font-size:0.9rem;'>
            進度：{done}/{len(questions)}　|　答對：{score}
        </div>
        <div style='height:8px;width:100%;background:#e9ecef;border-radius:4px;overflow:hidden;
                    margin-top:4px;margin-bottom:24px;'>
            <div style='height:8px;width:{progress_ratio*100}%;background:#74c69d;'></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    final_score = score
    final_done = done




# ========== 重新開始本模式（最底） ==========
st.markdown("---")
if st.button("🔄 重新開始本模式"):
    init_mode(bank, st.session_state.mode)
    st.rerun()

# （錯題回顧區塊可在這裡加，沿用 st.session_state.wrong_answers）
