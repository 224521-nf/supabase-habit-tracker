from supabase import Client


class AuthManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ------------------ auth ------------------
    def login(self, email: str, password: str):
        return self.supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

    def signup(self, email: str, password: str):
        return self.supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )

    def logout(self):
        self.supabase.auth.sign_out()

    # ------------------ session / user ------------------
    def get_user(self):
        """
        戻り値: User | None
        """
        try:
            response = self.supabase.auth.get_user()
            # response は直接 User オブジェクトを返す
            return response
        except Exception:
            return None

    def get_session(self):
        """
        戻り値: Session | None
        """
        try:
            response = self.supabase.auth.get_session()
            # response は直接 Session オブジェクトを返す
            return response
        except Exception:
            return None

    def is_authenticated(self) -> bool:
        """
        access_token が存在する場合のみ True
        """
        try:
            session = self.get_session()
            if session and hasattr(session, "access_token"):
                return bool(session.access_token)
            return False
        except Exception:
            return False