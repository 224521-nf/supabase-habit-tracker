import datetime
import random
import statistics
import time
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta
from supabase import create_client, Client

# 外部モジュールのインポート（これらは既存のファイルとして存在前提）
from constants import *
from auth_manager import AuthManager
from data_manager_supabase import DataManagerSupabase
from habit_tracker import HabitTracker

# ------------------------------
# 設定・初期化
# ------------------------------

# テスト時はTrueにしてください
DEBUG_MODE = True 

@st.cache_resource
def get_supabase_client():
    """Supabaseクライアントのキャッシュ化"""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

supabase = get_supabase_client()
auth = AuthManager(supabase)
dm = DataManagerSupabase(supabase)
tracker = HabitTracker(dm)

# ------------------------------
# LINE通知関数
# ------------------------------

def send_line_notification_to_user(supabase: Client, message: str, user_id: str):
    """ユーザーにLINE通知を送信"""
    try:
        result = supabase.table("user_line_settings").select("line_user_id, notification_enabled").eq("user_id", user_id).execute()
        if not result.data:
            return True
        
        settings = result.data[0]
        if not settings.get("notification_enabled", False):
            return True
        
        line_user_id = settings.get("line_user_id")
        if not line_user_id:
            return True
        
        response = supabase.functions.invoke(
            'send-line-notifications',
            invoke_options={
                'body': {
                    'message': message,
                    'userId': line_user_id
                }
            }
        )
        
        if hasattr(response, 'error') and response.error:
            st.error(f"LINE通知エラー: {response.error}")
            return False
            
        return True
    except Exception as e:
        st.error(f"エラー: {e}")
        return False

# ------------------------------
# 共通UIコンポーネント
# ------------------------------

def render_line_settings(user_id, supabase):
    """LINE通知設定UI"""
    st.markdown("### 🔔 LINE通知設定")
    try:
        result = supabase.table("user_line_settings").select("notification_enabled").eq("user_id", user_id).single().execute()
        settings = result.data
    except Exception:
        settings = None

    if not settings:
        st.error("⚠️ LINE通知設定が見つかりません")
        return

    st.success("✅ LINE通知は設定済みです")
    enabled = st.toggle("通知を有効にする", value=settings.get("notification_enabled", True), key="notification_toggle")

    if enabled != settings.get("notification_enabled", True):
        try:
            supabase.table("user_line_settings").update({"notification_enabled": enabled}).eq("user_id", user_id).execute()
            st.success("設定を更新しました")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"更新エラー: {e}")

def render_progress_bar(current, total):
    progress = min(current / total, 1.0)
    st.progress(progress)
    st.markdown(f"<p style='text-align: center; font-size: 1.2rem;'><b>{current}</b> / {total} 日達成</p>", unsafe_allow_html=True)

def check_milestone(count):
    milestones = {
        3: ("🌱", "3日目突破！", "素晴らしいスタートです！"),
        7: ("🔥", "1週間達成！", "習慣化の第一歩をクリアしました！"),
        14: ("💪", "2週間達成！", "もう折り返し地点です！すごい！"),
        21: ("⭐", "3週間達成！", "習慣が身についてきました！あと少し！"),
        30: ("🏆", "30日完全達成！", "おめでとうございます！完璧です！")
    }
    return milestones.get(count, None)

def render_progress_chart(logs, max_days=30):
    if not logs:
        st.info("📊 まだ記録がありません。")
        return

    df = pd.DataFrame(logs)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values(by="log_date").tail(max_days)
    
    avg_hour = statistics.mean(df["completion_hour"])
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📈 平均達成時間", f"{avg_hour:.1f}時")
    with col2:
        st.metric("📅 記録日数", f"{len(df)}日")
   
    fig, ax = plt.subplots(figsize=(10, 4))
    df['count_idx'] = range(1, len(df) + 1)
    ax.plot(df["count_idx"], df["completion_hour"], marker="o", linestyle="-", color="#ff4b4b", linewidth=2, markersize=6)
    ax.set_ylim(-1, 24)
    ax.set_xlim(1, 30)
    ax.set_yticks(range(0, 25, 4))
    ax.set_ylabel("Hour", fontweight='bold')
    ax.set_xlabel("Days", fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.4)
    st.pyplot(fig)

# ------------------------------
# 各ページ描画
# ------------------------------

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🎯 習慣化支援</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["ログイン", "新規登録"])
        with tab1:
            email = st.text_input("メールアドレス", key="l_email")
            pw = st.text_input("パスワード", type="password", key="l_pw")
            if st.button("ログイン", use_container_width=True, type="primary"):
                auth.login(email, pw)
                st.rerun()
        with tab2:
            email = st.text_input("メールアドレス", key="s_email")
            pw = st.text_input("パスワード", type="password", key="s_pw")
            if st.button("新規登録", use_container_width=True):
                auth.signup(email, pw)
                st.rerun()

def render_settings(user_id):
    st.markdown("<h1 style='text-align: center;'>🎯 新しい習慣を設定</h1>", unsafe_allow_html=True)
    with st.expander("🔔 LINE通知設定", expanded=False):
        render_line_settings(user_id, supabase)
    
    habit = dm.load_user_habit(user_id)
    name = st.text_input("習慣の内容", value=habit.get("name", "") if habit else "")
    
    t_val = TIME_INPUT_DEFAULT
    if habit and habit.get("target_time"):
        h, m = map(int, habit["target_time"].split(":"))
        t_val = datetime.time(h, m)
    
    time_input = st.time_input('目標時刻', value=t_val)
    
    if st.button('🚀 チャレンジを開始！', use_container_width=True, type="primary"):
        if name:
            supabase.table("habits").upsert({
                "user_id": user_id, "name": name, "target_time": time_input.strftime("%H:%M"), "active": True
            }, on_conflict="user_id").execute()
            send_line_notification_to_user(supabase, f"🎯 チャレンジ開始！\n「{name}」", user_id)
            st.session_state.page = "challenge"
            st.rerun()

def render_challenge(user_id):
    habit = dm.load_user_habit(user_id)
    if not habit:
        st.warning("習慣を設定してください")
        if st.button("設定へ"): 
            st.session_state.page = "settings"
            st.rerun()
        return

    st.markdown(f"<h2 style='text-align: center;'>🎯 {habit['name']}</h2>", unsafe_allow_html=True)
    logs = tracker.get_logs(user_id)
    count, last_date = tracker.get_click_status(logs)
    
    render_progress_bar(count, MAX_CHALLENGE_DAYS)
    
    col1, col2 = st.columns(2)
    col1.metric("🔥 連続", f"{count}日")
    col2.metric("🎯 残り", f"{MAX_CHALLENGE_DAYS - count}日")

    if tracker.is_completed(count):
        st.balloons()
        st.success("🏆 30日達成おめでとうございます！")
        if st.button("次の習慣へ"):
            tracker.archive(user_id, habit["name"], habit["target_time"])
            tracker.reset_logs(user_id)
            dm.delete_user_habit(user_id)
            st.session_state.page = "settings"
            st.rerun()
    elif tracker.can_click_today(last_date):
        if st.button("✅ 今日の習慣を記録", use_container_width=True, type="primary"):
            tracker.record_today(user_id)
            st.rerun()
    else:
        st.info("✅ 本日は記録済みです。また明日！")

def render_history(user_id):
    st.markdown("<h1 style='text-align: center;'>🏆 履歴</h1>", unsafe_allow_html=True)
    history = dm.load_history(user_id)
    if not history:
        st.info("履歴はありません。")
        return
    for r in history:
        with st.expander(f"🏅 {r['habit_name']} ({r['total_days']}日達成)"):
            render_progress_chart(r.get("log_summary", []))

# ------------------------------
# メインロジック
# ------------------------------

def main():
    st.set_page_config(page_title="習慣化アプリ", layout="wide")
    
    if not auth.is_authenticated():
        render_login()
        return

    user_id = auth.get_user().id
    
    # ページ初期化
    if "page" not in st.session_state:
        habit = dm.load_user_habit(user_id)
        st.session_state.page = "challenge" if habit and habit.get("name") else "settings"

    # サイドバーメニュー
    st.sidebar.title("メニュー")
    if st.sidebar.button("🎯 チャレンジ画面"): st.session_state.page = "challenge"; st.rerun()
    if st.sidebar.button("🏆 履歴"): st.session_state.page = "history"; st.rerun()
    if st.sidebar.button("⚙️ 設定"): st.session_state.page = "settings"; st.rerun()
    
    # デバッグメニュー
    if DEBUG_MODE:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🛠 テスト用")
        with st.sidebar.expander("データ操作"):
            test_count = st.number_input("日数をセット", 0, 30, 0)
            if st.button(f"{test_count}日分生成"):
                tracker.reset_logs(user_id)
                for i in range(test_count):
                    d = (datetime.date.today() - timedelta(days=test_count-1-i)).strftime(DATE_FORMAT)
                    supabase.table("progress_logs").insert({
                        "user_id": user_id, "log_date": d, "completion_hour": random.randint(7, 22)
                    }).execute()
                st.rerun()
            if st.button("全リセット"):
                tracker.reset_logs(user_id)
                dm.delete_user_habit(user_id)
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 ログアウト"):
        auth.logout()
        st.rerun()

    # ページ表示
    if st.session_state.page == "settings": render_settings(user_id)
    elif st.session_state.page == "challenge": render_challenge(user_id)
    elif st.session_state.page == "history": render_history(user_id)

if __name__ == "__main__":
    main()