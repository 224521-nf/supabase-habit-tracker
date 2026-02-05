import datetime

# 日付フォーマット
DATE_FORMAT = "%Y-%m-%d"

# チャレンジの最大日数
MAX_CHALLENGE_DAYS = 30

# リセット判定の閾値（日数）
# 最終記録日から何日経過したらリセットするか
MISS_DAYS_THRESHOLD = 2

# 時刻入力のデフォルト値
TIME_INPUT_DEFAULT = datetime.time(9, 0)