import datetime
import statistics
from datetime import date

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from supabase import create_client, Client

from constants import *
from auth_manager import AuthManager
from data_manager_supabase import DataManagerSupabase
from habit_tracker import HabitTracker

# =====================================================
# 初期化（resource cache）
# =====================================================

@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

supabase = get_supabase()
auth = AuthManager(supabase)
dm = DataManagerSupabase(supabase)
tracker = HabitTracker(supabase)

# =====================================================
# data cache
# =====================================================

@st.cache_data(ttl=60)
def load_user_habit_cached(user_id):
    return dm.load_user_habit(user_id)

@st.cache_data(ttl=30)
def load_logs_cached(user_id):
    return tracker.get_logs(user_id)

@st.cache_data(ttl=300)
def load_history_cached(user_id):
    return dm.load_history(user_id)

# =====================================================
# LINE通知（ロジック維持）
# =====================================================

def send_line_notification_to_user(supabase: Client, message: str, user_id: str):
    try:
        res = (
            supabase
            .table("user_line_settings")
            .select("line_user_id, notification_enabled")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not res.data or not res.data["notification_enabled"]:
            return

        line_user_id = res.data.get("line_user_id")
        if not line_user_id:
            return

        supabase.functions.invoke(
            "send-line-notifications",
            invoke_options={
                "body": {
                    "userId": line_user_id,
                    "message": message
                }
            }
        )
    except Exception as e:
        print("LINE通知エラー:", e)

# =====================================================
# CSS（最小・集中）
# =====================================================

def inject_css():
    st.markdown("""
    <style>
    .card {
        padding: 1.5rem;
        border-radius: 12px;
        background: #f5f6fa;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================
# fragment：重い描画
# =====================================================

@st.fragment
def render_progress_chart(logs, max_days):
    if not logs:
        st.info("まだ記録がありません")
        return

    df = pd.DataFrame(logs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    avg = statistics.mean(df["count"])

    col1, col2 = st.columns(2)
    col1.metric("平均達成数", f"{avg:.1f}")
    col2.metric("記録日数", len(df))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df["count"], marker="o")
    ax.set_ylim(0, max_days)
    ax.set_xlabel("日付")
    ax.set_ylabel("達成数")
    ax.grid(True, alpha=0.4)

    st.pyplot(fig)

@st.fragment
def render_milestone(icon, title, msg):
    st.markdown(f"""
    <div class="card" style="text-align:center;">
        <div style="font-size:3rem">{icon}</div>
        <h3>{title}</h3>
        <p>{msg}</p>
    </div>
    """, unsafe_allow_html=True)

@st.fragment
def render_decision_view(user_id, habit):
    st.error("⚠️ 数日間記録がなかったため、連続日数がリセットされます")
    st.write("この習慣をどうしますか？")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 続ける", use_container_width=True):
            tracker.reset_logs(user_id)
            st.session_state.challenge_phase = None
            st.cache_data.clear()
            st.rerun()

    with col2:
        if st.button("📝 習慣を変更", use_container_width=True):
            tracker.archive(user_id, habit["name"], habit["target_time"])
            tracker.reset_logs(user_id)
            dm.delete_user_habit(user_id)
            st.session_state.page = "settings"
            st.session_state.challenge_phase = None
            st.cache_data.clear()
            st.rerun()

# =====================================================
# セッション初期化
# =====================================================

def init_session():
    defaults = {
        "page": "challenge",
        "challenge_phase": None,
        "milestone_message": None,
        "balloons_triggered": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# =====================================================
# Challenge
# =====================================================

def render_challenge(user_id):
    habit = load_user_habit_cached(user_id)
    logs = load_logs_cached(user_id)

    if not habit:
        st.warning("習慣が設定されていません")
        return

    st.title(f"🎯 {habit['name']}")

    count, last_date = tracker.get_click_status(logs)

    # decisionフェーズ
    if last_date:
        last = datetime.datetime.strptime(last_date, DATE_FORMAT).date()
        if (date.today() - last).days > MISS_DAYS_THRESHOLD and count > 0:
            st.session_state.challenge_phase = "decision"

    if st.session_state.challenge_phase == "decision":
        render_decision_view(user_id, habit)
        return

    # 記録
    if tracker.can_click_today(last_date):
        if st.button("✅ 今日の習慣を記録する", use_container_width=True):
            tracker.record_today(user_id)
            st.cache_data.clear()

            new_count = count + 1
            milestone = {
                3: ("🌱", "3日達成", "良いスタート！"),
                7: ("🔥", "1週間達成", "習慣化の第一歩"),
                14: ("💪", "2週間達成", "すごい継続力"),
                30: ("🏆", "30日完全達成", "おめでとう！")
            }.get(new_count)

            if milestone:
                st.session_state.milestone_message = milestone
                send_line_notification_to_user(
                    supabase,
                    f"{milestone[1]}：{habit['name']}",
                    user_id
                )
                st.balloons()

            st.rerun()
    else:
        st.success("今日はすでに記録済みです")

    st.metric("連続日数", count)

    if st.session_state.milestone_message:
        render_milestone(*st.session_state.milestone_message)
        st.session_state.milestone_message = None

    render_progress_chart(logs, MAX_CHALLENGE_DAYS)

# =====================================================
# History
# =====================================================

def render_history(user_id):
    st.title("🏆 達成履歴")

    history = load_history_cached(user_id)
    if not history:
        st.info("まだ履歴はありません")
        return

    for r in history:
        with st.expander(f"{r['habit_name']}（{r['total_days']}日）"):
            render_progress_chart(r["log_summary"], r["total_days"])

# =====================================================
# Main
# =====================================================

def main():
    init_session()
    inject_css()

    user = auth.get_current_user()
    if not user:
        st.warning("ログインしてください")
        return

    user_id = user["id"]

    st.sidebar.title("メニュー")
    page = st.sidebar.radio(
        "移動",
        ["challenge", "history"],
        index=0 if st.session_state.page == "challenge" else 1
    )
    st.session_state.page = page

    if page == "challenge":
        render_challenge(user_id)
    else:
        render_history(user_id)

if __name__ == "__main__":
    main()
