import streamlit as st
from supabase import Client


class AuthManager:

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # -------- session helpers --------

    def get_user(self):
        return st.session_state.get("supabase_user")

    def get_session(self):
        return st.session_state.get("supabase_session")

    def is_authenticated(self) -> bool:
        return self.get_user() is not None

    def _set_session(self, user, session):
        """セッション情報をStreamlitとSupabaseに反映"""
        st.session_state.supabase_user = user
        st.session_state.supabase_session = session

        if session and getattr(session, "access_token", None):
            self.supabase.postgrest.auth(session.access_token)

    def _clear_session(self):
        """セッション情報を完全クリア"""
        st.session_state.supabase_user = None
        st.session_state.supabase_session = None
        self.supabase.postgrest.auth(None)

    # -------- auth --------

    def login(self, email: str, password: str):
        """ログイン処理"""
        try:
            res = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if res.user and res.session:
                self._set_session(res.user, res.session)

            return res

        except Exception as e:
            print(f"Login error: {e}")
            self._clear_session()
            return None

    def signup(self, email: str, password: str):
        """新規登録処理"""
        try:
            res = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if res.user:
                self._set_session(res.user, res.session)

            return res

        except Exception as e:
            print(f"Signup error: {e}")
            self._clear_session()
            return None

    def logout(self):
        """ログアウト処理"""
        try:
            self.supabase.auth.sign_out()
        finally:
            self._clear_session()
