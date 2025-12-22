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
        total_click_count = len(logs)
        last_click_date = logs[0]["log_date"] if logs else None
        return total_click_count, last_click_date
 
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