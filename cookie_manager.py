import streamlit as st
import json
import base64
from datetime import datetime, timedelta

class CookieManager:
    """シンプルなクッキー管理クラス"""
    
    def __init__(self, cookie_name: str = "habit_app_auth"):
        self.cookie_name = cookie_name
    
    def set_cookie(self, value: dict, days: int = 7):
        """クッキーに値を設定"""
        # 値をJSON文字列に変換してBase64エンコード
        json_str = json.dumps(value)
        encoded = base64.b64encode(json_str.encode()).decode()
        
        # 有効期限を計算
        expires = datetime.now() + timedelta(days=days)
        expires_str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # クッキーを設定するJavaScriptコード
        cookie_js = f"""
        <script>
            document.cookie = "{self.cookie_name}={encoded}; expires={expires_str}; path=/; SameSite=Lax";
            console.log("Cookie set successfully");
        </script>
        """
        
        st.components.v1.html(cookie_js, height=0, width=0)
    
    def get_cookie(self):
        """クッキーから値を取得"""
        # セッションステートにキャッシュがあればそれを使用
        cache_key = f"_cookie_cache_{self.cookie_name}"
        if cache_key in st.session_state:
            return st.session_state[cache_key]
        
        # クッキーを読み取るJavaScriptコード
        cookie_js = f"""
        <script>
            function getCookie(name) {{
                const value = `; ${{document.cookie}}`;
                const parts = value.split(`; ${{name}}=`);
                if (parts.length === 2) {{
                    return parts.pop().split(';').shift();
                }}
                return null;
            }}
            
            const cookieValue = getCookie("{self.cookie_name}");
            if (cookieValue) {{
                // Streamlitに値を送信
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    value: cookieValue
                }}, "*");
            }}
        </script>
        """
        
        # JavaScriptを実行して結果を取得
        result = st.components.v1.html(cookie_js, height=0, width=0)
        
        if result:
            try:
                # Base64デコードしてJSONをパース
                decoded = base64.b64decode(result).decode()
                data = json.loads(decoded)
                # キャッシュに保存
                st.session_state[cache_key] = data
                return data
            except Exception as e:
                print(f"クッキー読み取りエラー: {e}")
                return None
        
        return None
    
    def delete_cookie(self):
        """クッキーを削除"""
        # キャッシュもクリア
        cache_key = f"_cookie_cache_{self.cookie_name}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        
        # クッキーを削除するJavaScriptコード
        cookie_js = f"""
        <script>
            document.cookie = "{self.cookie_name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
            console.log("Cookie deleted");
        </script>
        """
        
        st.components.v1.html(cookie_js, height=0, width=0)