import datetime
from constants import DATE_FORMAT, MAX_CHALLENGE_DAYS

class HabitTracker:
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    # ------------------ ログの取得と状態 ------------------
    def get_logs(self, user_id):
        """ユーザーの進捗ログを取得する (最新順)"""
        return self.data_manager.load_click_logs(user_id)
    
    def get_click_status(self, logs: list):
        """現在のクリック状況（連続日数、最新日）を取得する"""
        if not logs:
            return 0, None

        last_click_date = logs[0].get("log_date")

        # 空・None・空白対策
        if not last_click_date or str(last_click_date).strip() == "":
            return 0, None

        # ログを日付順にソート（新しい順）
        sorted_logs = sorted(logs, key=lambda x: x["log_date"], reverse=True)

        consecutive_count = 0
        expected_date = datetime.datetime.strptime(
            last_click_date, DATE_FORMAT
        ).date()

        for log in sorted_logs:
            log_date = datetime.datetime.strptime(
                log["log_date"], DATE_FORMAT
            ).date()

            if log_date == expected_date:
                consecutive_count += 1
                expected_date -= datetime.timedelta(days=1)
            else:
                break

        return consecutive_count, last_click_date

    
    def is_completed(self, count: int) -> bool:
        """チャレンジ完了（MAX_CHALLENGE_DAYSに達したか）を判定する"""
        return count >= MAX_CHALLENGE_DAYS
    
    # ------------------ クリック・記録 ------------------
    def can_click_today(self, last_click_date: str) -> bool:
        """今日、記録ボタンをクリックできるか（最後にクリックした日が今日ではないか）を判定する"""
        today_str = datetime.date.today().strftime(DATE_FORMAT)
        
        if last_click_date is None:
            return True
        
        return last_click_date != today_str
    
    def record_today(self, user_id: str):
        """今日の習慣の達成ログを保存する"""
        now = datetime.datetime.now()
        log_date = now.strftime(DATE_FORMAT)
        completion_hour = now.hour
        self.data_manager.save_click_log(user_id, log_date, completion_hour)
    
    def delete_today_log(self, user_id: str):
        """今日のログを削除する（取り消し機能）"""
        today_str = datetime.date.today().strftime(DATE_FORMAT)
        self.data_manager.delete_click_log(user_id, today_str)
    
    # ------------------ チャレンジ完了・リセット ------------------
    def archive(self, user_id: str, habit_name: str, target_time: str):
        """チャレンジを完了し、習慣履歴テーブルに保存する"""
        logs = self.get_logs(user_id)
        logs.reverse()
        
        history_record = {
            "user_id": user_id,
            "habit_name": habit_name,
            "target_time": target_time,
            "archived_at": datetime.datetime.now().isoformat(),
            "total_days": len(logs),
            "log_summary": logs,
        }
        self.data_manager.save_history(history_record)
    
    def reset_logs(self, user_id: str):
        """progress_logsテーブルの記録をリセットする"""
        self.data_manager.reset_click_logs(user_id)
    
    def needs_reset(self, logs: list, threshold: int) -> bool:
        """リセットが必要な状態（記録が途切れている）かを判定する"""
        if not logs:
            return False
        
        # get_click_statusと同じく最新のログを取得
        last_date_str = logs[0]["log_date"]
        last_date_obj = datetime.datetime.strptime(last_date_str, DATE_FORMAT).date()
        days_since_last = (datetime.date.today() - last_date_obj).days
        
        return days_since_last > threshold
    
    def hour_to_hhmm(hour_float):
        total_minutes = round(hour_float * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"