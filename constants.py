import datetime

# ------------------ date / time ------------------
DATE_FORMAT = "%Y-%m-%d"

# completion_hour は「0〜24 の float（時間単位）」で扱う
# 例: 8.5 = 08:30
HOUR_FLOAT_BASE = 24

TIME_INPUT_DEFAULT = datetime.time(8, 0)

# ------------------ challenge settings ------------------
MAX_CHALLENGE_DAYS = 30

# 最後の記録からこの日数を超えたらリセット
MISS_DAYS_THRESHOLD = 2
