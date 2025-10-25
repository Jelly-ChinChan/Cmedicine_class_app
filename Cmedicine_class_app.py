# Cmedicine_class_app.py
# 三模式中藥測驗（+ 錯題回顧）
#   1. 全部題目（看圖選藥名）
#   2. 隨機10題測驗
#   3. 圖片選擇模式（1x2），兩張圖並列，學生選左/右即作答，題目即時判定並顯示紅綠框
#
# 核心功能：
#   - 即時記錄學生的錯誤作答
#   - 當前進度條與答對題數
#   - 頁面最底部顯示「錯題回顧」清單
#   - 可隨時重新開始本模式（重抽題）
#
# 2025-10-25 consolidated build


import streamlit as st
import pandas as pd
import random
import os

try:
    from PIL import Image, ImageDraw
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
FIXED_SIZE = 300          # 模式1/2 單張題目圖大小
NUM_OPTIONS = 4           # 模式1/2 一題的文字選項數
DEFAULT_MODE = "全部題目"

# 模式3設定
TILE_SIZE = 160           # 單一候選圖的邊長 (正方形)
TMP_DIR = os.path.join(os.getcwd(), "temp_images")  # 本地暫存縮圖路徑
os.makedirs(TMP_DIR, exist_ok=True)

# Streamlit 頁面設定
st.set_page_config(
    page_title="中藥圖像測驗",
    page_icon="🌿",
    layout="centered",
)

# ====== 全域 CSS（適用所有模式）======
st.markdown(
    """
    <style>
    /* 隱藏預設 header/footer (Streamlit bar / "made with Streamlit") */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 頂部內距稍微縮小，減少大白邊 */
    .block-container {
        padding-top: 1rem;
        max-width: 700px;
    }

    /* 題目圖片卡片陰影/圓角 (模式1/2) */
    .img-card {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 0.25rem;
        border:4px solid transparent;
    }

    /* 模式標籤區塊 */
    .mode-banner-box {
        background:#f1f3f5;
        border:1px solid #dee2e6;
        border-radius:6px;
        padding:8px 12px;
        font-size:0.9rem;
        font-weight:600;
        line-height:1.4;
        display:inline-block;
        margin-top:0.5rem;
    }

    /* 模式3：按鈕行為 */
    .opt-result-correct {
        color:#2f9e44;
        font-weight:600;
        margin-top:8px;
        margin-bottom:8px;
    }
    .opt-result-wrong {
        color:#d00000;
        font-weight:600;
        margin-top:8px;
        margin-bottom:8px;
    }

    hr {
        border: none;
        border-top: 1px solid #dee2e6;
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


# ================= 影像工具：模式1/2用 =================
def crop_square_bottom(img, size=300):
    """
    裁成正方形並縮放到固定尺寸：
    - 高於寬：從上方切掉多的，保留底部
    - 寬於高：左右置中裁切
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
    顯示圖片卡 (模式1/2)，用 base64 內嵌，避免 file://
    如果 border_color 有值，就幫這張圖上色框
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
            <img src="{path}" width="{size}">
        </div>
        """,
        unsafe_allow_html=True
    )


# ================= 出題輔助 =================
def build_options(correct, pool, k=4):
    """
    回傳 k 個候選（正解 + 干擾），隨機順序，不重複
    correct: 正確值 (name 或 filename)
    pool:    所有可能值 list
    """
    distractors = [p for p in pool if p != correct]
    random.shuffle(distractors)
    opts = distractors[: max(0, k - 1)] + [correct]
    # 去重複再洗牌
    opts = list(dict.fromkeys(opts))
    random.shuffle(opts)
    return opts


def init_mode(bank, mode):
    """
    初始化當前模式的題目集，並清空上次的作答與錯題
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


# ================= 啟動 state =================
bank = load_question_bank()
filename_to_name = {item["filename"]: item["name"] for item in bank}

if "mode" not in st.session_state:
    st.session_state.mode = DEFAULT_MODE
if "questions" not in st.session_state:
    init_mode(bank, st.session_state.mode)
if "wrong_answers" not in st.session_state:
    st.session_state.wrong_answers = []

# ================= 模式切換 UI =================
st.markdown("### 🌿 模式選擇")

selected_mode = st.radio(
    "請選擇測驗模式",
    ["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"],
    index=["全部題目", "隨機10題測驗", "圖片選擇模式（1x2）"].index(st.session_state.mode),
    horizontal=False,
)

if selected_mode != st.session_state.mode:
    init_mode(bank, selected_mode)

questions = st.session_state.questions

# 每題選項預先緩存
for i, q in enumerate(questions):
    cache_key = f"opts_{i}"
    if cache_key not in st.session_state.opts_cache:
        if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
            # 模式1/2：四個藥名選項
            all_names = [x["name"] for x in bank]
            st.session_state.opts_cache[cache_key] = build_options(
                q["name"], all_names, k=NUM_OPTIONS
            )
        else:
            # 模式3：兩圖一題，先用4個檔名抽，前兩個檔名當左右
            all_files = [x["filename"] for x in bank]
            cand_files = build_options(q["filename"], all_files, k=2)
            # 保底：確保一定有2個，如果不夠就重補
            while len(cand_files) < 2:
                extra = random.choice(all_files)
                if extra not in cand_files:
                    cand_files.append(extra)
            st.session_state.opts_cache[cache_key] = cand_files[:2]

# ================= 模式標籤區塊 =================
st.markdown(
    f"""
    <div class="mode-banner-box">
        目前模式：{st.session_state.mode}
    </div>
    """,
    unsafe_allow_html=True
)


# ======================================================
# 模式1 & 模式2：看圖選藥名 / radio
# ======================================================
if st.session_state.mode in ["全部題目", "隨機10題測驗"]:
    score = 0
    done = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. 這個中藥的名稱是？**")

        # 顯示題目圖片
        img_path = os.path.join(IMAGE_DIR, q["filename"])
        render_img_card(img_path, size=FIXED_SIZE, border_color=None)

        # 題目選項
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

        # 解析 + 錯題記錄
        if chosen is not None:
            done += 1
            if chosen == q["name"]:
                score += 1
                st.markdown(
                    "<div class='opt-result-correct'>✔ 正確！</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，正確答案是「{q['name']}」</div>",
                    unsafe_allow_html=True,
                )

                # 紀錄錯題 (避免重複塞)
                signature = f"mode12-{i}-{chosen}"
                if not any(w.get("sig") == signature for w in st.session_state.wrong_answers):
                    st.session_state.wrong_answers.append({
                        "sig": signature,
                        "question": "辨識圖片屬於哪個中藥？",
                        "correct": q["name"],
                        "chosen": chosen,
                        "chosen_name": chosen,
                        "img": q["filename"],
                    })

        st.markdown("<hr />", unsafe_allow_html=True)

    # 進度條 + 答對數
    progress_ratio = (done / len(questions)) if questions else 0
    st.markdown(
        f"""
        <div style='margin-top:8px;font-size:0.9rem;'>
            進度：{done}/{len(questions)}　|　答對：{score}
        </div>

        <div style='height:8px;width:100%;background:#e9ecef;border-radius:4px;
                    overflow:hidden;margin:6px 0 24px 0;'>
            <div style='height:8px;width:{progress_ratio*100}%;background:#74c69d;'></div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ======================================================
# 模式3：圖片選擇模式（1x2）
# 兩張圖並排；各自有一顆按鈕；按下即作答；答後呈現紅/綠框
# ======================================================
elif st.session_state.mode == "圖片選擇模式（1x2）":

    # ========================
    # 模式3：圖片選擇模式（1x2）
    # ========================
    # 手機/電腦顯示兩張圖並排 (左邊/右邊)
    # 學生按「選左邊」或「選右邊」作答
    # 作答後：即時顯示紅/綠框 + 解析
    # 並且把錯題記錄到 st.session_state.wrong_answers

    # --- 參數 ---
    TILE_SIZE = 160  # 單張圖片邊長（正方形顯示大小）

    # --- 確保有暫存資料夾可存加工後的小圖（跨平台：Windows / Mac / Streamlit Cloud 都可以） ---
    TMP_DIR = os.path.join(os.getcwd(), "temp_images")
    os.makedirs(TMP_DIR, exist_ok=True)

    # --- 圖片處理工具 ---
    def make_square_tile(path):
        """
        讀入原始中藥圖，裁成正方形並縮到 TILE_SIZE x TILE_SIZE。
        規則：以底部為基準裁切(保留下面的外觀特徵)，在辨認乾燥藥材時比較直覺。
        若無法讀圖，回傳灰色方塊。
        """
        if os.path.exists(path) and Image is not None:
            try:
                im = Image.open(path)
                w, h = im.size
                side = min(w, h)
                # 從底往上切，使底部保留
                crop = im.crop((0, h - side, side, h))
                return crop.resize((TILE_SIZE, TILE_SIZE))
            except Exception:
                pass

        # fallback: 回傳灰色方塊（避免整頁炸掉）
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), color=(230, 230, 230))

    def draw_border(tile_img, status):
        """
        在 tile_img 外圍畫紅或綠框，回傳新影像。
        status:
          None       -> 不畫框
          "correct"  -> 綠框
          "wrong"    -> 紅框
        """
        out = tile_img.copy()
        if status is None:
            return out

        draw = ImageDraw.Draw(out)
        color = (47, 158, 68) if status == "correct" else (208, 0, 0)  # 綠 or 紅
        pad = 4
        x0, y0 = pad, pad
        x1, y1 = TILE_SIZE - pad - 1, TILE_SIZE - pad - 1

        # 疊3層 1px 線，看起來像粗框
        for off in range(3):
            draw.rectangle(
                [x0 + off, y0 + off, x1 - off, y1 - off],
                outline=color,
                width=1,
            )
        return out

    # --- 分數/進度統計 ---
    score = 0
    done = 0

    # === 問題迴圈：逐題顯示 ===
    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['name']}**")

        # 兩個候選圖檔名（左 / 右）
        opts_files = st.session_state.opts_cache[f"opts_{i}"]

        # 保險：如果某些情況下只有抓到一張圖，就補一張
        if len(opts_files) < 2:
            all_files = [x["filename"] for x in bank]
            while len(opts_files) < 2:
                extra = random.choice(all_files)
                if extra not in opts_files:
                    opts_files.append(extra)

        left_file = opts_files[0]
        right_file = opts_files[1]

        # ans_key：這題學生的作答會存這裡
        ans_key = f"ans_{i}"
        chosen = st.session_state.get(ans_key, None)

        # 正確解是哪個檔案
        correct_file = q["filename"]

        # --- 產生每張 tile（方形小圖） ---
        left_raw = make_square_tile(os.path.join(IMAGE_DIR, left_file))
        right_raw = make_square_tile(os.path.join(IMAGE_DIR, right_file))

        # --- 依學生狀態決定要不要畫框 ---
        left_status = None
        right_status = None

        if chosen:
            # 如果學生選了左圖
            if chosen == left_file:
                if left_file == correct_file:
                    left_status = "correct"
                else:
                    left_status = "wrong"
                    # 如果左邊是錯的，就把右邊標成正解（若它是正解）
                    if right_file == correct_file:
                        right_status = "correct"

            # 如果學生選了右圖
            elif chosen == right_file:
                if right_file == correct_file:
                    right_status = "correct"
                else:
                    right_status = "wrong"
                    if left_file == correct_file:
                        left_status = "correct"

            # fallback：理論上不太會走到，但保留以防萬一
            else:
                if left_file == correct_file:
                    left_status = "correct"
                if right_file == correct_file:
                    right_status = "correct"

        # --- 把框畫到圖上，得到最終顯示版本 ---
        left_final = draw_border(left_raw, left_status)
        right_final = draw_border(right_raw, right_status)

        # --- 把結果圖寫成實體檔案 (temp_images/tile_left_i.png 等)
        left_tmp_path = os.path.join(TMP_DIR, f"tile_left_{i}.png")
        right_tmp_path = os.path.join(TMP_DIR, f"tile_right_{i}.png")
        left_final.save(left_tmp_path)
        right_final.save(right_tmp_path)

        # --- 兩欄並列 (手機也盡力維持左右排) ---
        colL, colR = st.columns(2)

        with colL:
            # 顯示左邊的圖
            st.image(left_tmp_path, width=TILE_SIZE)
            # 底下放「選左邊」按鈕
            if st.button("選左邊", key=f"left_btn_{i}"):
                st.session_state[ans_key] = left_file
                st.rerun()  # 立即重整，讓紅/綠框與解析出現

        with colR:
            st.image(right_tmp_path, width=TILE_SIZE)
            if st.button("選右邊", key=f"right_btn_{i}"):
                st.session_state[ans_key] = right_file
                st.rerun()

        # --- 答題結果解析區塊 ---
        if chosen:
            if chosen == correct_file:
                # 答對
                st.markdown(
                    "<div style='color:#2f9e44;font-weight:600;'>✔ 正確！</div>",
                    unsafe_allow_html=True
                )
            else:
                # 答錯，顯示該張圖實際是誰
                picked_name = filename_to_name.get(chosen, "（未知）")
                st.markdown(
                    f"<div style='color:#d00000;font-weight:600;'>✘ 錯誤，此為：{picked_name}</div>",
                    unsafe_allow_html=True
                )

                # 紀錄錯題（避免重複記錄同一題同一錯）
                sig = f"mode3-{i}-{chosen}"
                already_logged = any(
                    w.get("sig") == sig for w in st.session_state.wrong_answers
                )
                if not already_logged:
                    st.session_state.wrong_answers.append({
                        "sig": sig,
                        "question": f"請找出：{q['name']}",
                        "correct": q["name"],
                        "chosen": chosen,
                        "chosen_name": picked_name,
                        "img": chosen,  # 用錯的那張或學生點到的那張
                    })

        # --- 題間分隔線 ---
        st.markdown("<hr style='margin:16px 0;' />", unsafe_allow_html=True)

        # --- 統計作答進度 & 分數 ---
        if chosen is not None:
            done += 1
            if chosen == correct_file:
                score += 1

    # === 題組結尾：顯示當前進度條 / 答對題數 ===
    progress_ratio = (done / len(questions)) if questions else 0
    st.markdown(
        f"""
        <div style='margin-top:8px;font-size:0.9rem;'>
            進度：{done}/{len(questions)}　|　答對：{score}
        </div>

        <div style='height:8px;
                    width:100%;
                    background:#e9ecef;
                    border-radius:4px;
                    overflow:hidden;
                    margin:6px 0 24px 0;'>
            <div style='height:8px;
                        width:{progress_ratio*100}%;
                        background:#74c69d;'>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# 最底部：重新開始本模式
# ======================================================
st.markdown("---")
if st.button("🔄 重新開始本模式", key="reset_mode_bottom"):
    init_mode(bank, st.session_state.mode)
    st.rerun()
