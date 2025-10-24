# Cmedicine_class_app.py
# 一次列出全部題目（Q1, Q2, ...）
# 顯示圖片 -> 四選一（藥名）-> 選了就馬上顯示解析（綠/紅）
#
# 檔案結構：
#   Cmedicine_class_app.py
#   Cmedicine_class_app.xlsx
#   photos/
#   requirements.txt 需包含: streamlit pandas openpyxl pillow
#
# Excel 必須至少有：
#   - 藥名欄：name / 名稱 / 藥名 / 品項 其中一個
#   - 圖片欄：filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔 其中一個
#
# 流程：
#   - 每一題：圖片 (縮成 3/4 大小) + 四個選項（正確藥名 + 3 個干擾藥名）
#   - 學生點選後，立刻在該題下方顯示「解析」
#   - 上方顯示目前作答數/總數、得分

import streamlit as st
import pandas as pd
import random
import os

# Pillow 縮圖
try:
    from PIL import Image
except ImportError:
    Image = None  # 如果 pillow 沒裝，仍會顯示圖片，只是不能精準縮 3/4

# openpyxl 讀 xlsx
try:
    import openpyxl  # noqa: F401
except ImportError:
    st.error(
        "⚠ 缺少 openpyxl 套件，無法讀取 Excel 題庫。\n\n"
        "請在 requirements.txt 加入：streamlit pandas openpyxl pillow\n"
        "或在本機執行： pip install openpyxl pillow"
    )
    st.stop()

# ----------------- 可調參數 -----------------
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"
IMAGE_SCALE = 0.75     # 圖片縮成原圖的 3/4 大小
NUM_OPTIONS = 4        # 每題4個選項（正解1 + 干擾3）
# --------------------------------------------

st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ========== 載題庫 ==========

def load_question_bank():
    """
    從 Excel 載入題庫，找出 name / filename 欄位
    回傳一個 list[ {name, filename} , ... ]
    """
    if not os.path.isfile(EXCEL_PATH):
        st.error("❌ 找不到題庫檔案 Cmedicine_class_app.xlsx，請確認放在同一層。")
        st.stop()

    # 目前假設題庫是 .xlsx
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

    # 對應欄位
    name_col = None
    file_col = None

    for c in df.columns:
        cname = str(c).strip().lower()
        if cname in ["name", "名稱", "藥名", "品項"]:
            name_col = c
        elif cname in ["filename", "圖片檔名", "檔名", "file", "photo", "圖片", "圖檔"]:
            file_col = c

    if not name_col or not file_col:
        st.error(
            "❌ Excel 缺少必要欄位。\n"
            "需要藥名欄（name / 名稱 / 藥名 / 品項）\n"
            "以及圖片檔名欄（filename / 圖片檔名 / 檔名 / file / photo / 圖片 / 圖檔）"
        )
        st.stop()

    # 移除空值
    df = df.dropna(subset=[name_col, file_col])

    bank = []
    for _, row in df.iterrows():
        bank.append({
            "name": str(row[name_col]).strip(),       # 正確答案（藥名）
            "filename": str(row[file_col]).strip(),   # 對應圖片
        })

    if len(bank) == 0:
        st.error("❌ 題庫是空的。請確認 Excel 內有資料列。")
        st.stop()

    return bank


bank_raw = load_question_bank()

# 我們需要隨機順序，但要在第一次載入時固定住
if "questions" not in st.session_state:
    # 打散題目
    shuffled = bank_raw[:]
    random.shuffle(shuffled)
    st.session_state.questions = shuffled

# 取出固定後的題目清單
questions = st.session_state.questions

# ========== 產生四選項（正解 + 3干擾）並固定住 ==========

def build_name_options(correct_name, all_names, k=4):
    """
    從整體藥名池 all_names 中：
    - 挑 3 個不等於 correct_name 的干擾
    - 加上正確答案
    - 打亂
    """
    distractors = [n for n in all_names if n != correct_name]
    random.shuffle(distractors)
    opts = distractors[: max(0, k-1)] + [correct_name]
    # 去重以防重複，然後再洗
    opts = list(set(opts))
    random.shuffle(opts)
    return opts

# 我們會把每一題的4個選項事先算好並存起來（保持穩定，不會每次重新洗）
if "options_cache" not in st.session_state:
    st.session_state.options_cache = {}

all_names_pool = [q["name"] for q in questions]

for idx, q in enumerate(questions):
    qkey = f"q{idx}_options"
    if qkey not in st.session_state.options_cache:
        st.session_state.options_cache[qkey] = build_name_options(
            correct_name=q["name"],
            all_names=all_names_pool,
            k=NUM_OPTIONS
        )

# ========== 計算目前分數 / 完成度（即時） ==========
# 「得分」= 有作答且答對的題目數
# 「已作答」= 有選答案的題目數
score_now = 0
answered_count = 0

for idx, q in enumerate(questions):
    ans_key = f"answer_{idx}"
    sel = st.session_state.get(ans_key, None)
    if sel is not None:
        answered_count += 1
        if sel == q["name"]:
            score_now += 1

total_q = len(questions)
progress_ratio = answered_count / total_q

# ========== 頂部狀態卡（但不顯示主標題） ==========

st.markdown(
    f"""
    <div style='border-radius:16px;
                box-shadow:0 4px 12px rgba(0,0,0,0.08);
                padding:16px;
                background:#ffffff;
                border:1px solid rgba(0,0,0,0.07);
                margin-bottom:16px;'>
        <div style='font-weight:600; font-size:16px; margin-bottom:4px;'>
            進度 {answered_count}/{total_q}（{progress_ratio*100:.0f}%）
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

# ========== 工具：顯示縮小圖片（不顯示名字/檔名） ==========

def render_scaled_image(image_path: str):
    """
    顯示圖片，縮成原圖 3/4。
    不顯示任何 caption（不顯示藥名、不顯示檔名）。
    """
    if not os.path.isfile(image_path):
        st.warning(f"⚠ 找不到圖片檔案：{image_path}")
        return

    if Image is not None:
        try:
            img = Image.open(image_path)
            w, h = img.size
            new_size = (max(1, int(w * IMAGE_SCALE)), max(1, int(h * IMAGE_SCALE)))
            img_resized = img.resize(new_size)
            # 我們不要 caption，也不要 use_container_width 去拉大到滿版
            st.image(img_resized)
            return
        except Exception:
            pass

    # 備援：如果 pillow 沒裝或縮圖失敗
    st.image(image_path)

# ========== 題目逐題顯示（Q1, Q2, ...） ==========

for idx, q in enumerate(questions):
    q_header = f"**Q{idx+1}. 這個中藥的名稱是？**"
    st.markdown(q_header)

    # 圖片（只顯示圖片本身，沒有藥名/檔名 caption）
    img_path = os.path.join(IMAGE_DIR, q["filename"])
    render_scaled_image(img_path)

    # 四個選項（正解+干擾）固定於 options_cache
    opts_key = f"q{idx}_options"
    opts_list = st.session_state.options_cache[opts_key]

    # radio 用 key=f"answer_{idx}" 來記每題的答案
    ans_key = f"answer_{idx}"
    prev_val = st.session_state.get(ans_key, None)

    # 因為我們不再有「送出/下一題」按鈕，所以一旦選了就算送出
    # st.radio 本身就會即時寫入 st.session_state[ans_key]
    st.radio(
        "選項：",
        opts_list,
        index=(opts_list.index(prev_val) if prev_val in opts_list else None),
        key=ans_key,
        label_visibility="collapsed"
    )

    # 顯示解析區塊（如果已經選了答案）
    chosen = st.session_state.get(ans_key, None)
    if chosen is not None:
        if chosen == q["name"]:
            # 正確 -> 綠色解析
            st.markdown(
                "<div style='color:#2f9e44; font-weight:600;'>"
                "解析：✔ 答對！</div>",
                unsafe_allow_html=True
            )
        else:
            # 錯誤 -> 紅色解析 + 正解
            st.markdown(
                "<div style='color:#d00000; font-weight:600;'>"
                f"解析：✘ 答錯，正確答案是「{q['name']}」。"
                "</div>",
                unsafe_allow_html=True
            )

    # 每題之間留一條淡淡的分隔線，手機視覺比較清楚
    st.markdown(
        "<hr style='border:0;border-top:1px solid rgba(0,0,0,0.07);margin:24px 0;' />",
        unsafe_allow_html=True
    )

# 到這裡就全部題目都呈現了，沒有「下一題」按鈕。
# 學生可以逐題點選，每題下方即時出現紅/綠解析。
