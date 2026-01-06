import datetime
import random
import statistics
import time
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
# キャッシュ付き初期化
# =====================================================

@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

supabase: Client = get_supabase()
auth_manager = AuthManager(supabase)
dm = DataManagerSupabase(supabase)
tracker = HabitTracker(supabase)

# =====================================================
# キャッシュ付き DB 取得
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
# LINE 通知（ロジックは変更なし）
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
# 重い描画は fragment 化
# =====================================================

def render_progress_chart(logs, max_days=30):
    df = pd.DataFrame(logs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig, ax = plt.subplots()
    ax.plot(df["date"], df["count"])
    ax.set_ylim(0, max_days)
    ax.set_xlabel("日付")
    ax.set_ylabel("達成数")

    st.pyplot(fig)

@st.fragment
def render_progress_chart_fragment(logs, max_days=30):
    render_progress_chart(logs, max_days)

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
# Challenge 画面
# =====================================================

def render_challenge(user_id):
    habit = load_user_habit_cached(user_id)
    logs = load_logs_cached(user_id)

    st.title("今日の習慣チャレンジ")

    # -----------------------
    # 記録ボタン
    # -----------------------
    if st.button("今日も実行した！"):
        tracker.record_today(user_id)
        st.cache_data.clear()   # DB更新後なので安全にクリア
        st.rerun()

    # -----------------------
    # 状態表示
    # -----------------------
    count, last_date = tracker.get_click_status(logs)
    st.metric("継続日数", count)

    # -----------------------
    # マイルストーン
    # -----------------------
    if count in [3, 7, 14, 30] and not st.session_state.balloons_triggered:
        st.session_state.milestone_message = f"🎉 {count}日達成！"
        st.session_state.balloons_triggered = True
        st.balloons()

    if st.session_state.milestone_message:
        st.success(st.session_state.milestone_message)

    # -----------------------
    # グラフ（fragment）
    # -----------------------
    render_progress_chart_fragment(logs, MAX_CHALLENGE_DAYS)

# =====================================================
# 履歴画面
# =====================================================

def render_history(user_id):
    st.title("履歴")

    history = load_history_cached(user_id)
    df = pd.DataFrame(history)

    st.dataframe(df)

# =====================================================
# メイン
# =====================================================

def main():
    init_session()

    user = auth_manager.get_current_user()
    if not user:
        st.warning("ログインしてください")
        return

    user_id = user["id"]

    st.sidebar.title("メニュー")
    page = st.sidebar.radio(
        "移動",
        options=["challenge", "history"],
        index=0 if st.session_state.page == "challenge" else 1
    )
    st.session_state.page = page

    if page == "challenge":
        render_challenge(user_id)
    elif page == "history":
        render_history(user_id)

if __name__ == "__main__":
    main()
