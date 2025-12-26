import datetime
import random
import statistics
import time
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from supabase import create_client, Client

from constants import *
from auth_manager import AuthManager
from data_manager_supabase import DataManagerSupabase
from habit_tracker import HabitTracker

# ------------------------------
# LINE通知関数
# ------------------------------

def send_line_notification_to_user(supabase: Client, message: str, user_id: str) -> bool:
    """ユーザーにLINE通知を送信"""
    try:
        result = (
            supabase
            .table("user_line_settings")
            .select("line_user_id, notification_enabled")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            return True

        settings = result.data[0]

        if not settings.get("notification_enabled", False):
            return True

        line_user_id = settings.get("line_user_id")
        if not line_user_id:
            return True

        response = supabase.functions.invoke(
            "send-line-notifications",
            invoke_options={
                "body": {
                    "message": message,
                    "userId": line_user_id
                }
            }
        )

        if response is None:
            st.error("LINE通知のレスポンスがありません")
            return False

        if getattr(response, "error", None):
            st.error(f"LINE通知エラー: {response.error}")
            return False

        return True

    except Exception as e:
        st.error(f"LINE通知例外: {e}")
        return False


# ------------------------------
# LINE設定UI
# ------------------------------

def render_line_settings(user_id, supabase):
    st.markdown("### 🔔 LINE通知設定")

    try:
        result = (
            supabase
            .table("user_line_settings")
            .select("notification_enabled")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        settings = result.data
    except Exception:
        settings = None

    if not settings:
        st.error("⚠️ LINE通知設定が見つかりません")
        return

    enabled = st.toggle(
        "通知を有効にする",
        value=settings.get("notification_enabled", True)
    )

    if enabled != settings.get("notification_enabled", True):
        supabase.table("user_line_settings").update(
            {"notification_enabled": enabled}
        ).eq("user_id", user_id).execute()
        st.success("設定を更新しました")
        time.sleep(0.5)
        st.rerun()


# ------------------------------
# Streamlit設定
# ------------------------------

st.set_page_config(
    page_title="習慣化支援Webアプリ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------
# Supabase初期化
# ------------------------------

supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

auth = AuthManager(supabase)
dm = DataManagerSupabase(supabase)
tracker = HabitTracker(dm)

# ------------------------------
# 共通UI
# ------------------------------

def render_progress_bar(current, total):
    progress = current / total if total else 0
    st.progress(progress)
    st.markdown(
        f"<p style='text-align:center; font-size:1.2rem;'><b>{current}</b> / {total} 日達成</p>",
        unsafe_allow_html=True
    )


def check_milestone(count):
    milestones = {
        3: ("🌱", "3日目突破！", "素晴らしいスタートです！"),
        7: ("🔥", "1週間達成！", "習慣化の第一歩！"),
        14: ("💪", "2週間達成！", "折り返し地点です！"),
        21: ("⭐", "3週間達成！", "かなり定着してきました！"),
        30: ("🏆", "30日完全達成！", "おめでとうございます！")
    }
    return milestones.get(count)


def render_progress_chart(logs, max_days=30):
    if not logs:
        st.info("まだ記録がありません")
        return

    df = pd.DataFrame(logs)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values("log_date").tail(max_days)

    hours = df["completion_hour"].dropna()
    avg_hour = statistics.mean(hours) if not hours.empty else 0

    col1, col2 = st.columns(2)
    col1.metric("📈 平均達成時刻", f"{avg_hour:.1f}時")
    col2.metric("📅 記録日数", f"{len(df)}日")

    df["count"] = range(1, len(df) + 1)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["count"], df["completion_hour"], marker="o")

    ax.set_ylim(-1, 24)
    ax.set_xlim(1, max_days)
    ax.set_ylabel("達成時刻（時）")
    ax.set_xlabel("連続日数")
    ax.set_title("習慣の達成時刻の推移")
    ax.grid(True)

    st.pyplot(fig)


# ------------------------------
# Pages
# ------------------------------

def render_challenge(user_id):
    habit = dm.load_user_habit(user_id)
    logs = tracker.get_logs(user_id)
    count, last_date = tracker.get_click_status(logs)

    render_progress_bar(count, MAX_CHALLENGE_DAYS)

    if tracker.can_click_today(last_date):
        if st.button("✅ 今日の習慣を記録する", use_container_width=True):
            tracker.record_today(user_id)
            new_count = count + 1

            milestone = check_milestone(new_count)
            if milestone:
                key = f"milestone_sent_{new_count}"
                if key not in st.session_state:
                    send_line_notification_to_user(
                        supabase,
                        f"{milestone[0]} {milestone[1]}\n{milestone[2]}",
                        user_id
                    )
                    st.session_state[key] = True

            st.rerun()
    else:
        st.success("今日は既に記録済みです")

    render_progress_chart(logs)


def render_history(user_id):
    st.header("🏆 達成履歴")
    history = dm.load_history(user_id)

    if not history:
        st.info("まだ履歴はありません")
        return

    for r in history:
        with st.expander(f"{r['habit_name']} ({r['total_days']}日)"):
            render_progress_chart(r.get("log_summary", []), r["total_days"])


# ------------------------------
# Main
# ------------------------------

def main():
    if not auth.is_authenticated():
        st.info("ログインしてください")
        return

    user = auth.get_user()
    user_id = user.id

    if "page" not in st.session_state:
        habit = dm.load_user_habit(user_id)
        st.session_state.page = "challenge" if habit else "settings"

    st.sidebar.radio(
        "ページ",
        ["challenge", "history"],
        key="page"
    )

    if st.sidebar.button("🔔 LINEテスト通知"):
        ok = send_line_notification_to_user(
            supabase,
            "🔔 テスト通知です",
            user_id
        )
        if ok:
            st.sidebar.success("送信しました")
        else:
            st.sidebar.error("送信失敗")

    if st.session_state.page == "challenge":
        render_challenge(user_id)
    elif st.session_state.page == "history":
        render_history(user_id)


if __name__ == "__main__":
    main()
