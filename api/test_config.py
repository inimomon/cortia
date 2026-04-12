from config import Config
import mysql.connector

print("Testing Config...")

print(Config.BASE_DIR)
print(Config.ARTIFACT_DIR)
print(Config.DAERAH_LIST)

try:
    conn = mysql.connector.connect(**Config.DB_CONFIG)
    print("Database OK")
    conn.close()
except Exception as e:
    print("Database Error:", e)
# py -m uvicorn server:app --reload
