# Cmedicine_class_app.py
#
# 中藥圖像小測驗（含手機 2x2、錯題回顧）
#
# 模式：
#   1. 全部題目：看「圖片」選「藥名」
#   2. 隨機10題測驗：同上，但隨機抽 10 題
#   3. 圖片選擇模式（2x2）：看「藥名」選「正確圖片」
#      - 手機與電腦都維持 2x2
#      - 點圖片即作答
#      - 綠/紅框即時標示
#      - 答錯顯示「✘ 答錯 / 此為：<你點到的藥材名稱>」
#
# 共同特性：
#   - 圖片統一正方形（從下往上裁，保留底部）
#   - 每題一作答就立即顯示解析
#   - 全部題目結束後顯示進度＆得分
#   - 自動記錄錯題並在頁面底部「錯題回顧」區塊呈現
#
# requirements.txt 請至少包含：
# streamlit
# pandas
# openpyxl
# pillow

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
GRID_SIZE = 150                          # 模式3四宮格小圖(px)
NUM_OPTIONS = 4                          # 4選1
DEFAULT_MODE = "全部題目"

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ================== CSS：手機也固定兩欄 ==================
# 我們強制 st.columns(2) 在任何螢幕都保持左右兩欄 (各50%)
# 並加上 !important 與 @media 再保險，避免被 Streamlit 的行動版樣式覆蓋
st.markdown(
    """
    <style>
    /* 外層 columns 容器：用 flex row + wrap，間距小一點 */
    div.stColumns {
        display: flex !important;
        flex-wrap: wrap !important;
        flex-direction: row !important;
        gap: 0.75rem !important;
        margin-bottom: 0.75rem !important;
    }

    /* 每個 column：固定佔 50% 寬，禁止掉行動版 "100% 寬" 行為 */
    div.stColumns > div[data-testid="column"] {
        flex: 0 0 calc(50% - 0.75rem) !important;
        width: calc(50% - 0.75rem) !important;
        max-width: calc(50% - 0.75rem) !important;
        min-width: calc(50% - 0.75rem) !important;
        padding-right: 0px !important;
        padding-left: 0px !important;
    }

    /* 再加一層保險：在小螢幕下一樣鎖兩欄 */
    @media (max-width: 768px) {
        div.stColumns {
            display: flex !important;
            flex-wrap: wrap !important;
            flex-direction: row !important;
            gap: 0.75rem !important;
        }
        div.stColumns > div[data-testid="column"] {
            flex: 0 0 calc(50% - 0.75rem) !important;
            width: calc(50% - 0.75rem) !important;
            max-width: calc(50% - 0.75rem) !important;
            min-width: calc(50% - 0.75rem) !important;
        }
    }

    /* 圖片卡：陰影+圓角 */
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
    從 Excel 讀入題庫：
    [
      {"name": "某藥名", "filename": "1.jpg"},
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
       - 如果圖太高：從上面裁掉多的，保留底部
       - 如果圖太寬：左右置中裁
    2. 再縮成指定 size x size
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
    顯示圖卡 (陰影+圓角)，可帶綠框/紅框。
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

    # fallback：如果 PIL 失敗
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
    建立亂序的4選項 (correct + 干擾)
    去重後隨機。
    """
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct]
    opts = list(set(opts))
    random.shuffle(opts)
    return opts


def init_mode(bank, mode):
    """
    初始化模式：
      - 全部題目：全拿
      - 隨機10題測驗：抽10題
      - 圖片選擇模式（2x2）：抽10題
    並重置所有作答記錄和錯題回顧。
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

    # 清掉上一輪作答
    for k in list(st.session_state.keys()):
        if k.startswith("ans_"):
            del st.session_state[k]

    # 重置錯題回顧
    st.session_state.wrong_answers = []


# ================= 啟動 / 模式切換 =================
bank = load_question_bank()
filename_to_name = {item["filename"]: item["name"] for item in bank}  # 給模式3用

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

# 幫每一題建立固定的 4 個選項（避免重整時順序跳動）
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            # 模式1/2: 選的是藥名
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"],
                all_names,
                k=NUM_OPTIONS
            )
        else:
            # 模式3: 選的是圖檔
            all_files = [x["filename"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["filename"],
                all_files,
                k=NUM_OPTIONS
            )


# ================= 模式1 & 模式2 =================
# 題型：看圖片 -> 選藥名 (radio)
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

                # 記錄錯題
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
                        "chosen_name": chosen,  # 在此模式中 chosen 本身就是藥名
                        "img": q["filename"],
                    })

        st.markdown("<hr style='margin:20px 0;' />", unsafe_allow_html=True)

    # 進度＆得分（整份題目後顯示）
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

# ================= 模式3：圖片選擇模式（2x2） =================
# 題型：顯示藥名 -> 學生從4張圖片中選正確的那一張
# 回饋：
#   - 你按的那張圖：
#       ✔ 正確 → 綠框 + "✔ 正確！"
#       ✘ 錯誤 → 紅框 + "✘ 答錯 / 此為：<你選到的那張藥材名稱>"
#   - 正確圖同時亮綠框
elif st.session_state.mode == "圖片選擇模式（2x2）":
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        opts = st.session_state.opts_cache[f"opts_{i}"]
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 我們建兩列，每列 st.columns(2)
        # CSS 已強制不管在手機或電腦都保持左右兩欄各佔50%
        rows = [opts[:2], opts[2:]]
        for row_idx, row_opts in enumerate(rows):
            cols = st.columns(2)
            for col_idx, opt_filename in enumerate(row_opts):
                img_path = os.path.join(IMAGE_DIR, opt_filename)

                with cols[col_idx]:
                    btn_key = f"btn_{i}_{row_idx}_{col_idx}"
                    if st.button("", key=btn_key, help="點這張圖作答"):
                        st.session_state[ans_key] = opt_filename
                        chosen = opt_filename  # 立刻更新畫面

                    # 邊框顏色判斷
                    border_color = None
                    if chosen:
                        if chosen == q["filename"] and opt_filename == chosen:
                            border_color = "#2f9e44"  # 你選的是正解 → 綠框
                        elif chosen == opt_filename and chosen != q["filename"]:
                            border_color = "#d00000"  # 你選錯了 → 紅框
                        elif chosen != opt_filename and opt_filename == q["filename"]:
                            border_color = "#2f9e44"  # 正解（沒選到） → 標出綠框

                    # 顯示該張圖（150x150）
                    render_img_card(
                        path=img_path,
                        size=GRID_SIZE,
                        border_color=border_color
                    )

                    # 解析文字：僅對「你剛選的那張」顯示
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

                            # 記錄錯題（避免重覆同一題同一錯法）
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
                                    "img": chosen,  # 把他選錯的那張圖記錄下來
                                })

        st.markdown("<hr style='margin:16px 0;' />", unsafe_allow_html=True)

        # 分數 / 進度 累積
        if chosen is not None:
            done += 1
            if chosen == q["filename"]:
                score += 1

    # 在整份題目後方顯示 進度+得分
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
