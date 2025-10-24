# streamlit_app.py —— 圖片↔中文分類 配對測驗
# Author: Jelly + GPT-5 Thinking
#
# 使用方式：
#   1. 放這個檔案跟 Cmedicine_class_app.xlsx 在同一層
#   2. 解壓 file_photo.zip 成資料夾 photos/ ，裡面放 1.jpg, 2.jpg, ...
#   3. 執行: streamlit run streamlit_app.py
#
# Excel 允許兩種欄位命名：
#   英文: name / filename / category
#   中文: 名稱 / 圖片檔名 / 分類
#
# 測驗流程：
#   - 顯示圖片
#   - 學生選該圖片的正確「分類」
#   - 一鍵送出答案→下一題
#   - 最後顯示總分，並可重新開始
#
# 介面風格：
#   - 進度卡 + 得分
#   - 單選題
#   - 手機友善，只有一顆主按鈕

import streamlit as st
import pandas as pd
import random
import os

# ===================== 可調參數 =====================
EXCEL_PATH = "Cmedicine_class_app.xlsx"
IMAGE_DIR = "photos"  # 請把解壓後的圖片放在這裡
NUM_OPTIONS = 4       # 每題最多幾個選項 (包含正確答案)。如果分類總數小於這個數字就自動縮小。

st.set_page_config(
    page_title="中藥圖像分類小測驗",
    page_icon="🌿",
    layout="centered"
)

# ===================== 工具函式 =====================

def load_question_bank():
    """
    從 Excel 讀資料，標準化欄位名稱，回傳一個 list[dict]
    dict 格式：{"name":..., "filename":..., "category":...}
    """
    df = pd.read_excel(EXCEL_PATH)

    # 嘗試對應欄位
    col_map_candidates = {
        "name": ["name", "名稱", "藥名", "品項"],
        "filename": ["filename", "圖片檔名", "檔名", "file", "photo"],
        "category": ["category", "分類", "類別", "功效分類"]
    }

    col_map = {}
    for std_col, candidates in col_map_candidates.items():
        for c in candidates:
            if c in df.columns:
                col_map[std_col] = c
                break

    # 確認欄位都有抓到
    needed = ["name", "filename", "category"]
    for n in needed:
        if n not in col_map:
            st.error(f"Excel 缺少必要欄位：{n}（支援欄名: {col_map_candidates[n]}）")
            st.stop()

    # 轉成乾淨 list[dict]
    bank = []
    for _, row in df.iterrows():
        item_name = str(row[col_map["name"]]).strip()
        filename = str(row[col_map["filename"]]).strip()
        category = str(row[col_map["category"]]).strip()

        # 檢查圖片檔是否存在，方便除錯
        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.isfile(img_path):
            # 不直接停掉，先警告，老師看到就知道哪張圖缺
            st.warning(f"找不到圖片檔: {img_path}")

        bank.append({
            "name": item_name,
            "filename": filename,
            "category": category
        })

    return bank


def init_session_state(bank):
    """
    第一次載入或重新開始時初始化狀態
    """
    random_order = bank[:]
    random.shuffle(random_order)

    st.session_state.questions = random_order
    st.session_state.total = len(random_order)

    st.session_state.index = 0          # 第幾題 (0-based)
    st.session_state.score = 0          # 累計分數
    st.session_state.submitted = False  # 目前這一題「是否已經送出答案」
    st.session_state.selected = None    # 目前這一題學生的選擇
    st.session_state.finished = False   # 是否已經做完所有題目


def get_current_question():
    """
    取得目前題目的 dict
    """
    i = st.session_state.index
    return st.session_state.questions[i]


def get_all_categories(bank):
    """
    回傳所有可能分類 (不重複)
    """
    cats = sorted(list(set([q["category"] for q in bank])))
    return cats


def build_options(correct_cat, all_cats, k=4):
    """
    產生本題選項：
    - 包含正確答案
    - 其餘為隨機干擾
    - 隨機打亂順序
    """
    # 其他分類當干擾
    distractors = [c for c in all_cats if c != correct_cat]
    random.shuffle(distractors)

    # 取干擾 + 正解
    opts = distractors[: max(0, k-1)]
    opts.append(correct_cat)

    # 去重後再洗牌
    opts = list(set(opts))
    random.shuffle(opts)
    return opts


def render_progress_card():
    """
    顯示進度 / 分數的小卡片
    """
    current_q_num = st.session_state.index + 1
    total_q = st.session_state.total
    pct = (current_q_num / total_q) * 100

    score_now = st.session_state.score

    card_html = f"""
    <div style="
        border-radius:16px;
        box-shadow:0 4px 12px rgba(0,0,0,0.08);
        padding:12px 16px;
        background:linear-gradient(to right, #f8f9fa, #ffffff);
        font-size:14px;
        line-height:1.4;
        border:1px solid rgba(0,0,0,0.05);
        margin-bottom:12px;
    ">
        <div style="font-weight:600; font-size:15px; margin-bottom:4px;">
            進度 {current_q_num} / {total_q}（{pct:.0f}%）
        </div>
        <div style="font-size:13px; color:#444;">
            目前得分：<span style="font-weight:600;">{score_now}</span>
        </div>
        <div style="margin-top:8px; height:8px; width:100%;
                    background:#e9ecef; border-radius:4px; overflow:hidden;">
            <div style="
                height:100%;
                width:{pct}%;
                background:#74c69d;
            "></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_final_screen():
    """
    全部題目回答完後的總結畫面
    """
    total_q = st.session_state.total
    score = st.session_state.score

    st.success(f"完成測驗！總得分：{score} / {total_q}")

    if st.button("重新開始", use_container_width=True):
        # 重新洗牌+歸零
        init_session_state(st.session_state.questions)


# ===================== 主邏輯開始 =====================

# 載入題庫
bank = load_question_bank()

# 初始化狀態（第一次進來或按了重新開始 init_session_state() 之後）
if "questions" not in st.session_state:
    init_session_state(bank)

# 如果已經完成整份測驗，直接顯示總結畫面
if st.session_state.finished:
    st.title("🌿 中藥圖像分類小測驗")
    render_final_screen()
    st.stop()

# 還沒做完的情況
q = get_current_question()
all_categories = get_all_categories(bank)

# 建立本題選項（為了確保按「下一題」時選項不變，我們會存在 session_state）
if "options_cache" not in st.session_state:
    st.session_state.options_cache = {}

qid_key = f"q{st.session_state.index}"
if qid_key not in st.session_state.options_cache:
    st.session_state.options_cache[qid_key] = build_options(
        correct_cat=q["category"],
        all_cats=all_categories,
        k=NUM_OPTIONS
    )

options = st.session_state.options_cache[qid_key]

# ===================== UI 畫面 =====================

st.title("🌿 中藥圖像分類小測驗")

# 進度卡
render_progress_card()

# 題目區
st.markdown(
    f"**Q{st.session_state.index + 1}. 這個屬於哪一類？**",
    help="請看圖片並選正確分類"
)

# 顯示圖片
img_path = os.path.join(IMAGE_DIR, q["filename"])
st.image(
    img_path,
    caption=f"{q['name']}（{q['filename']}）",
    use_column_width=True
)

# 單選選項（radio）
# 我們把目前的選擇存在 session_state.selected，讓送出後不要被洗掉
if st.session_state.selected not in options:
    # 如果之前的選擇不在這題選項裡，清空
    st.session_state.selected = None

st.session_state.selected = st.radio(
    "選擇分類：",
    options,
    index=options.index(st.session_state.selected) if st.session_state.selected in options else None,
    label_visibility="collapsed",
)

# ======= 作答後回饋 =======
if st.session_state.submitted:
    # 檢查對錯
    if st.session_state.selected == q["category"]:
        st.markdown(
            f"<div style='color:#2f9e44; font-weight:600;'>✔ 答對！正確分類：{q['category']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='color:#d00000; font-weight:600;'>✘ 答錯</div>"
            f"<div style='margin-top:4px;'>正確分類：<b>{q['category']}</b></div>",
            unsafe_allow_html=True
        )

    st.markdown(
        f"<div style='font-size:13px; color:#666; margin-top:6px;'>"
        f"這張圖是：{q['name']}"
        f"</div>",
        unsafe_allow_html=True
    )

# ======= 送出答案 / 下一題 按鈕 =======
button_label = "送出答案" if not st.session_state.submitted else "下一題"

if st.button(button_label, use_container_width=True):
    # 狀態一：還沒送出 -> 這次按下就是「交答案」
    if not st.session_state.submitted:
        st.session_state.submitted = True

        # 如果沒選就當作答錯（不加分）
        if st.session_state.selected == q["category"]:
            st.session_state.score += 1

    # 狀態二：已送出 -> 這次按下就是「跳到下一題」
    else:
        st.session_state.index += 1
        st.session_state.submitted = False
        st.session_state.selected = None  # 清掉上一題的選擇

        # 如果已經超過最後一題，進入結算畫面
        if st.session_state.index >= st.session_state.total:
            st.session_state.finished = True

        # 注意：下一題時不馬上重建 options，因為我們在進入下一題時才會重新跑本程式，
        # 上面會檢查 options_cache 裡有沒有下個題目的key，沒有才會生成。


# ======= 如果剛好已經完成全部題目，立刻顯示總結 =======
if st.session_state.finished:
    st.success("測驗完成！")
    render_final_screen()
