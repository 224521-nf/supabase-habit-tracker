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
        戻り値:
          UserResponse | None
        user_response.user.id で参照する
        """
        try:
            return self.supabase.auth.get_user()
        except Exception:
            return None

    def get_session(self):
        """
        戻り値:
          SessionResponse | None
        session.session.access_token を使う
        """
        try:
            return self.supabase.auth.get_session()
        except Exception:
            return None

    def is_authenticated(self) -> bool:
        """
        access_token が存在する場合のみ True
        """
        session_response = self.get_session()

        if not session_response:
            return False

        session = getattr(session_response, "session", None)
        if not session:
            return False

        return bool(getattr(session, "access_token", None))
