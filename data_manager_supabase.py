from supabase import Client


class DataManagerSupabase:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ------------------ validation ------------------
    def _validate_user_id(self, user_id: str) -> bool:
        if not user_id or not isinstance(user_id, str):
            return False

        import re
        uuid_pattern = (
            r'^[0-9a-f]{8}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{12}$'
        )
        return bool(re.match(uuid_pattern, user_id, re.IGNORECASE))

    def _validate_habit_name(self, name: str, allow_suffix: bool = False) -> bool:
        if not name or not isinstance(name, str):
            return False

        check_name = name
        if allow_suffix and name.endswith(" (未完了)"):
            check_name = name[:-6]

        if len(check_name) > 30:
            return False

        dangerous_patterns = [
            "<script", "javascript:", "onerror=", "onclick="
        ]
        name_lower = check_name.lower()
        return not any(p in name_lower for p in dangerous_patterns)

    def _validate_time_format(self, time_str: str) -> bool:
        if not time_str or not isinstance(time_str, str):
            return False

        import re
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(time_pattern, time_str))

    def _validate_date_format(self, date_str: str) -> bool:
        if not date_str or not isinstance(date_str, str):
            return False

        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

    # ------------------ habits ------------------
    def load_user_habit(self, user_id: str) -> dict:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        res = (
            self.supabase
            .table("habits")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if res and hasattr(res, "data") and res.data:
            if res.data.get("target_time") and not isinstance(res.data["target_time"], str):
                res.data["target_time"] = str(res.data["target_time"])[:5]
            return res.data

        return {}

    def save_user_habit(self, user_id: str, name: str, target_time: str) -> bool:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        if not self._validate_habit_name(name):
            raise ValueError("Invalid habit name")
        if not self._validate_time_format(target_time):
            raise ValueError("Invalid time format")

        res = (
            self.supabase
            .table("habits")
            .upsert(
                {
                    "user_id": user_id,
                    "name": name,
                    "target_time": target_time[:5],
                    "active": True,
                },
                on_conflict="user_id",
            )
            .execute()
        )
        return bool(res and getattr(res, "data", None))

    # ------------------ progress_logs ------------------
    def load_click_logs(self, user_id: str) -> list:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        res = (
            self.supabase
            .table("progress_logs")
            .select("log_date, completion_hour")
            .eq("user_id", user_id)
            .order("log_date", desc=True)
            .execute()
        )

        return res.data if res and hasattr(res, "data") else []

    def save_click_log(self, user_id: str, log_date: str, hour: float) -> bool:
        """★ float対応（例: 12.75）"""
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        if not isinstance(hour, (int, float)) or hour < 0 or hour >= 24:
            raise ValueError("Invalid completion_hour value")

        if not self._validate_date_format(log_date):
            raise ValueError("Invalid date format")

        res = (
            self.supabase
            .table("progress_logs")
            .upsert(
                {
                    "user_id": user_id,
                    "log_date": log_date,
                    "completion_hour": float(hour),
                },
                on_conflict="user_id,log_date",
            )
            .execute()
        )
        return bool(res and getattr(res, "data", None))

    def delete_click_log(self, user_id: str, log_date: str) -> bool:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")
        if not self._validate_date_format(log_date):
            raise ValueError("Invalid date format")

        res = (
            self.supabase
            .table("progress_logs")
            .delete()
            .eq("user_id", user_id)
            .eq("log_date", log_date)
            .execute()
        )
        return res is not None

    def reset_click_logs(self, user_id: str) -> bool:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        res = (
            self.supabase
            .table("progress_logs")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        return res is not None

    # ------------------ history ------------------
    def load_history(self, user_id: str) -> list:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        res = (
            self.supabase
            .table("habit_history")
            .select("*")
            .eq("user_id", user_id)
            .order("archived_at", desc=True)
            .execute()
        )
        return res.data if res and hasattr(res, "data") else []

    def save_history(self, record: dict) -> bool:
        if "user_id" in record and not self._validate_user_id(record["user_id"]):
            raise ValueError("Invalid user_id format")

        if "habit_name" in record and not self._validate_habit_name(
            record["habit_name"], allow_suffix=True
        ):
            raise ValueError("Invalid habit name")

        res = (
            self.supabase
            .table("habit_history")
            .insert(record)
            .execute()
        )
        return bool(res and getattr(res, "data", None))

    def delete_user_habit(self, user_id: str) -> bool:
        if not self._validate_user_id(user_id):
            raise ValueError("Invalid user_id format")

        res = (
            self.supabase
            .table("habits")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        return res is not None
