from supabase import Client


class DataManagerSupabase:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    # -------- habits --------

    def load_user_habit(self, user_id: str) -> dict:
        try:
            res = (
                self.supabase
                .table("habits")
                .select("*")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if res and hasattr(res, 'data') and res.data:
                # target_timeがtime型の場合、文字列に変換
                if res.data.get('target_time') and not isinstance(res.data['target_time'], str):
                    res.data['target_time'] = str(res.data['target_time'])
                return res.data
            return {}
        except Exception as e:
            print(f"Error loading user habit: {e}")
            return {}

    def save_user_habit(self, user_id: str, name: str, target_time: str) -> bool:
        try:
            data = {
                "user_id": user_id,
                "name": name,
                "target_time": target_time,
                "active": True,
            }
            
            res = (
                self.supabase
                .table("habits")
                .upsert(data, on_conflict="user_id")
                .execute()
            )
            
            return res is not None and hasattr(res, 'data') and bool(res.data)
                
        except Exception as e:
            print(f"Error saving user habit: {e}")
            return False

    # -------- progress_logs --------

    def load_click_logs(self, user_id: str) -> list:
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .select("log_date, completion_hour")
                .eq("user_id", user_id)
                .order("log_date", desc=True)
                .execute()
            )
            if res and hasattr(res, 'data') and res.data:
                return res.data
            return []
        except Exception as e:
            print(f"Error loading click logs: {e}")
            return []

    def save_click_log(self, user_id: str, log_date: str, hour: int) -> bool:
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .upsert(
                    {
                        "user_id": user_id,
                        "log_date": log_date,
                        "completion_hour": hour,
                    },
                    on_conflict="user_id,log_date"
                )
                .execute()
            )
            return res is not None and hasattr(res, 'data') and bool(res.data)
        except Exception as e:
            print(f"Error saving click log: {e}")
            return False

    def delete_click_log(self, user_id: str, log_date: str) -> bool:
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .delete()
                .eq("user_id", user_id)
                .eq("log_date", log_date)
                .execute()
            )
            # deleteの場合はstatus_codeをチェック
            return res is not None and (
                hasattr(res, 'status_code') and res.status_code == 204 or
                hasattr(res, 'data')
            )
        except Exception as e:
            print(f"Error deleting click log: {e}")
            return False

    def reset_click_logs(self, user_id: str) -> bool:
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .delete()
                .eq("user_id", user_id)
                .execute()
            )
            # deleteの場合はstatus_codeをチェック
            return res is not None and (
                hasattr(res, 'status_code') and res.status_code == 204 or
                hasattr(res, 'data')
            )
        except Exception as e:
            print(f"Error resetting click logs: {e}")
            return False

    # -------- history --------

    def load_history(self, user_id: str) -> list:
        try:
            res = (
                self.supabase
                .table("habit_history")
                .select("*")
                .eq("user_id", user_id)
                .order("archived_at", desc=True)
                .execute()
            )
            if res and hasattr(res, 'data') and res.data:
                return res.data
            return []
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def save_history(self, record: dict) -> bool:
        try:
            res = (
                self.supabase
                .table("habit_history")
                .insert(record)
                .execute()
            )
            return res is not None and hasattr(res, 'data') and bool(res.data)
        except Exception as e:
            print(f"Error saving history: {e}")
            return False