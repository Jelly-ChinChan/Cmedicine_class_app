# ================= 模式2：圖片 1×2 選擇 =================
def init_mode2_state(total_n):
    st.session_state.m2_round = 1
    st.session_state.m2_used_idxs = []
    st.session_state.m2_scores = []
    st.session_state.m2_wrong_log = []
    st.session_state.m2_round_complete = False
    st.session_state.m2_show_summary = False
    st.session_state.m2_total_n = total_n
    st.session_state.m2_current_idxs = random.sample(list(range(total_n)), min(10, total_n))


def start_next_round_mode2():
    total_n = st.session_state.m2_total_n
    used = set(st.session_state.m2_used_idxs)
    available = [i for i in range(total_n) if i not in used]
    if len(available) < 1:
        st.session_state.m2_show_summary = True
        return
    take = min(10, len(available))
    st.session_state.m2_current_idxs = random.sample(available, take)
    st.session_state.m2_round += 1
    st.session_state.m2_round_complete = False


def run_mode2(bank, filename_to_name):
    total_n = min(len(bank), 100)
    if "m2_round" not in st.session_state:
        init_mode2_state(total_n)

    current_round = st.session_state.m2_round
    current_idxs = st.session_state.m2_current_idxs

    st.markdown(f"#### 🖼 模式2：圖片 1×2 選擇（第 {current_round} 回合，最多 2 回合）")
    st.markdown("每回合 10 題，最多兩回合（20 題），題目不重複。")

    GAP = 8
    COMBO_W = TILE_SIZE * 2 + GAP

    def make_square_tile(path):
        if os.path.exists(path) and Image is not None:
            try:
                return crop_square_bottom(Image.open(path), TILE_SIZE)
            except Exception:
                pass
        if Image is None:
            return None
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), (240, 240, 240))

    def compose_combo(left_tile, right_tile, hl_left=None, hl_right=None):
        if Image is None:
            return None
        combo = Image.new("RGB", (COMBO_W, TILE_SIZE), "white")
        if left_tile is not None:
            combo.paste(left_tile, (0, 0))
        if right_tile is not None:
            combo.paste(right_tile, (TILE_SIZE + GAP, 0))
        draw = ImageDraw.Draw(combo)

        def draw_border(x, color):
            draw.rectangle([x + 3, 3, x + TILE_SIZE - 4, TILE_SIZE - 4], outline=color, width=4)

        if hl_left == "correct":
            draw_border(0, (47, 158, 68))
        elif hl_left == "wrong":
            draw_border(0, (208, 0, 0))

        if hl_right == "correct":
            draw_border(TILE_SIZE + GAP, (47, 158, 68))
        elif hl_right == "wrong":
            draw_border(TILE_SIZE + GAP, (208, 0, 0))

        return combo

    score_this = 0
    wrong_this_round = []

    for local_i, idx in enumerate(current_idxs):
        q = bank[idx]
        st.markdown(f"**Q{local_i+1}. {q['name']}**")

        # 一正一錯
        all_idxs = list(range(total_n))
        other_idxs = [i for i in all_idxs if i != idx]
        wrong_idx = random.choice(other_idxs) if other_idxs else idx
        left_is_correct = random.choice([True, False])

        left_idx = idx if left_is_correct else wrong_idx
        right_idx = wrong_idx if left_is_correct else idx

        left_file = bank[left_idx]["filename"]
        right_file = bank[right_idx]["filename"]
        correct_file = q["filename"]

        ans_key = f"m2_r{current_round}_q{local_i}"
        chosen = st.session_state.get(ans_key)

        left_tile = make_square_tile(os.path.join(IMAGE_DIR, left_file))
        right_tile = make_square_tile(os.path.join(IMAGE_DIR, right_file))

        hl_left = hl_right = None
        if chosen is not None:
            if chosen == "left":
                hl_left = "correct" if left_file == correct_file else "wrong"
                if left_file != correct_file and right_file == correct_file:
                    hl_right = "correct"
            elif chosen == "right":
                hl_right = "correct" if right_file == correct_file else "wrong"
                if right_file != correct_file and left_file == correct_file:
                    hl_left = "correct"

        if Image is not None:
            combo = compose_combo(left_tile, right_tile, hl_left, hl_right)
            if combo is not None:
                combo_path = os.path.join(TMP_DIR, f"m2_combo_r{current_round}_{local_i}.png")
                combo.save(combo_path)
                st.image(combo_path, width=COMBO_W)
        else:
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(os.path.join(IMAGE_DIR, left_file), use_column_width=True)
            with col_img2:
                st.image(os.path.join(IMAGE_DIR, right_file), use_column_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("選左邊", key=f"m2_left_{current_round}_{local_i}", use_container_width=True):
                st.session_state[ans_key] = "left"
                st.rerun()
        with col2:
            if st.button("選右邊", key=f"m2_right_{current_round}_{local_i}", use_container_width=True):
                st.session_state[ans_key] = "right"
                st.rerun()

        if chosen is not None:
            chosen_file = left_file if chosen == "left" else right_file
            is_correct = (chosen_file == correct_file)
            if is_correct:
                score_this += 1
                st.markdown("<div class='opt-result-correct'>✔ 正確！</div>", unsafe_allow_html=True)
            else:
                wrong_name = filename_to_name.get(chosen_file, "未知")
                st.markdown(
                    f"<div class='opt-result-wrong'>✘ 錯誤，此為：{wrong_name}</div>",
                    unsafe_allow_html=True
                )
                wrong_this_round.append({
                    "round": current_round,
                    "idx": idx,
                    "name": q["name"],
                    "filename": q["filename"],
                    "chosen_name": wrong_name,
                })

            # GSheet logging
            log_key = f"mode2|{current_round}|{idx}"
            chosen_name = filename_to_name.get(chosen_file, "未知")
            log_answer_once(
                log_key,
                mode="模式2",
                round_no=current_round,
                q_index=idx + 1,
                question_name=q["name"],
                chosen=chosen_name,
                correct=is_correct,
                filename=q["filename"],
            )

        st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown(f"本回合目前答對：**{score_this}/{len(current_idxs)}**")

    if not st.session_state.m2_round_complete:
        if st.button("✅ 結算本回合成績（模式2）"):
            st.session_state.m2_scores.append(score_this)
            st.session_state.m2_wrong_log.extend(wrong_this_round)
            st.session_state.m2_used_idxs.extend(current_idxs)
            st.session_state.m2_round_complete = True
            st.rerun()
    else:
        st.success(f"模式2 第 {current_round} 回合結算完成：得分 {st.session_state.m2_scores[-1]}/{len(current_idxs)}")

        max_rounds = 2
        have_next_round = (current_round < max_rounds) and (len(st.session_state.m2_used_idxs) < total_n)

        col1, col2 = st.columns(2)
        with col1:
            if have_next_round and st.button("➡ 進入下一回合（模式2）"):
                start_next_round_mode2()
                st.rerun()
        with col2:
            if st.button("🏁 查看模式2結算"):
                st.session_state.m2_show_summary = True

    if st.session_state.m2_show_summary:
        st.markdown("### 🧾 模式2 總結算")
        total_rounds = len(st.session_state.m2_scores)
        total_correct = sum(st.session_state.m2_scores)
        st.markdown(f"- 總回合數：**{total_rounds}**")
        st.markdown(f"- 總得分：**{total_correct}** 題")
        st.markdown("#### 各回合成績")
        for i, s in enumerate(st.session_state.m2_scores, start=1):
            st.markdown(f"- 第 {i} 回合：**{s}/10**")

        if st.session_state.m2_wrong_log:
            st.markdown("#### ❌ 錯題總整理")
            for miss in st.session_state.m2_wrong_log:
                render_img_card(os.path.join(IMAGE_DIR, miss["filename"]), size=140)
                st.markdown(
                    f"- 回合：第 {miss['round']} 回合  \n"
                    f"- 題目：{miss['name']}  \n"
                    f"- 你選了：{miss['chosen_name']}"
                )
                st.markdown("<hr/>", unsafe_allow_html=True)
