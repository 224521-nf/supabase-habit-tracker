from supabase import Client
import streamlit as st

class DataManagerSupabase:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def _validate_user_id(self, user_id: str) -> bool:
        """user_idのフォーマットを検証"""
        if not user_id or not isinstance(user_id, str):
            return False
        # SupabaseのUUIDフォーマットを検証
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, user_id, re.IGNORECASE))
    
    def _validate_habit_name(self, name: str) -> bool:
        """習慣名のバリデーション"""
        if not name or not isinstance(name, str):
            return False
        if len(name) > 100:
            return False
        # 危険な文字列のチェック
        dangerous_patterns = ['<script', 'javascript:', 'onerror=', 'onclick=']
        name_lower = name.lower()
        return not any(pattern in name_lower for pattern in dangerous_patterns)
    
    def _validate_time_format(self, time_str: str) -> bool:
        """時刻フォーマットのバリデーション"""
        if not time_str or not isinstance(time_str, str):
            return False
        import re
        # HH:MM形式のみ許可
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(time_pattern, time_str))
    
    # -------- habits --------
    def load_user_habit(self, user_id: str) -> dict:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
    
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
        # バリデーション
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        if not self._validate_habit_name(name):
            raise ValueError("Invalid habit name")
        if not self._validate_time_format(target_time):
            raise ValueError("Invalid time format")
        
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
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
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
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
        # hour のバリデーション
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ValueError("Invalid hour value")
        
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
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .delete()
                .eq("user_id", user_id)
                .eq("log_date", log_date)
                .execute()
            )
            return res is not None and (
                hasattr(res, 'status_code') and res.status_code == 204
                or hasattr(res, 'data')
            )
        except Exception as e:
            print(f"Error deleting click log: {e}")
            return False
    
    def reset_click_logs(self, user_id: str) -> bool:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
        try:
            res = (
                self.supabase
                .table("progress_logs")
                .delete()
                .eq("user_id", user_id)
                .execute()
            )
            return res is not None and (
                hasattr(res, 'status_code') and res.status_code == 204
                or hasattr(res, 'data')
            )
        except Exception as e:
            print(f"Error resetting click logs: {e}")
            return False
    
    # -------- history --------
    def load_history(self, user_id: str) -> list:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
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
        # user_idのバリデーション
        if 'user_id' in record and not self._validate_user_id(record['user_id']):
            raise ValueError("Invalid user_id format")
        
        # habit_nameのバリデーション
        if 'habit_name' in record and not self._validate_habit_name(record['habit_name']):
            raise ValueError("Invalid habit name")
        
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
    
    # -------- habits --------
    def delete_user_habit(self, user_id: str) -> bool:
        """現在の習慣を削除"""
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        
        try:
            res = (
                self.supabase
                .table("habits")
                .delete()
                .eq("user_id", user_id)
                .execute()
            )
            return res is not None
        except Exception as e:
            print(f"Error deleting habit: {e}")
            return False