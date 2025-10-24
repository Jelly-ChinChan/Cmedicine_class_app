# streamlit_app.py —— 中藥測驗（3 模式：分類單選 / 分類多選 / 圖片辨識）
import streamlit as st
import random
import os
import io
import zipfile
import tempfile
from PIL import Image
import pandas as pd

st.set_page_config(
    page_title="中藥測驗（項目↔分類↔圖片）",
    page_icon="🌿",
    layout="centered"
)

# ===================== 你原本的題庫（文字題用） =====================
DATA = [
    {"item": "人參", "category": "補氣藥"}, {"item": "黨參", "category": "補氣藥"},
    {"item": "黃耆", "category": "補氣藥"}, {"item": "山藥", "category": "補氣藥"},
    {"item": "大棗", "category": "補氣藥"}, {"item": "甘草", "category": "補氣藥"},

    {"item": "當歸", "category": "補血藥"}, {"item": "地黃", "category": "補血藥"},
    {"item": "白芍", "category": "補血藥"},

    {"item": "枸杞子", "category": "補陰藥"}, {"item": "麥門冬", "category": "補陰藥"},
    {"item": "知母", "category": "補陰藥"}, {"item": "石斛", "category": "補陰藥"},
    {"item": "女貞子", "category": "補陰藥"},

    {"item": "巴戟天", "category": "補陽藥"}, {"item": "淫羊藿", "category": "補陽藥"},
    {"item": "杜仲", "category": "補陽藥"}, {"item": "鎖陽", "category": "補陽藥"},

    {"item": "附子", "category": "溫裏藥"}, {"item": "吳茱萸", "category": "溫裏藥"},
    {"item": "細辛", "category": "溫裏藥"}, {"item": "丁香", "category": "溫裏藥"},

    {"item": "香附", "category": "理氣藥"}, {"item": "枳實", "category": "理氣藥"},
    {"item": "陳皮", "category": "理氣藥"},

    {"item": "天麻", "category": "平肝息風藥"}, {"item": "鉤藤", "category": "平肝息風藥"},

    {"item": "酸棗仁", "category": "安神藥"}, {"item": "柏子仁", "category": "安神藥"},
    {"item": "遠志", "category": "安神藥"},

    {"item": "芡實", "category": "收澀藥"}, {"item": "五味子", "category": "收澀藥"},
    {"item": "山茱萸", "category": "收澀藥"},

    {"item": "麻黃", "category": "辛溫解表藜藥"}, {"item": "辛夷", "category": "辛溫解表藥"},
    {"item": "白芷", "category": "辛溫解表藥"}, {"item": "蒼耳子", "category": "辛溫解表藥"},
    {"item": "防風", "category": "辛溫解表藥"}, {"item": "荊芥", "category": "辛溫解表藥"},
    {"item": "紫蘇葉", "category": "辛溫解表藥"},

    {"item": "紫胡", "category": "辛涼解表藥"}, {"item": "葛根", "category": "辛涼解表藥"},
    {"item": "升麻", "category": "辛涼解表藥"},

    {"item": "半夏", "category": "化痰藥"}, {"item": "貝母", "category": "化痰藥"},
    {"item": "桔梗", "category": "化痰藥"}, {"item": "旋覆花", "category": "化痰藥"},

    {"item": "白果", "category": "止咳平喘藥"}, {"item": "杏仁", "category": "止咳平喘藥"},
    {"item": "桑白皮", "category": "止咳平喘藥"}, {"item": "枇杷葉", "category": "止咳平喘藥"},

    {"item": "泽潟", "category": "利水滲濕藥"}, {"item": "茯苓", "category": "利水滲濕藥"},

    {"item": "蒼朮", "category": "芳香化濕藥"}, {"item": "厚朴", "category": "芳香化濕藥"},
    {"item": "砂仁", "category": "芳香化濕藥"},

    {"item": "威靈仙", "category": "祛風濕藥"}, {"item": "秦艽", "category": "祛風濕藥"},
    {"item": "獨活", "category": "祛風濕藥"},

    {"item": "山楂", "category": "消食藥"}, {"item": "麥芽", "category": "消食藥"},

    {"item": "大黃", "category": "攻下藥"}, {"item": "蘆薈", "category": "攻下藥"},

    {"item": "火麻仁", "category": "潤下藥"},

    {"item": "丹參", "category": "活血祛瘀藥"}, {"item": "桃仁", "category": "活血祛瘀藥"},
    {"item": "紅花", "category": "活血祛瘀藥"}, {"item": "延胡索", "category": "活血祛瘀藥"},
    {"item": "川芎", "category": "活血祛瘀藥"}, {"item": "益母草", "category": "活血祛瘀藥"},
    {"item": "牛膝", "category": "活血祛瘀藥"}, {"item": "水蛭", "category": "活血祛瘀藥"},

    {"item": "白及", "category": "止血藥"}, {"item": "艾草", "category": "止血藥"},
    {"item": "側柏葉", "category": "止血藥"}, {"item": "三七", "category": "止血藥"},

    {"item": "金銀花", "category": "清熱解毒藥"}, {"item": "連翹", "category": "清熱解毒藥"},
    {"item": "蒲公英", "category": "清熱解毒藥"}, {"item": "射干", "category": "清熱解毒藥"},

    {"item": "梔子", "category": "清熱瀉火藥"}, {"item": "夏枯草", "category": "清熱瀉火藥"},

    {"item": "黃連", "category": "清熱燥濕藥"}, {"item": "黃芩", "category": "清熱燥濕藥"},
    {"item": "黃柏", "category": "清熱燥濕藥"}, {"item": "龍膽", "category": "清熱燥濕藥"},
    {"item": "苦參", "category": "清熱燥濕藥"},

    {"item": "玄參", "category": "清熱涼血藥"}, {"item": "牡丹皮", "category": "清熱涼血藥"},
    {"item": "紫草", "category": "清熱涼血藥"}, {"item": "赤芍", "category": "清熱涼血藥"},

    {"item": "青蒿", "category": "清虛藥"},
    {"item": "蛇床子", "category": "外用藥"},
    {"item": "檳榔", "category": "驅蟲藥"},
]

ITEMS = [d["item"] for d in DATA]
CATES = sorted(list({d["category"] for d in DATA}))
ITEM2CATE = {d["item"]: d["category"] for d in DATA}
CATE2ITEMS = {}
for d in DATA:
    CATE2ITEMS.setdefault(d["category"], []).append(d["item"])

# ===================== 常數（題數 / 模式名稱） =====================
MAX_QUESTIONS = 10

MODE_1 = "模式1【單選：藥材→分類】"
MODE_2 = "模式2【多選：分類→藥材】"
MODE_3 = "模式3【圖片辨識：看圖選藥材】"

# ===================== 样式 =====================
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 22px !important; }
h2 { font-size: 26px !important; margin-top: 0.22em !important; margin-bottom: 0.22em !important; }
.block-container { padding-top: 0.4rem !important; padding-bottom: 0.9rem !important; max-width: 1000px; }
.progress-card { margin-bottom: 0.22rem !important; }
.stRadio, .stCheckbox { margin-top: 0 !important; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stRadio"]) { margin-top: 0 !important; }
.stButton>button{ height: 44px; padding: 0 18px; }
.feedback-small { font-size: 17px !important; line-height: 1.4; margin: 6px 0 2px 0; }
.choice-grid > label { display:block; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)

# ===================== 圖片模式的資料載入 =====================
@st.cache_data(show_spinner=False)
def load_herb_dataset(table_bytes: bytes, table_type: str, zip_bytes: bytes):
    """
    讀 Excel/CSV (必須要有 name / filename / category 欄位)
    解壓 ZIP 圖檔
    回傳 (herb_data_list, base_dir)
    herb_data_list = [
        {"name": "...", "img_path": "/tmp/.../1.jpg", "category": "..."},
        ...
    ]
    """
    # 1. 讀表格
    if table_type == "excel":
        xls = pd.ExcelFile(io.BytesIO(table_bytes))
        # 用第一個工作表
        df = pd.read_excel(xls, xls.sheet_names[0])
    else:
        df = pd.read_csv(io.BytesIO(table_bytes))

    # 強制使用固定欄位
    required_cols = ["name", "filename", "category"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"缺少欄位 {col}，請確認欄位名稱。")

    # 2. 解壓 ZIP
    tmp_dir = tempfile.mkdtemp(prefix="herb_imgs_")
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        zf.extractall(tmp_dir)

    # 3. 建立清單
    herb_list = []
    for _, row in df.iterrows():
        name = str(row["name"]).strip()
        filename = str(row["filename"]).strip()
        category = str(row["category"]).strip() if not pd.isna(row["category"]) else ""

        local_path = os.path.join(tmp_dir, filename)
        if os.path.exists(local_path):
            herb_list.append({
                "name": name,
                "img_path": local_path,
                "category": category
            })
        # 如果圖不在 ZIP，就先略過，不會把它放進題庫

    return herb_list, tmp_dir

# ===================== 狀態初始化 =====================
def _stem_key(mode, stem):
    return f"{mode}::{stem}"

def init_state():
    st.session_state.mode = MODE_1
    st.session_state.q_index = 0
    st.session_state.submitted = False
    st.session_state.records = []  # (mode, stem, options, correct_set, chosen_set, is_correct)
    st.session_state.used_stems = set()
    st.session_state.round_bank = []
    # 圖片辨識模式的來源資料
    st.session_state.herb_data = []
    st.session_state.herb_tmpdir = None

def start_new_round():
    st.session_state.q_index = 0
    st.session_state.submitted = False
    st.session_state.records.clear()
    st.session_state.used_stems.clear()
    st.session_state.round_bank = []

    for _ in range(MAX_QUESTIONS):
        q = generate_question(st.session_state.mode)
        tries = 0
        while _stem_key(q["mode"], q["stem"]) in st.session_state.used_stems and tries < 20:
            q = generate_question(st.session_state.mode)
            tries += 1
        st.session_state.used_stems.add(_stem_key(q["mode"], q["stem"]))
        st.session_state.round_bank.append(q)

# 第一次啟動
if "q_index" not in st.session_state:
    init_state()
    start_new_round()

# ===================== 安全抽樣工具 =====================
def safe_sample(population, k):
    population = list(population)
    if k <= 0:
        return []
    if k >= len(population):
        random.shuffle(population)
        return population[:]
    return random.sample(population, k=k)

# ===================== 題目生成 =====================
def generate_question(mode):
    # 模式1：單選（題幹=藥材名稱，選分類）
    if mode == MODE_1:
        stem = random.choice(ITEMS)
        correct_cate = ITEM2CATE[stem]
        distractors = safe_sample([c for c in CATES if c != correct_cate], 3)
        options = [correct_cate] + distractors
        options = options[:4]
        random.shuffle(options)
        correct_set = {correct_cate}
        return {
            "mode": MODE_1,
            "stem": stem,
            "options": options,
            "correct_set": correct_set
        }

    # 模式3：圖片辨識（題幹=圖片，選正確藥材名稱）
    if mode == MODE_3:
        # herb_data 來自使用者上傳的 Excel + ZIP
        pool = st.session_state.herb_data
        # 如果沒有圖資料，先塞一題假的避免崩潰
        if not pool:
            return {
                "mode": MODE_3,
                "stem": None,
                "options": ["(尚未上傳圖片資料)"],
                "correct_set": {""}
            }

        correct = random.choice(pool)
        stem_img = correct["img_path"]  # 本地暫存路徑
        # 組四個候選藥名
        other_names = [h["name"] for h in pool if h["name"] != correct["name"]]
        distractors = safe_sample(other_names, 3)
        options = [correct["name"]] + distractors
        options = options[:4]
        random.shuffle(options)
        return {
            "mode": MODE_3,
            "stem": stem_img,
            "options": options,
            "correct_set": {correct["name"]}
        }

    # 模式2：多選（題幹=分類，選該分類的所有藥材）
    stem = random.choice(CATES)
    pool_correct = CATE2ITEMS[stem][:]
    n_correct = max(1, min(3, len(pool_correct)))
    correct_items = set(safe_sample(pool_correct, n_correct))
    pool_wrong = [it for it in ITEMS if ITEM2CATE[it] != stem]
    wrong_items = set(safe_sample(pool_wrong, 4 - len(correct_items)))
    options = list(correct_items | wrong_items)[:4]
    random.shuffle(options)
    return {
        "mode": MODE_2,
        "stem": stem,
        "options": options,
        "correct_set": set(correct_items)
    }

# ===================== 畫面元件：進度條 =====================
def render_progress_card():
    i = st.session_state.q_index + 1
    n = MAX_QUESTIONS
    percent = int(i / n * 100)
    st.markdown(
        f"""
        <div class="progress-card" style='background-color:#f5f5f5; padding:9px 14px; border-radius:12px;'>
            <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;'>
                <div style='font-size:18px;'>🎯 進度：{i} / {n}</div>
                <div style='font-size:16px; color:#555;'>{percent}%</div>
            </div>
            <progress value='{i}' max='{n}' style='width:100%; height:14px;'></progress>
        </div>
        """,
        unsafe_allow_html=True
    )

# ===================== 題目顯示（依模式） =====================
def render_question(qobj):
    mode = qobj["mode"]
    stem = qobj["stem"]
    options = qobj["options"]

    # 模式1：單選 題幹=藥材名稱
    if mode == MODE_1:
        st.markdown(
            f"<h2>Q{st.session_state.q_index + 1}. {stem}</h2>",
            unsafe_allow_html=True
        )
        choice = st.radio("", options,
                          key=f"mc_{st.session_state.q_index}",
                          label_visibility="collapsed")
        return [choice] if choice else []

    # 模式3：看圖選名字（單選）
    if mode == MODE_3:
        st.markdown(
            f"<h2>Q{st.session_state.q_index + 1}. 請選出正確的藥材名稱</h2>",
            unsafe_allow_html=True
        )
        if stem is not None:
            st.image(stem, use_column_width=True)
        else:
            st.warning("尚未載入圖片資料，請先在左邊上傳 Excel + ZIP")
        choice = st.radio("",
                          options,
                          key=f"img_{st.session_state.q_index}",
                          label_visibility="collapsed")
        return [choice] if choice else []

    # 模式2：多選 題幹=分類
    st.markdown(
        f"<h2>Q{st.session_state.q_index + 1}. {stem}</h2>",
        unsafe_allow_html=True
    )
    chosen = []
    for idx, it in enumerate(options):
        if st.checkbox(it, key=f"chk_{st.session_state.q_index}_{idx}"):
            chosen.append(it)
    return chosen

# ===================== 判分與流程控制 =====================
def handle_action(qobj, chosen_list):
    correct_set = set(qobj["correct_set"])
    chosen_set = set(chosen_list)
    # 單選題 / 多選題都採 "完全一致才算對"
    is_correct = (chosen_set == correct_set)

    st.session_state.records.append(
        (qobj["mode"], qobj["stem"], qobj["options"], correct_set, chosen_set, is_correct)
    )
    st.session_state.submitted = True
    st.session_state.last_q = qobj

def goto_next():
    st.session_state.submitted = False
    st.session_state.q_index += 1
    if st.session_state.q_index >= MAX_QUESTIONS:
        return
    st.rerun()

# ===================== 側邊欄 =====================
with st.sidebar:
    st.markdown("### 中藥配對遊戲")

    st.markdown("**上傳圖片辨識用資料（模式3）**")
    table_file = st.file_uploader(
        "藥材資料表 (Excel 或 CSV，需 name/filename/category)",
        type=["xlsx", "xls", "csv"],
        key="table_upload"
    )
    zip_file = st.file_uploader(
        "圖片 ZIP (檔名要和 filename 一致)",
        type=["zip"],
        key="zip_upload"
    )

    if table_file and zip_file:
        # 偵測是 excel 還是 csv
        if table_file.name.lower().endswith((".xlsx", ".xls")):
            table_type = "excel"
        else:
            table_type = "csv"

        try:
            herb_data, tmp_dir = load_herb_dataset(
                table_bytes=table_file.read(),
                table_type=table_type,
                zip_bytes=zip_file.read()
            )
            if herb_data:
                st.session_state.herb_data = herb_data
                st.session_state.herb_tmpdir = tmp_dir
                st.success(f"已載入 {len(herb_data)} 筆圖片資料，可使用模式3。")
            else:
                st.warning("有讀到檔案，但沒有可用的藥材圖片對應。請確認 filename 與 ZIP 內檔名一致。")
        except Exception as e:
            st.error(f"載入圖片模式資料時發生問題：{e}")

    # 模式選擇（會依照是否有 herb_data 來限制模式3）
    allowed_modes = [MODE_1, MODE_2]
    if st.session_state.herb_data:
        allowed_modes.append(MODE_3)

    new_mode = st.radio(
        "選擇模式",
        allowed_modes,
        index=allowed_modes.index(st.session_state.mode) if st.session_state.mode in allowed_modes else 0
    )

    # 如果玩家切換模式，重新出題
    if new_mode != st.session_state.mode:
        st.session_state.mode = new_mode
        start_new_round()
        st.rerun()

    if st.button("🔄 重新開始"):
        init_state()
        start_new_round()
        st.rerun()

# ===================== 主畫面邏輯 =====================
if st.session_state.q_index < MAX_QUESTIONS:
    render_progress_card()
    qobj = st.session_state.round_bank[st.session_state.q_index]
    chosen_list = render_question(qobj)

    if st.session_state.submitted:
        ok = st.session_state.records[-1][-1]
        color = "#1a7f37" if ok else "#c62828"

        # 顯示正解（簡化：只顯示正解，不顯示多餘說明）
        if qobj["mode"] in (MODE_1, MODE_3):
            true_ans = list(qobj["correct_set"])[0]
            st.markdown(
                f"<div style='font-size:22px; font-weight:700; color:{color};'>{true_ans}</div>",
                unsafe_allow_html=True
            )
        else:
            # 模式2：一題可能多個正確藥材
            corr_items = "、".join(sorted(list(qobj["correct_set"])))
            st.markdown(
                f"<div style='font-size:22px; font-weight:700; color:{color};'>{corr_items}</div>",
                unsafe_allow_html=True
            )

        if st.button("下一題", key="next_btn"):
            goto_next()

    else:
        if st.button("送出答案", key="submit_btn"):
            if qobj["mode"] in (MODE_1, MODE_3) and not chosen_list:
                st.warning("請先選擇一個答案。")
            elif qobj["mode"] == MODE_2 and not chosen_list:
                st.warning("請至少勾選一個項目。")
            else:
                handle_action(qobj, chosen_list)
                st.rerun()

else:
    # 回顧頁
    total = len(st.session_state.records)
    correct = sum(1 for r in st.session_state.records if r[-1])
    acc = (correct / total * 100) if total else 0.0

    st.subheader("📊 總結")
    st.markdown(f"<h3>Total Answered: {total}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h3>Total Correct: {correct}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h3>Accuracy: {acc:.1f}%</h3>", unsafe_allow_html=True)

    with st.expander("查看每題結果"):
        for i, (mode, stem, options, correct_set, chosen_set, is_ok) in enumerate(st.session_state.records, 1):
            st.markdown(f"**Q{i}** — {mode}")

            if mode == MODE_1:
                st.markdown(f"- 題幹（藥材）：{stem}")
                st.markdown(f"- 選項（分類）：{'、'.join(options)}")
                st.markdown(f"- 正解：{list(correct_set)[0]}")
                st.markdown(f"- 你的作答：{list(chosen_set)[0] if chosen_set else '(未作答)'}")

            elif mode == MODE_2:
                st.markdown(f"- 題幹（分類）：{stem}")
                st.markdown(f"- 選項（藥材）：{'、'.join(options)}")
                st.markdown(f"- 正解（此題正確的藥材）：{'、'.join(sorted(list(correct_set)))}")
                st.markdown(f"- 你的作答：{'、'.join(sorted(list(chosen_set))) if chosen_set else '(未作答)'}")

            elif mode == MODE_3:
                st.markdown(f"- 題幹（圖片檔）：{os.path.basename(stem) if stem else '(無)'}")
                st.markdown(f"- 選項（藥材名）：{'、'.join(options)}")
                st.markdown(f"- 正解（藥材名）：{list(correct_set)[0]}")
                st.markdown(f"- 你的作答：{list(chosen_set)[0] if chosen_set else '(未作答)'}")

            st.markdown(f"- 結果：{'✅ 正確' if is_ok else '❌ 錯誤'}")
            st.markdown("---")

    st.button("🔄 再玩一次", on_click=lambda: (init_state(), start_new_round()))
