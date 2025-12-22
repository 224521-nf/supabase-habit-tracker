import streamlit as st
from supabase import Client


class AuthManager:

    def __init__(self, supabase: Client):
        self.supabase = supabase

    def get_user(self):
        return st.session_state.get("supabase_user")
    
    def get_session(self):
        """現在のセッション情報を取得"""
        return st.session_state.get("supabase_session")

    def is_authenticated(self) -> bool:
        return self.get_user() is not None

    def login(self, email: str, password: str):
        """ログイン処理"""
        res = self.supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # ユーザー情報とセッション情報を保存
        st.session_state.supabase_user = res.user
        st.session_state.supabase_session = res.session
        
        # セッショントークンをSupabaseクライアントに設定
        if res.session and res.session.access_token:
            self.supabase.postgrest.auth(res.session.access_token)
        
        return res

    def signup(self, email: str, password: str):
        """新規登録処理"""
        res = self.supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if res.user:
            st.session_state.supabase_user = res.user
            st.session_state.supabase_session = res.session
            
            # セッショントークンをSupabaseクライアントに設定
            if res.session and res.session.access_token:
                self.supabase.postgrest.auth(res.session.access_token)
        
        return res

    def logout(self):
        """ログアウト処理"""
        self.supabase.auth.sign_out()
        st.session_state.supabase_user = None
        st.session_state.supabase_session = None