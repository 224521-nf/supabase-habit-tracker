from supabase import Client


class AuthManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ------------------ auth ------------------
    def login(self, email: str, password: str):
        response = self.supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )
        return response

    def signup(self, email: str, password: str):
        response = self.supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )
        return response

    def logout(self):
        self.supabase.auth.sign_out()

    # ------------------ session / user ------------------
    def get_user(self):
        """現在のユーザーを取得"""
        try:
            # supabase-py v2 では get_user() が直接 User を返す
            user = self.supabase.auth.get_user()
            return user
        except Exception as e:
            print(f"get_user error: {e}")
            return None

    def get_session(self):
        """現在のセッションを取得"""
        try:
            # セッション情報を取得
            session = self.supabase.auth.get_session()
            return session
        except Exception as e:
            print(f"get_session error: {e}")
            return None

    def is_authenticated(self) -> bool:
        """認証状態を確認"""
        try:
            session = self.supabase.auth.get_session()
            return session is not None
        except Exception:
            return False