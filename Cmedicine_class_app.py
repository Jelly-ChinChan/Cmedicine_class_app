# Cmedicine_class_app.py
# 中藥圖像→藥名選擇測驗
# 特性：
#   - 圖片裁成 300x300，從下方為準保留底部，寬圖置中裁切
#   - 每題四選一（正確藥名 + 隨機3個干擾藥名）
#   - 點了選項就立即出現解析（綠=對，紅=錯，附正解）
#   - 題號為 Q1, Q2, ...
#   - 沒有「下一題」按鈕
#   - 頁首顯示目前得分 & 進度
#   - sidebar 可切換「全部題目」或「隨機10題測驗」

import streamlit as st
import pandas as pd
import random
import os

# Pillow 用於裁切/縮放圖片
try:
    from PIL import Image
except ImportError:
    Image = None

# openpyxl 用於讀取 Excel
try:
    import openpyxl  # noqa
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl，無法讀取 Excel 題庫。\n\n"
        "請在 requirements.txt 中加入：\n"
        "streamlit\npandas\nopenpyxl\npillow"
    )
    st.stop()

# ================= 基本設定 =================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
FIXED_SIZE = 250      # 每張圖最後都會呈現為 300x300
NUM_OPTIONS = 4       # 每題 4 個選項（正解1 + 干擾3）
DEFAULT_MODE = "全部題目"  # 初始模式

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ========== 讀題庫 ==========
def load_question_bank():
    """從 Excel 載入題庫並回傳 [{'name':..., 'filename':...}, ...]"""
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到題庫檔案 Cmedicine_class_app.xlsx，請確認檔案與程式在同一層。")
        st.stop()

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

    # 對應欄位：藥名 & 圖片檔名
    name_col, file_col = None, None
    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name", "名稱", "藥名", "品項"]:
            name_col = c
        elif cname in ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"]:
            file_col = c

    if not name_col or not file_col:
        st.error(
            "❌ Excel 缺少必要欄位：\n"
            "  藥名欄（name / 名稱 / 藥名 / 品項）\n"
            "  圖片欄（filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔）"
        )
        st.stop()

    df = df.dropna(subset=[name_col, file_col])

    bank = []
    for _, row in df.iterrows():
        bank.append({
            "name": str(row[name_col]).strip(),        # 正確答案
            "filename": str(row[file_col]).strip(),    # 對應照片檔名
        })

    if not bank:
        st.error("❌ 題庫為空。請檢查 Excel 內容。")
        st.stop()

    return bank


# ========== 建立四個選項 (正解 + 干擾) ==========
def build_options(correct_name, all_names, k=4):
    """
    回傳長度最多 k 的亂序選項清單：
    - 包含正確答案
    - 其餘為隨機干擾藥名，不重複
    """
    distractors = [n for n in all_names if n != correct_name]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct_name]
    # 去重 & 打亂
    opts = list(set(opts))
    random.shuffle(opts)
    return opts


# ========== 圖片裁切 & 縮放為 300x300 ==========
def render_square_image(path):
    """
    顯示圖片並處理成統一的 300x300：
    - 如果圖比較高：保留底部，從上方裁掉多的
    - 如果圖比較寬：左右置中裁掉
    - 不顯示 caption（不露出藥名或檔名）
    """
    if not os.path.isfile(path):
        st.warning(f"⚠ 找不到圖片檔案：{path}")
        return

    # 如果 pillow 沒裝或裁切失敗，就 fallback 用固定寬顯示
    if Image is None:
        st.image(path, width=FIXED_SIZE)
        return

    try:
        img = Image.open(path)
        w, h = img.size

        if h > w:
            # 太高 → 從上方裁掉多餘，保留底部
            top_crop = h - w
            img = img.crop((0, top_crop, w, h))
        elif w > h:
            # 太寬 → 水平置中裁掉
            left_crop = (w - h) // 2
            img = img.crop((left_crop, 0, left_crop + h, h))
        # 如果剛好是正方形就不裁

        img = img.resize((FIXED_SIZE, FIXED_SIZE))
        st.image(img)
    except Exception:
        st.image(path, width=FIXED_SIZE)


# ========== 初始化 / 模式切換邏輯 ==========
def init_mode_state(all_questions, mode):
    """
    根據模式決定題目集，並重設所有互動狀態。
    mode:
        - "全部題目": 使用全部題目，隨機排序
        - "隨機10題測驗": 從題庫中隨機抽10題（不夠10就全拿），再隨機排序
    """
    # 依模式取題
    if mode == "隨機10題測驗":
        sample_size = min(10, len(all_questions))
        picked = random.sample(all_questions, sample_size)
    else:
        picked = all_questions[:]

    random.shuffle(picked)

    # 寫入 session_state
    st.session_state.mode = mode
    st.session_state.questions = picked
    st.session_state.options_cache = {}
    # 清除舊答案
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith("ans_")]
    for k in keys_to_delete:
        del st.session_state[k]


def ensure_initialized(all_questions):
    """
    確保 session_state 有 mode / questions 這些東西。
    如果第一次進來就用 DEFAULT_MODE 初始化。
    如果使用者改了 sidebar 的模式，就重新初始化。
    """
    # 讀 sidebar 模式
    sidebar_mode = st.sidebar.radio(
        "選擇測驗模式",
        ["全部題目", "隨機10題測驗"],
        index=0 if DEFAULT_MODE == "全部題目" else 1,
    )

    # 如果還沒初始化任何東西，或 mode 不存在 → 初始化
    if "mode" not in st.session_state or "questions" not in st.session_state:
        init_mode_state(all_questions, sidebar_mode)
        return

    # 如果 sidebar 選的模式和現在不同 → 重新初始化（並清答案）
    if st.session_state.mode != sidebar_mode:
        init_mode_state(all_questions, sidebar_mode)


# ========== 計算目前得分與進度 ==========
def compute_progress_and_score(questions):
    score_now = 0
    answered = 0

    for idx, q in enumerate(questions):
        ans_key = f"ans_{idx}"
        chosen = st.session_state.get(ans_key)
        if chosen is not None:
            answered += 1
            if chosen == q["name"]:
                score_now += 1

    total_q = len(questions)
    progress_ratio = (answered / total_q) if total_q > 0 else 0.0
    return score_now, answered, total_q, progress_ratio


# =================== 主程式流程 ===================

# 1. 載題庫
full_bank = load_question_bank()

# 2. 確保有正確初始化模式 & 題目集
ensure_initialized(full_bank)

questions = st.session_state.questions
all_names_pool = [q["name"] for q in questions]

# 3. 確保每題的選項列表固定住（避免畫面重新整理時亂跳）
for idx, q in enumerate(questions):
    cache_key = f"opts_{idx}"
    if cache_key not in st.session_state.options_cache:
        st.session_state.options_cache[cache_key] = build_options(
            correct_name=q["name"],
            all_names=all_names_pool,
            k=NUM_OPTIONS
        )

# 4. 計算目前分數 / 進度
score_now, answered, total_q, progress_ratio = compute_progress_and_score(questions)

# 5. 頂部狀態條
st.markdown(
    f"""
    <div style='border-radius:16px;
                box-shadow:0 4px 12px rgba(0,0,0,0.08);
                padding:16px;
                background:#ffffff;
                border:1px solid rgba(0,0,0,0.07);
                margin-bottom:16px;'>
        <div style='font-weight:600; font-size:16px; margin-bottom:4px;'>
            模式：{st.session_state.mode}
        </div>
        <div style='font-size:14px; color:#444; margin-bottom:4px;'>
            進度 {answered}/{total_q}（{progress_ratio*100:.0f}%）
        </div>
        <div style='font-size:14px; color:#444; margin-bottom:8px;'>
            目前得分：<b>{score_now}</b>
        </div>
        <div style='height:8px; width:100%;
                    background:#e9ecef;
                    border-radius:4px;
                    overflow:hidden;'>
            <div style='height:8px;
                        width:{progress_ratio*100}%;
                        background:#74c69d;'>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# 6. 呈現每一題
for idx, q in enumerate(questions):
    st.markdown(f"**Q{idx+1}. 這個中藥的名稱是？**")

    # 圖片（300x300 底部裁切）
    img_path = os.path.join(IMAGE_DIR, q["filename"])
    render_square_image(img_path)

    # 取得本題固定的四個選項
    opts_key = f"opts_{idx}"
    opts_list = st.session_state.options_cache[opts_key]

    # radio key 會直接存在 session_state["ans_{idx}"]
    ans_key = f"ans_{idx}"
    prev_choice = st.session_state.get(ans_key, None)

    st.radio(
        "選項：",
        opts_list,
        index=(opts_list.index(prev_choice) if prev_choice in opts_list else None),
        key=ans_key,
        label_visibility="collapsed"
    )

    chosen = st.session_state.get(ans_key, None)
    if chosen is not None:
        if chosen == q["name"]:
            # 綠色解析（答對）
            st.markdown(
                "<div style='color:#2f9e44; font-weight:600;'>解析：✔ 答對！</div>",
                unsafe_allow_html=True
            )
        else:
            # 紅色解析（答錯+正解）
            st.markdown(
                "<div style='color:#d00000; font-weight:600;'>"
                f"解析：✘ 答錯，正確答案是「{q['name']}」。"
                "</div>",
                unsafe_allow_html=True
            )

    st.markdown(
        "<hr style='border:0;border-top:1px solid rgba(0,0,0,0.08);margin:20px 0;' />",
        unsafe_allow_html=True
    )
