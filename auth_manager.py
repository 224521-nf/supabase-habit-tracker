from supabase import Client
import streamlit as st
from datetime import datetime, timedelta
from cookie_manager import CookieManager

class AuthManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.SESSION_DURATION_DAYS = 7  # セッション有効期限（7日間）
        self.cookie_manager = CookieManager("habit_app_auth")
    
    def _is_session_expired(self, session_data: dict) -> bool:
        """セッションの有効期限をチェック"""
        if not session_data or 'saved_at' not in session_data:
            return True
        
        try:
            saved_at = datetime.fromisoformat(session_data['saved_at'])
            expires_at = saved_at + timedelta(days=self.SESSION_DURATION_DAYS)
            return datetime.now() > expires_at
        except:
            return True
    
    def _restore_session(self, session_data: dict) -> bool:
        """保存されたセッション情報からSupabaseセッションを復元"""
        try:
            # Supabaseのセッションを設定
            self.supabase.auth.set_session(
                session_data['access_token'],
                session_data['refresh_token']
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
            # セッション情報をクッキーに保存
            session_data = {
                'access_token': response.session.access_token,
                'refresh_token': response.session.refresh_token,
                'user_id': response.user.id,
                'email': response.user.email,
                'saved_at': datetime.now().isoformat()
            }
            
            # クッキーに保存（7日間有効）
            self.cookie_manager.set_cookie(session_data, days=self.SESSION_DURATION_DAYS)
            
            # session_stateにも保存（即座にアクセスできるように）
            st.session_state['auth_data'] = session_data
            st.session_state['authenticated'] = True
            
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
            # クッキーを削除
            self.cookie_manager.delete_cookie()
            
            # session_stateをクリア
            if 'auth_data' in st.session_state:
                del st.session_state['auth_data']
            if 'authenticated' in st.session_state:
                del st.session_state['authenticated']
    
    def is_authenticated(self) -> bool:
        """認証状態をチェック"""
        # まずsession_stateをチェック（高速）
        if st.session_state.get('authenticated', False):
            auth_data = st.session_state.get('auth_data')
            if auth_data and not self._is_session_expired(auth_data):
                return True
        
        # クッキーをチェック
        cookie_data = self.cookie_manager.get_cookie()
        if cookie_data and not self._is_session_expired(cookie_data):
            # セッションを復元
            if self._restore_session(cookie_data):
                # session_stateに保存
                st.session_state['auth_data'] = cookie_data
                st.session_state['authenticated'] = True
                return True
        
        # 認証なしまたは期限切れ
        st.session_state['authenticated'] = False
        return False
    
    def get_user(self):
        """現在のユーザー情報を取得"""
        # session_stateから取得
        auth_data = st.session_state.get('auth_data')
        if auth_data:
            # 簡易的なユーザーオブジェクトを作成
            class User:
                def __init__(self, user_id, email):
                    self.id = user_id
                    self.email = email
            
            return User(auth_data['user_id'], auth_data['email'])
        
        # Supabaseから取得を試みる
        try:
            user = self.supabase.auth.get_user()
            return user
        except:
            return None
    
    def get_session(self):
        """現在のセッション情報を取得"""
        try:
            return self.supabase.auth.get_session()
        except:
            return None
    
    def refresh_session(self):
        """セッションをリフレッシュ（トークンを更新）"""
        try:
            auth_data = st.session_state.get('auth_data')
            if auth_data and 'refresh_token' in auth_data:
                # リフレッシュトークンを使用してセッションを更新
                response = self.supabase.auth.refresh_session(auth_data['refresh_token'])
                
                if response and response.session:
                    # 新しいセッション情報を保存
                    session_data = {
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token,
                        'user_id': response.user.id,
                        'email': response.user.email,
                        'saved_at': datetime.now().isoformat()
                    }
                    
                    self.cookie_manager.set_cookie(session_data, days=self.SESSION_DURATION_DAYS)
                    st.session_state['auth_data'] = session_data
                    return True
        except Exception as e:
            print(f"セッションリフレッシュエラー: {e}")
        
        return False