import streamlit as st
import datetime

from supabase import create_client
from constants import (
    SUPABASE_URL,
    SUPABASE_KEY,
    DATE_FORMAT,
    MISS_DAYS_THRESHOLD,
    MAX_CHALLENGE_DAYS,
)

from auth_manager import AuthManager
from data_manager_supabase import DataManagerSupabase
from habit_tracker import HabitTracker


# ======================
# 初期化
# ======================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

auth = AuthManager(supabase)
data_manager = DataManagerSupabase(supabase)
tracker = HabitTracker(data_manager)


st.set_page_config(page_title="5分習慣チャレンジ", layout="centered")
st.title("🕒 5分習慣チャレンジ")


# ======================
# 未ログイン
# ======================

if not auth.is_authenticated():
    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])

    with tab_login:
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            auth.login(email, password)
            st.rerun()

    with tab_signup:
        email = st.text_input("新規メールアドレス")
        password = st.text_input("新規パスワード", type="password")
        if st.button("登録"):
            auth.signup(email, password)
            st.success("登録完了。ログインしてください。")

    st.stop()


# ======================
# ログイン後
# ======================

user = auth.get_user()
user_id = user.id

habit = data_manager.load_user_habit(user_id)
logs = tracker.get_logs(user_id)

# ----------------------
# リセット判定（最優先）
# ----------------------

should_reset = tracker.should_reset(logs, MISS_DAYS_THRESHOLD)

if should_reset:
    st.warning("⚠️ 2日間習慣が達成されなかったため、リセットされます。")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("この習慣で再チャレンジ"):
            # ★ 未達でも archive する（重要修正点）
            if habit:
                tracker.archive(
                    user_id,
                    habit["name"] + "（未完了）",
                    habit["target_time"],
                )
            tracker.reset_logs(user_id)
            st.rerun()

    with col2:
        if st.button("新しい習慣を設定"):
            if habit:
                tracker.archive(
                    user_id,
                    habit["name"] + "（未完了）",
                    habit["target_time"],
                )
            tracker.reset_logs(user_id)
            data_manager.delete_user_habit(user_id)
            st.rerun()

    st.stop()


# ======================
# 習慣未設定
# ======================

if not habit:
    st.subheader("📌 新しい習慣を設定")

    habit_name = st.text_input("習慣名（例：ストレッチ）")
    target_time = st.time_input("目標時間", datetime.time(7, 0))

    if st.button("この習慣で始める"):
        data_manager.save_user_habit(
            user_id,
            habit_name,
            target_time.strftime("%H:%M"),
        )
        st.rerun()

    st.stop()


# ======================
# 習慣進行中
# ======================

st.subheader(f"🔥 習慣：{habit['name']}")
st.caption(f"目標時間：{habit['target_time']}")

count, last_click_date = tracker.get_click_status(logs)

st.metric("連続達成日数", f"{count} 日")

# ----------------------
# 完了判定
# ----------------------

if tracker.is_completed(count):
    st.success("🎉 チャレンジ達成！")

    if st.button("履歴に保存して終了"):
        tracker.archive(
            user_id,
            habit["name"] + "（達成）",
            habit["target_time"],
        )
        tracker.reset_logs(user_id)
        data_manager.delete_user_habit(user_id)
        st.rerun()

    st.stop()


# ----------------------
# 今日のクリック
# ----------------------

can_click = tracker.can_click_today(last_click_date)

if can_click:
    if st.button("✅ 今日の習慣を達成した"):
        tracker.record_today(user_id)
        st.rerun()
else:
    st.info("今日はすでに記録済みです")

    if st.button("↩ 記録を取り消す"):
        tracker.delete_today_log(user_id)
        st.rerun()


# ======================
# 履歴表示
# ======================

with st.expander("📜 過去の履歴を見る"):
    history = data_manager.load_history(user_id)

    if not history:
        st.write("履歴はまだありません")
    else:
        for h in history:
            st.markdown(
                f"""
                **{h['habit_name']}**  
                期間：{h['total_days']}日  
                終了日：{h['archived_at'][:10]}
                """
            )
            st.divider()
