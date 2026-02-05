from supabase import Client
import streamlit as st
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.SESSION_DURATION_DAYS = 7  # セッション有効期限（7日間）
    
    def _save_session_to_storage(self, session):
        """セッション情報をローカルストレージ風に保存"""
        if session and session.access_token:
            # セッション情報をst.session_stateに保存
            st.session_state['auth_session'] = {
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
                'expires_at': session.expires_at,
                'user': {
                    'id': session.user.id,
                    'email': session.user.email
                },
                'saved_at': datetime.now().isoformat()
            }
    
    def _load_session_from_storage(self):
        """保存されたセッション情報を読み込む"""
        return st.session_state.get('auth_session')
    
    def _clear_session_storage(self):
        """保存されたセッション情報をクリア"""
        if 'auth_session' in st.session_state:
            del st.session_state['auth_session']
    
    def _is_session_expired(self, saved_session):
        """セッションの有効期限をチェック"""
        if not saved_session:
            return True
        
        try:
            saved_at = datetime.fromisoformat(saved_session['saved_at'])
            expires_at = saved_at + timedelta(days=self.SESSION_DURATION_DAYS)
            return datetime.now() > expires_at
        except:
            return True
    
    def _restore_session(self, saved_session):
        """保存されたセッション情報からセッションを復元"""
        try:
            # Supabaseのセッションを復元
            self.supabase.auth.set_session(
                saved_session['access_token'],
                saved_session['refresh_token']
            )
            return True
        except Exception as e:
            print(f"セッション復元エラー: {e}")
            return False
    
    def login(self, email: str, password: str):
        """ログイン処理"""
        response = self.supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response and response.session:
            # セッション情報を保存
            self._save_session_to_storage(response.session)
            return response
        
        raise Exception("ログインに失敗しました")
    
    def signup(self, email: str, password: str):
        """新規登録処理"""
        response = self.supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        return response
    
    def logout(self):
        """ログアウト処理"""
        try:
            self.supabase.auth.sign_out()
        except:
            pass
        finally:
            # 保存されたセッション情報をクリア
            self._clear_session_storage()
    
    def is_authenticated(self) -> bool:
        """認証状態をチェック"""
        # まず現在のセッションをチェック
        current_session = self.supabase.auth.get_session()
        if current_session:
            return True
        
        # 保存されたセッション情報をチェック
        saved_session = self._load_session_from_storage()
        if saved_session and not self._is_session_expired(saved_session):
            # セッションを復元
            if self._restore_session(saved_session):
                return True
        
        # セッションが期限切れまたは無効な場合はクリア
        self._clear_session_storage()
        return False
    
    def get_user(self):
        """現在のユーザー情報を取得"""
        # まず現在のセッションから取得
        user = self.supabase.auth.get_user()
        if user:
            return user
        
        # 保存されたセッション情報から取得
        saved_session = self._load_session_from_storage()
        if saved_session and not self._is_session_expired(saved_session):
            # セッションを復元してから再取得
            if self._restore_session(saved_session):
                return self.supabase.auth.get_user()
        
        return None
    
    def get_session(self):
        """現在のセッション情報を取得"""
        return self.supabase.auth.get_session()