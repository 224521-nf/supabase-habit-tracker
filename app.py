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
# Utility & Notifications
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
# UI Components
# ------------------------------

def apply_custom_style():
    """カスタムCSSの適用"""
    st.markdown("""
    <style>
        .stProgress > div > div > div > div { background-color: #ff4b4b; }
        [data-testid="stMetricValue"] { font-size: 2rem; font-weight: bold; }
        .stButton > button { font-size: 1.1rem; padding: 0.75rem 1.5rem; border-radius: 10px; font-weight: 600; }
        .card { padding: 1.5rem; border-radius: 10px; background-color: #f0f2f6; margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

def render_progress_bar(current, total):
    """プログレスバーを表示"""
    progress = current / total
    st.progress(progress)
    st.markdown(f"<p style='text-align: center; font-size: 1.2rem;'><b>{current}</b> / {total} 日達成</p>", unsafe_allow_html=True)

def check_milestone(count):
    """マイルストーンをチェック"""
    milestones = {
        3: ("🌱", "3日目突破！", "素晴らしいスタートです！"),
        7: ("🔥", "1週間達成！", "習慣化の第一歩をクリアしました！"),
        14: ("💪", "2週間達成！", "もう折り返し地点です！すごい！"),
        21: ("⭐", "3週間達成！", "習慣が身についてきました！あと少し！"),
        30: ("🏆", "30日完全達成！", "おめでとうございます！完璧です！")
    }
    return milestones.get(count)

def render_progress_chart(logs, max_days=30):
    """達成ログのチャート表示"""
    if not logs:
        st.info("📊 まだ記録がありません。最初の一歩を踏み出しましょう！")
        return

    df = pd.DataFrame(logs)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values(by="log_date").tail(max_days)
    
    avg_hour = statistics.mean(df["completion_hour"])
    
    c1, c2 = st.columns(2)
    c1.metric("📈 平均達成時間", f"{avg_hour:.1f}時")
    c2.metric("📅 記録日数", f"{len(df)}日")
   
    fig, ax = plt.subplots(figsize=(10, 5))
    df['count'] = range(1, len(df) + 1)
    
    ax.plot(df["count"], df["completion_hour"], marker="o", linestyle="-", color="#ff4b4b", linewidth=2.5, markersize=8)
    ax.set_ylim(-1, 25)
    ax.set_xlim(1, 30)
    ax.set_yticks(range(0, 25, 2))
    ax.set_xticks(range(1, 31))
    ax.set_ylabel("click_hour", fontweight='bold')
    ax.set_xlabel("click_count", fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_title("Achievement time per click", fontsize=14, fontweight='bold')
    ax.set_facecolor('#fafafa')
    
    st.pyplot(fig)

# ------------------------------
# Settings UI
# ------------------------------

def render_line_settings(user_id, supabase):
    """LINE通知設定UI"""
    st.markdown("### 🔔 LINE通知設定")
    
    current_settings = None
    try:
        result = supabase.table("user_line_settings").select("*").eq("user_id", user_id).execute()
        current_settings = result.data[0] if result.data else None
    except:
        pass
    
    if current_settings and current_settings.get("line_user_id"):
        st.success("✅ LINE通知が設定されています")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**User ID:** {current_settings['line_user_id'][:10]}...")
        with col2:
            enabled = st.toggle("通知を有効にする", value=current_settings.get("notification_enabled", True), key="notification_toggle")
            if enabled != current_settings.get("notification_enabled", True):
                try:
                    supabase.table("user_line_settings").update({"notification_enabled": enabled}).eq("user_id", user_id).execute()
                    st.success("設定を更新しました")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"更新エラー: {e}")
        
        with st.expander("設定を変更する"):
            new_line_id = st.text_input("新しいLINE User ID", placeholder="Uから始まる33文字")
            if st.button("更新", use_container_width=True):
                if new_line_id and new_line_id.startswith("U") and len(new_line_id) == 33:
                    try:
                        supabase.table("user_line_settings").update({"line_user_id": new_line_id}).eq("user_id", user_id).execute()
                        st.success("LINE User IDを更新しました")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"更新エラー: {e}")
                else:
                    st.error("正しいLINE User IDを入力してください")
    else:
        st.warning("⚠️ LINE通知が設定されていません")
        with st.expander("📖 LINE User IDの取得方法", expanded=True):
            st.markdown("1. LINE Developersコンソール... (略)") # 省略表記ですが元の文を維持
        
        line_user_id = st.text_input("LINE User ID", placeholder="例: Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        if st.button("保存", use_container_width=True, type="primary"):
            if line_user_id and line_user_id.startswith("U") and len(line_user_id) == 33:
                try:
                    supabase.table("user_line_settings").upsert({
                        "user_id": user_id, "line_user_id": line_user_id, "notification_enabled": True
                    }, on_conflict="user_id").execute()
                    st.success("LINE通知を設定しました！")
                    send_line_notification_to_user(supabase, "🎉 LINE通知の設定が完了しました！", user_id)
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"保存エラー: {e}")
            else:
                st.error("正しい形式のLINE User IDを入力してください")

# ------------------------------
# Page Renders
# ------------------------------

def render_login(auth):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'> 習慣化支援アプリ</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["ログイン", "新規登録"])
        
        with tab1:
            e = st.text_input("メールアドレス", key="login_email")
            p = st.text_input("パスワード", type="password", key="login_password")
            if st.button("ログイン", use_container_width=True, type="primary"):
                try:
                    auth.login(e, p)
                    st.success("ログイン成功！")
                    st.rerun()
                except Exception as ex: st.error(f"認証エラー: {ex}")
        
        with tab2:
            e = st.text_input("メールアドレス", key="signup_email")
            p = st.text_input("パスワード（6文字以上）", type="password", key="signup_password")
            if st.button("新規登録", use_container_width=True, type="primary"):
                if len(p) < 6: st.error("パスワードは6文字以上で設定してください")
                else:
                    try:
                        auth.signup(e, p)
                        st.success("登録成功！")
                        st.rerun()
                    except Exception as ex: st.error(f"登録エラー: {ex}")

def render_settings(user_id, dm, supabase):
    st.markdown("<h1 style='text-align: center;'>🎯 新しい習慣を始めよう</h1>", unsafe_allow_html=True)
    
    habit = dm.load_user_habit(user_id)
    name = st.text_input("習慣の内容", value=habit.get("name", "") if habit else "")
    
    # バリデーション
    if name:
        if '5分' in name or len(name) < 30: st.success("✅ 良い習慣です！")
        elif len(name) > 50: st.warning("⚠️ 少し長すぎるかも。")

    t_val = TIME_INPUT_DEFAULT
    if habit and habit.get("target_time"):
        h, m = map(int, habit["target_time"].split(":"))
        t_val = datetime.time(h, m)
    
    time_input = st.time_input('目標時刻', value=t_val)
    
    if name and time_input:
        st.markdown("---")
        if st.button('🚀 この習慣で30日チャレンジを開始！', use_container_width=True, type="primary"):
            try:
                supabase.table("habits").upsert({
                    "user_id": user_id, "name": name, "target_time": time_input.strftime("%H:%M"), "active": True
                }, on_conflict="user_id").execute()
                send_line_notification_to_user(supabase, f"🎯 新しい習慣をスタート！\n「{name}」", user_id)
                st.session_state.page = "challenge"
                st.rerun()
            except Exception as e: st.error(f"エラー: {e}")

def render_challenge(user_id, dm, tracker, supabase):
    habit = dm.load_user_habit(user_id)
    if not habit:
        st.warning("まず習慣を設定してください")
        if st.button("習慣を設定する"): 
            st.session_state.page = "settings"
            st.rerun()
        return

    st.markdown(f"<h1 style='text-align: center;'>🎯 {habit['name']}</h1>", unsafe_allow_html=True)
    
    logs = tracker.get_logs(user_id)
    count, last_date = tracker.get_click_status(logs)
    
    # リセット判定
    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, DATE_FORMAT).date()
        if (datetime.date.today() - last_date_obj).days > MISS_DAYS_THRESHOLD and count > 0:
            st.error(f'😢 {MISS_DAYS_THRESHOLD}日以上経過したためリセットしました')
            send_line_notification_to_user(supabase, "⚠️ 習慣がリセットされました", user_id)
            tracker.reset_logs(user_id)
            st.rerun()

    # Session State
    for key in ['cheers_message', 'milestone_message', 'balloons_triggered']:
        if key not in st.session_state: st.session_state[key] = None if key != 'balloons_triggered' else False

    render_progress_bar(count, MAX_CHALLENGE_DAYS)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🔥 連続記録", f"{count}日")
    col2.metric("📅 最終記録日", last_date or "---")
    col3.metric("🎯 残り日数", f"{MAX_CHALLENGE_DAYS - count}日")

    if st.session_state.milestone_message:
        icon, title, msg = st.session_state.milestone_message
        st.markdown(f"<div style='text-align: center; background: #764ba2; color: white;'><h2>{icon} {title}</h2><p>{msg}</p></div>", unsafe_allow_html=True)
        st.session_state.milestone_message = None

    if tracker.is_completed(count):
        if not st.session_state.balloons_triggered:
            st.balloons()
            st.session_state.balloons_triggered = True
            send_line_notification_to_user(supabase, "🏆 30日完全達成おめでとう！", user_id)
        
        if st.button("🎉 次の習慣にチャレンジする", type="primary"):
            tracker.archive(user_id, habit["name"], habit["target_time"])
            tracker.reset_logs(user_id)
            dm.delete_user_habit(user_id)
            st.session_state.page = "settings"
            st.rerun()
    
    elif tracker.can_click_today(last_date):
        if st.button("✅ 今日の習慣を記録する", use_container_width=True, type="primary"):
            tracker.record_today(user_id)
            milestone = check_milestone(count + 1)
            if milestone:
                st.session_state.milestone_message = milestone
                st.balloons()
                send_line_notification_to_user(supabase, f"{milestone[0]} {milestone[1]}", user_id)
            else:
                st.session_state.cheers_message = random.choice(["🎉 素晴らしい！", "💪 その調子！"])
            st.rerun()
    else:
        st.success("✅ 今日は既に記録済みです")
        with st.expander("❌ 間違えて記録した場合"):
            if st.button("🔄 直前の記録を取り消す"):
                tracker.delete_today_log(user_id)
                st.rerun()

    if st.session_state.cheers_message:
        st.info(st.session_state.cheers_message)
        st.session_state.cheers_message = None

def render_history(user_id, dm):
    st.markdown("<h1 style='text-align: center;'>🏆 達成履歴</h1>", unsafe_allow_html=True)
    history = dm.load_history(user_id)
    if not history:
        st.info("📝 まだ履歴はありません")
        return
    
    st.metric("🎯 達成数", f"{len(history)}個")
    for i, r in enumerate(history, 1):
        with st.expander(f'🏅 {i}. {r["habit_name"]} ({r["total_days"]}日達成)'):
            render_progress_chart(r.get("log_summary", []), r["total_days"])

# ------------------------------
# Main Application
# ------------------------------

def main():
    st.set_page_config(page_title="習慣化支援Webアプリ", layout="wide", initial_sidebar_state="collapsed")
    apply_custom_style()

    try:
        supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Supabase接続エラー: {e}")
        st.stop()

    auth = AuthManager(supabase)
    dm = DataManagerSupabase(supabase)
    tracker = HabitTracker(dm)

    if not auth.is_authenticated():
        render_login(auth)
        return

    user_id = auth.get_user().id
    session = auth.get_session()
    if session and session.access_token:
        supabase.postgrest.auth(session.access_token)

    # ページ初期化
    habit = dm.load_user_habit(user_id)
    has_active_habit = bool(habit and habit.get("name"))
    
    if "page" not in st.session_state:
        st.session_state.page = "challenge" if has_active_habit else "settings"

    # サイドバー
    st.sidebar.title("📱 メニュー")
    if has_active_habit:
        page_labels = {"challenge": "🎯 挑戦中", "history": "🏆 履歴"}
        choice = st.sidebar.radio("移動", options=list(page_labels.keys()), format_func=lambda x: page_labels[x])
        if choice != st.session_state.page:
            st.session_state.page = choice
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.info(f"**現在の習慣:**\n{habit['name']}\n⏰ {habit['target_time']}")
        
        with st.sidebar.expander("🔔 LINE通知設定"):
            render_line_settings(user_id, supabase)
            if st.button("テスト通知送信"):
                send_line_notification_to_user(supabase, "🔔 テスト通知です", user_id)
    else:
        st.sidebar.info("習慣を設定してください")

    if st.sidebar.button("🚪 ログアウト"):
        auth.logout()
        st.rerun()

    # メイン表示
    if st.session_state.page == "settings":
        render_settings(user_id, dm, supabase)
    elif st.session_state.page == "challenge":
        render_challenge(user_id, dm, tracker, supabase)
    elif st.session_state.page == "history":
        render_history(user_id, dm)

if __name__ == "__main__":
    main()