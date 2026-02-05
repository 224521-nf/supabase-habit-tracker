import streamlit as st
from supabase import Client

class AuthManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        
        # セッション状態の初期化
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'session' not in st.session_state:
            st.session_state.session = None
    
    def signup(self, email: str, password: str):
        """新規ユーザー登録"""
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                return response.user
            else:
                raise Exception("登録に失敗しました")
        except Exception as e:
            raise Exception(f"登録エラー: {str(e)}")
    
    def login(self, email: str, password: str):
        """ログイン"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                st.session_state.user = response.user
                st.session_state.session = response.session
                return response.user
            else:
                raise Exception("ログインに失敗しました")
        except Exception as e:
            raise Exception(f"ログインエラー: {str(e)}")
    
    def logout(self):
        """ログアウト"""
        try:
            self.supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.session = None
        except Exception as e:
            print(f"ログアウトエラー: {e}")
            # エラーが発生してもセッションはクリア
            st.session_state.user = None
            st.session_state.session = None
    
    def is_authenticated(self) -> bool:
        """認証状態を確認"""
        # セッション状態をチェック
        if st.session_state.user and st.session_state.session:
            return True
        
        # Supabaseのセッションをチェック
        try:
            session = self.supabase.auth.get_session()
            if session:
                st.session_state.user = session.user
                st.session_state.session = session
                return True
        except:
            pass
        
        return False
    
    def get_user(self):
        """現在のユーザーを取得"""
        return st.session_state.user
    
    def get_session(self):
        """現在のセッションを取得"""
        return st.session_state.session