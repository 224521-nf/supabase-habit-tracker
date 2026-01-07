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

def send_line_notification_to_user(supabase: Client, message: str, user_id: str):
    """ユーザーにLINE通知を送信"""
    try:
        # LINE User IDを取得
        result = supabase.table("user_line_settings").select("line_user_id, notification_enabled").eq("user_id", user_id).execute()
        
        if not result.data:
            # 設定がない場合はスキップ
            return True
        
        settings = result.data[0]
        
        if not settings.get("notification_enabled", False):
            # 通知が無効の場合はスキップ
            return True
        
        line_user_id = settings.get("line_user_id")
        if not line_user_id:
            return True
        
        # 修正: invoke_optionsを使う
        response = supabase.functions.invoke(
            'send-line-notifications',
            invoke_options={
                'body': {
                    'message': message,
                    'userId': line_user_id
                }
            }
        )
        
        # レスポンスの確認
        if hasattr(response, 'error') and response.error:
            st.error(f"LINE通知エラー: {response.error}")
            return False
            
        return True
    
    except Exception as e:
        print(f"LINE通知エラー: {e}")
        st.error(f"エラー: {e}")
        return False

# ------------------------------
# LINE設定UI
# ------------------------------

def render_line_settings(user_id, supabase):
    """LINE通知設定UI（個人利用・登録済み前提）"""
    
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
        # 個人利用前提なので、ここに来るのは異常系
        st.error("⚠️ LINE通知設定が見つかりません")
        st.info("Supabase の user_line_settings を確認してください")
        return

    enabled = st.toggle(
        "通知を有効にする",
        value=settings.get("notification_enabled", True),
        key="notification_toggle"
    )

    if enabled != settings.get("notification_enabled", True):
        try:
            supabase.table("user_line_settings").update({
                "notification_enabled": enabled
            }).eq("user_id", user_id).execute()

            st.success("設定を更新しました")
            time.sleep(0.5)
            st.rerun()

        except Exception as e:
            st.error(f"更新エラー: {e}")

# ------------------------------
# Streamlit 設定
# ------------------------------

st.set_page_config(
    page_title="習慣化支援Webアプリ", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS
st.markdown("""
<style>
    /* プログレスバーのスタイル */
    .stProgress > div > div > div > div {
        background-color: #ff4b4b;
    }

    
    /* ボタンの改善 */
    .stButton > button {
        font-size: 1.1rem;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* カード風のスタイル */
    .card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)
 
# ------------------------------
# Supabase 初期化
# ------------------------------

try:
    supabase: Client = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )
except KeyError as e:
    st.error(f"secrets.tomlに必要なキーがありません: {e}")
    st.stop()
except Exception as e:
    st.error(f"Supabaseに接続できません: {e}")
    st.stop()
 
auth = AuthManager(supabase)
dm = DataManagerSupabase(supabase)
tracker = HabitTracker(dm)
 
# ------------------------------
# Auth UI
# ------------------------------

def render_login():
    # 中央寄せのレイアウト
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🎯 習慣化支援アプリ</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>30日間で人生を変える習慣を身につけよう</p>", unsafe_allow_html=True)
        st.write("")
        st.write("")
        
        tab1, tab2 = st.tabs(["ログイン", "新規登録"])
        
        with tab1:
            email = st.text_input("メールアドレス", key="login_email")
            password = st.text_input("パスワード", type="password", key="login_password")
            
            if st.button("ログイン", use_container_width=True, type="primary"):
                if not email or not password:
                    st.error("メールアドレスとパスワードを入力してください")
                    return
                
                try:
                    auth.login(email, password)
                    st.success("ログイン成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"認証エラー: {e}")
        
        with tab2:
            email = st.text_input("メールアドレス", key="signup_email")
            password = st.text_input("パスワード（6文字以上）", type="password", key="signup_password")
            
            if st.button("新規登録", use_container_width=True, type="primary",help="一般ユーザーに権限がないため登録できない"):
                if not email or not password:
                    st.error("メールアドレスとパスワードを入力してください")
                    return
                
                if len(password) < 6:
                    st.error("パスワードは6文字以上で設定してください")
                    return
                
                try:
                    auth.signup(email, password)
                    st.success("登録成功！ログインしてください")
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")

# ------------------------------
# 共通UI
# ------------------------------

def render_progress_bar(current, total):
    """プログレスバーを表示"""
    progress = current / total
    st.progress(progress)
    st.markdown(f"<p style='text-align: center; font-size: 1.2rem;'><b>{current}</b> / {total} 日達成</p>", unsafe_allow_html=True)

def check_milestone(count):
    """マイルストーンをチェックして特別なメッセージを返す"""
    milestones = {
        3: ("🌱", "3日目突破！", "素晴らしいスタートです！"),
        7: ("🔥", "1週間達成！", "習慣化の第一歩をクリアしました！"),
        14: ("💪", "2週間達成！", "もう折り返し地点です！すごい！"),
        21: ("⭐", "3週間達成！", "習慣が身についてきました！あと少し！"),
        30: ("🏆", "30日完全達成！", "おめでとうございます！完璧です！")
    }
    
    return milestones.get(count, None)
 
def render_progress_chart(logs, max_days=30):
    """習慣の達成ログをプロットする"""
    if not logs:
        st.info("📊 まだ記録がありません。最初の一歩を踏み出しましょう！")
        return
 
    df = pd.DataFrame(logs)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values(by="log_date").tail(max_days)
    
    # 平均時間を計算
    avg_hour = statistics.mean(df["completion_hour"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📈 平均達成時間", f"{avg_hour:.1f}時", help="習慣を実行した平均時刻")
    with col2:
        st.metric("📅 記録日数", f"{len(df)}日", help="これまでに記録した日数")
   
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # 達成回数を計算
    df['count'] = range(1, len(df) + 1)
    
    ax.plot(df["count"], df["completion_hour"], 
            marker="o", linestyle="-", color="#ff4b4b", 
            linewidth=2.5, markersize=8)
   
    ax.set_ylim(-1, 24)
    ax.set_xlim(1, 30)
    
    ax.set_yticks(range(0, 24, 2))
    ax.set_xticks(range(1, 31))
    
    ax.set_ylabel("click_hour", fontsize=12, fontweight='bold')
    ax.set_xlabel("click_count", fontsize=12, fontweight='bold')
    
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_title("Achievement time per click", fontsize=14, fontweight='bold', pad=20)
    
    # 背景色を設定
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('white')
 
    plt.tight_layout()
    st.pyplot(fig)

# ------------------------------
# Pages
# ------------------------------
 
def render_settings(user_id):
    """習慣を設定するページ（改善版）"""
    
    # ヘッダー
    st.markdown("<h1 style='text-align: center;'>🎯 新しい習慣を始めよう</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; font-size: 1.1rem;'>30日間、一つの習慣に集中して人生を変えましょう</p>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    # ステップ1: 習慣の内容
    st.markdown("### 📝 ステップ1: 習慣の内容を決める")
    
    with st.expander("💡 習慣化のコツを見る", expanded=False):
        st.markdown("""
        **習慣を継続させる3つのポイント:**
        
        1. **目標のハードルを下げる** - 5分でできることから始めよう
        2. **具体的にする** - 「運動する」ではなく「腕立て10回」のように
        3. **楽しむ** - 自分が少しでも楽しめることを選ぼう
        
        **おすすめの習慣例:**
        - 🏃‍♂️ 5分間のストレッチ
        - 📚 参考書を3ページ読む
        - 🧹 机の上を整理する
        - 💧 水を1杯飲む
        - 📱 SNSを見る前に深呼吸3回
        """)
    
    habit = dm.load_user_habit(user_id)
    name = st.text_input(
        "習慣の内容", 
        value=habit.get("name", "") if habit else "", 
        placeholder="例: 朝5分ストレッチをする",
        help="できるだけシンプルで具体的に！"
    )
    
    # 入力内容のバリデーション
    if name:
        if '5分' in name or '５分' in name or len(name) < 30:
            st.success("✅ 良い習慣です！継続しやすそうですね")
        elif len(name) > 50:
            st.warning("⚠️ 少し長すぎるかも。もっとシンプルにしてみましょう")
    
    st.write("")
    st.write("")
    
    # ステップ2: 時間設定
    st.markdown("### ⏰ ステップ2: 実行する時間を決める")
    
    with st.expander("💡 タイミングのコツを見る", expanded=False):
        st.markdown("""
        **効果的なタイミングの選び方:**
        
        - **既存の習慣の前後** につなげると続きやすい
        - **ダラダラ時間を避ける** - 寝転がってスマホを見ている時は避けよう
        - **毎日同じ時間** にすると自動的になりやすい
        
        **タイミングの例:**
        - 🚿 お風呂に入る前後
        - 🍽️ 食事の前後
        - 🌙 寝る前
        - ☀️ 起きてすぐ
        """)
    
    t = TIME_INPUT_DEFAULT
    if habit and habit.get("target_time"):
        try:
            h, m = map(int, habit["target_time"].split(":"))
            t = datetime.time(h, m)
        except ValueError:
            t = TIME_INPUT_DEFAULT
    
    time_input = st.time_input(
        '目標時刻', 
        value=t,
        help="毎日この時間に実行することを目指しましょう"
    )
    
    # 確認と開始
    if name and time_input:
        st.markdown("---")
        st.markdown("### ✅ 設定内容の確認")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**習慣:** {name}")
        with col2:
            st.info(f"**時刻:** {time_input.strftime('%H:%M')}")
        
        st.warning("⚠️ **注意:** 一度開始すると、30日達成まで変更できません")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button('🚀 この習慣で30日チャレンジを開始！', use_container_width=True, type="primary"):
                try:
                    result = supabase.table("habits").upsert({
                        "user_id": user_id,
                        "name": name,
                        "target_time": time_input.strftime("%H:%M"),
                        "active": True
                    }, on_conflict="user_id").execute()
                    
                    if result and result.data:
                        st.success("✅ 習慣を設定しました！さあ、始めましょう！")
                        
                        # LINE通知を送信
                        send_line_notification_to_user(
                            supabase,
                            f"🎯 新しい習慣をスタート！\n「{name}」\n目標時刻: {time_input.strftime('%H:%M')}\n\n30日間頑張りましょう！",
                            user_id
                        )
                        
                        st.session_state.page = "challenge"
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("習慣の保存に失敗しました")
                        
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
 
def render_challenge(user_id):
    """習慣に挑戦し、進捗を記録するページ（改善版）"""
    
    # ページ遷移フラグをチェック
    if st.session_state.get('force_settings_page', False):
        st.session_state.page = "settings"
        st.session_state.pop('force_settings_page', None)
        st.rerun()
        return
    
    habit = dm.load_user_habit(user_id)
    
    if not habit or not habit.get("name"):
        st.warning("まず習慣を設定してください")
        if st.button("習慣を設定する", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
        return
    
    # ヘッダー
    st.markdown(f"<h1 style='text-align: center;'>🎯 {habit['name']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666;'>目標時刻: {habit['target_time']}</p>", unsafe_allow_html=True)
    
    st.write("")
    
    logs = tracker.get_logs(user_id)
    count, last_date = tracker.get_click_status(logs)
    
    # デバッグ情報（開発者用）
    with st.expander("🔧 デバッグ情報（開発者用）", expanded=False):
        st.write(f"**最終記録日:** {last_date}")
        st.write(f"**今日の日付:** {datetime.date.today().strftime(DATE_FORMAT)}")
        st.write(f"**現在のページ:** {st.session_state.get('page', 'なし')}")
        st.write(f"**習慣:** {habit}")
        
    # 2日以上記録がない場合のリセット判定
    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, DATE_FORMAT).date()
        days_since_last = (datetime.date.today() - last_date_obj).days

        if days_since_last > MISS_DAYS_THRESHOLD and count > 0:
            # まだリセット画面を表示していない場合のみフラグを立てる
            if not st.session_state.get('show_reset_screen', False):
                st.session_state['show_reset_screen'] = True
                # ログはまだ削除しない（ボタン押下時に削除）
        
            # リセット画面を表示
            st.markdown("### 習慣の連続日数が２日間更新されなかったため、日数を０に初期化しました。")   
            st.write("")
            st.markdown("<p style='color: #999; font-weight: bold;'>💡 習慣を続けるコツ: ハードルを下げて、毎日続けやすい内容にしましょう</p>", unsafe_allow_html=True)
            st.write("")
            st.write("")
        
            col1, col2 = st.columns(2)
        
            with col1:
                if st.button("この習慣で再チャレンジ", use_container_width=True, type="primary", key="rechallenge_btn"):
                    # ここでログをリセット
                    tracker.reset_logs(user_id)
                
                    # フラグをクリア
                    st.session_state.pop('show_reset_screen', None)
                
                    st.success(f"💪 「{habit['name']}」で再チャレンジ開始！頑張りましょう！")
                
                    # LINE通知を送信
                    try:
                        send_line_notification_to_user(
                            supabase,
                            f"🔄 再チャレンジ開始！\n「{habit['name']}」\n\nまた今日から頑張りましょう！",
                            user_id
                        )
                    except:
                        pass
                
                    time.sleep(1)
                    st.rerun()
        
            with col2:
                if st.button("新しい習慣を設定", use_container_width=True, key="change_habit_btn"):
                    # 現在のログを取得（削除前に取得！）
                    all_logs = dm.load_click_logs(user_id)
        
                    if all_logs:
                        # ログを古い順に並び替え
                        all_logs_sorted = sorted(all_logs, key=lambda x: x['log_date'])
            
                        # 履歴に保存
                        try:
                            history_record = {
                                "user_id": user_id,
                                "habit_name": habit["name"] + " (未完了)",
                                "target_time": habit["target_time"],
                                "archived_at": datetime.datetime.now().isoformat(),
                                "total_days": len(all_logs_sorted),
                                "log_summary": all_logs_sorted,
                            }
                            dm.save_history(history_record)
                            st.success("📝 履歴に保存しました")
                        except Exception as e:
                            st.warning(f"履歴の保存でエラーが発生しました: {e}")
        
                    # 習慣とログを削除
                    try:
                        tracker.reset_logs(user_id)  # ここでログを削除
                        dm.delete_user_habit(user_id)
                    
                        # セッションステートをクリア
                        st.session_state.pop('show_reset_screen', None)
                        st.session_state.pop('reset_screen_shown', None)
                        st.session_state.pop('challenge_phase', None)
                        st.session_state.pop('cheers_message', None)
                        st.session_state.pop('milestone_message', None)
                        st.session_state.pop('balloons_triggered', None)
                    
                        st.success("✅ 習慣を削除しました")
                        time.sleep(0.5)
                        # main()の強制送還ロジックに任せる
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"削除エラー: {e}")
        
            # リセット画面を表示したら、以降の処理をスキップ
            return  # ← このreturnの位置が重要！if文の最後

    # Session Stateの初期化
    if 'cheers_message' not in st.session_state:
        st.session_state.cheers_message = None

    if 'milestone_message' not in st.session_state:
        st.session_state.milestone_message = None

    if 'balloons_triggered' not in st.session_state:
        st.session_state.balloons_triggered = False

    # プログレスバー
    st.write("")
    render_progress_bar(count, MAX_CHALLENGE_DAYS)
    st.write("")

    # 統計情報
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🔥 連続記録", 
            f"{count}日",
            delta=None if count == 0 else "+1" if tracker.can_click_today(last_date) else "達成済"
        )

    with col2:
        display_date = last_date if last_date else "---"
        st.metric("📅 最終記録日", display_date)

    with col3:
        remaining = MAX_CHALLENGE_DAYS - count
        st.metric("🎯 残り日数", f"{remaining}日")

    st.write("")
    st.markdown("---")
    st.write("")

    # マイルストーンメッセージ
    if st.session_state.milestone_message:
        icon, title, message = st.session_state.milestone_message
        st.markdown(f"""
        <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; color: white; margin: 2rem 0;'>
            <div style='font-size: 4rem;'>{icon}</div>
            <h2 style='color: white; margin: 1rem 0;'>{title}</h2>
            <p style='font-size: 1.2rem; color: #f0f0f0;'>{message}</p>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.milestone_message = None

    # 30日達成
    if tracker.is_completed(count):
        if not st.session_state.balloons_triggered:
            st.balloons()
            st.session_state.balloons_triggered = True
            
            # 30日達成のLINE通知
            try:
                send_line_notification_to_user(
                    supabase,
                    f"🏆 30日完全達成おめでとう！🏆\n\n「{habit['name']}」を30日間継続しました！\n\nあなたは素晴らしい！次の習慣にもチャレンジしましょう！",
                    user_id
                )
            except:
                pass
        
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    border-radius: 20px; color: white;'>
            <div style='font-size: 5rem;'>🏆</div>
            <h1 style='color: white;'>30日完全達成！</h1>
            <p style='font-size: 1.3rem;'>おめでとうございます！あなたは素晴らしい！</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.write("")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🎉 次の習慣にチャレンジする", use_container_width=True, type="primary"):
                tracker.archive(user_id, habit["name"], habit["target_time"])
                tracker.reset_logs(user_id)
                dm.delete_user_habit(user_id)
                st.session_state.page = "settings"
                st.session_state.balloons_triggered = False
                st.rerun()

    # 記録ボタン
    elif tracker.can_click_today(last_date):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("今日の習慣を記録する", use_container_width=True, type="primary", help="クリックして今日の達成を記録！"):
                tracker.record_today(user_id)
                
                # 新しいカウント
                new_count = count + 1
                
                # マイルストーンチェック
                milestone = check_milestone(new_count)
                if milestone:
                    st.session_state.milestone_message = milestone
                    
                    # マイルストーン達成のLINE通知
                    icon, title, msg = milestone
                    try:
                        send_line_notification_to_user(
                            supabase,
                            f"{icon} {title}\n\n「{habit['name']}」\n{new_count}日連続達成！\n\n{msg}",
                            user_id
                        )
                    except:
                        pass
                    
                    st.balloons()
                else:
                    # 通常の応援メッセージ
                    messages = [
                        "🎉 今日も達成！素晴らしい！",
                        "💪 いい調子！継続は力なり",
                        "⭐ 小さな進歩も大きな一歩",
                        "🔥 一歩一歩着実に前進！",
                        "👏 今日もお疲れさま！",
                        "🌟 完璧です！明日も頑張ろう",
                    ]
                    st.session_state.cheers_message = random.choice(messages)
                
                st.rerun()
    else:
        st.success("✅ 今日は既に記録済みです。素晴らしい！")
        st.info("また明日も頑張りましょう 💪")
        
        # 取り消しボタン
        st.write("")
        with st.expander("❌ 間違えて記録した場合"):
            st.warning("本日の記録を取り消すことができます")
            if st.button("🔄 直前の記録を取り消す"):
                if count > 0:
                    tracker.delete_today_log(user_id)
                    st.success("記録を取り消しました。再度記録できます")
                    st.session_state.cheers_message = None
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("取り消す記録がありません")
                     
def render_history(user_id):
    """過去の習慣の達成履歴を表示するページ"""
    st.markdown("<h1 style='text-align: center;'>🏆 達成履歴</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>これまでに達成した習慣の記録</p>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    history = dm.load_history(user_id)
   
    if not history:
        st.info("📝 まだ完了した習慣の履歴はありません")
        st.write("30日間習慣を継続すると、ここに記録されます！")
        return
    
    # 達成数の表示
    st.metric("🎯 達成した習慣の数", f"{len(history)}個")
    st.write("")
       
    for i, r in enumerate(history, 1):
        archive_date = datetime.datetime.fromisoformat(r["archived_at"]).strftime("%Y年%m月%d日")
        log_summary = r.get("log_summary", [])
       
        with st.expander(f'🏅 {i}. {r["habit_name"]} - {archive_date} ({r["total_days"]}日達成)'):
            st.markdown(f'**⏰ 目標時間:** {r["target_time"]}')
            st.markdown(f'**📅 達成日:** {archive_date}')
            st.write("")
            render_progress_chart(log_summary, r["total_days"])
 
# ------------------------------
# Main
# ------------------------------

def main():
    if not auth.is_authenticated():
        render_login()
        return
 
    user = auth.get_user()
    user_id = user.id
    
    session = auth.get_session()
    if session and session.access_token:
        supabase.postgrest.auth(session.access_token)
 
    if "page" not in st.session_state:
        habit = dm.load_user_habit(user_id)
        if not habit or not habit.get("name"):
            st.session_state.page = "settings"
        else:
            st.session_state.page = "challenge"
    
    habit = dm.load_user_habit(user_id)
    has_active_habit = habit and habit.get("name")
 
    if has_active_habit:
        st.sidebar.title("メニュー")
        st.sidebar.markdown(" ")
        
        #ラジオボタン間隔調整
        st.sidebar.markdown(
            """
            <style>
            section[data-testid = "stSidebar"] div[role = "radiogroup"] > label {
                margin-bottom: 14px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        page_options = ["challenge", "history"]
        page_labels = {"challenge": "**習慣クリック画面**", "history": "**履歴画面**"}
        
        current_index = page_options.index(st.session_state.page) if st.session_state.page in page_options else 0
        
        page = st.sidebar.radio(
            "移動",
            options=page_options,
            format_func=lambda x: page_labels[x],
            index=current_index,
            label_visibility="collapsed"
        )
        
        if page != st.session_state.page:
            st.session_state.page = page
            st.rerun()
            
        st.sidebar.markdown("---")
        
        # LINE通知設定
        with st.sidebar:
            st.write("### LINE通知設定")
            render_line_settings(user_id, supabase)
        
        st.sidebar.markdown("---")
        
        # 現在の習慣情報
        st.sidebar.markdown("### 現在の習慣")
        st.sidebar.write(f"{habit['name']}")
        st.sidebar.write(f"開始時刻 {habit['target_time']}")
        
        st.sidebar.markdown("---")
        
        if st.sidebar.button(" ログアウト", use_container_width=True):
            auth.logout()
            st.rerun()
    else:
        st.sidebar.title("メニュー")
        st.sidebar.info("習慣を設定してください")
        st.sidebar.markdown("---")
        if st.sidebar.button(" ログアウト", use_container_width=True):
            auth.logout()
            st.rerun()
 
    if st.session_state.page == "settings":
        render_settings(user_id)
    elif st.session_state.page == "challenge":
        render_challenge(user_id)
    elif st.session_state.page == "history":
        render_history(user_id)
   
if __name__ == "__main__":
    main()