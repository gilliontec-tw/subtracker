"""
migrate_encrypt_login_password.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
一次性遷移腳本：將 saas_subscriptions.login_password 欄位
從明文轉換為 Fernet 加密密文。

執行條件:
  - 必須先設定 SECRET_KEY 環境變數（與應用程式相同的金鑰）
  - 確認 .env 已載入（透過 python-dotenv）

使用方式:
  python scripts/migrate_encrypt_login_password.py

安全注意事項:
  - 此腳本具備冪等性：已加密的密文會被跳過（無法被 encrypt() 再次加密）
  - 執行前建議先備份資料庫
  - 完成後請確認應用程式正常運作，再刪除此腳本
"""
import sys
import os

# 確保能 import 專案模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.models import SubscriptionModel
from src.infrastructure.auth.field_encrypt import encrypt as _enc, decrypt as _dec


def _is_already_encrypted(value: str) -> bool:
    """
    Fernet token 以 'gAAA' 開頭（base64 encoded version byte 0x80）。
    嘗試解密；若成功表示已加密，直接跳過。
    """
    return _dec(value) is not None


def migrate() -> None:
    session = SessionLocal()
    try:
        rows = session.query(SubscriptionModel).all()
        updated = 0
        skipped_encrypted = 0
        skipped_empty = 0

        for row in rows:
            if not row.login_password:
                skipped_empty += 1
                continue

            # 若已是有效密文，跳過（冪等性保護）
            if _is_already_encrypted(row.login_password):
                skipped_encrypted += 1
                continue

            # 明文 → Fernet 密文
            row.login_password = _enc(row.login_password)
            updated += 1

        session.commit()
        print(f"[完成] 已加密: {updated} 筆  "
              f"| 已跳過（已加密）: {skipped_encrypted} 筆  "
              f"| 已跳過（空值）: {skipped_empty} 筆")
    except Exception as exc:
        session.rollback()
        print(f"[錯誤] 遷移失敗，已回滾。原因: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    print("開始遷移 login_password 欄位（明文 → Fernet 加密）...")
    migrate()
