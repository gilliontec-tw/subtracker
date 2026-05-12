"""
field_encrypt.py
~~~~~~~~~~~~~~~~
提供欄位層級（Field-Level）的對稱加密工具，用於保護儲存在資料庫中的敏感欄位。

加密演算法: Fernet (AES-128-CBC + HMAC-SHA256)
金鑰來源:   由環境變數 SECRET_KEY 透過 SHA-256 衍生 32 bytes，再做 URL-safe base64 編碼。
            此衍生過程與 Session 簽名金鑰（itsdangerous 直接使用 SECRET_KEY）分離，
            避免同一金鑰材料用於多個目的。

使用規則:
- 加密後的密文以 str 型別儲存於 DB，欄位寬度需 ≥ 500 chars（Fernet 輸出含 base64 overhead）。
- encrypt(None) → None；decrypt(None) → None，方便處理可選欄位。
- 若 SECRET_KEY 尚未設定（空字串），模組初始化時會拋出 RuntimeError，
  讓啟動期間的錯誤能被 lifespan 攔截。

遷移注意:
- 若 DB 中已有明文 login_password 資料，需執行一次性遷移腳本將明文轉為密文。
  請參閱 scripts/migrate_encrypt_login_password.py。
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

# ── 金鑰衍生 ────────────────────────────────────────────────────────────────
def _derive_fernet_key() -> bytes:
    """從 SECRET_KEY 衍生 Fernet 用金鑰（32 bytes → URL-safe base64）。"""
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        raise RuntimeError(
            "SECRET_KEY 未設定，無法初始化欄位加密模組。"
            "請在 .env 中設定 SECRET_KEY 後再啟動應用程式。"
        )
    # SHA-256(SECRET_KEY) → 32 bytes，再做 URL-safe base64 → Fernet key
    raw = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(raw)


# 模組載入時建立單例 Fernet 物件；SECRET_KEY 不存在時立即 fail-fast
_fernet = Fernet(_derive_fernet_key())


# ── 公開 API ─────────────────────────────────────────────────────────────────
def encrypt(plaintext: str | None) -> str | None:
    """
    將明文字串加密為 Fernet token（str）。
    - None 輸入 → None 輸出（可選欄位）。
    - 空字串視為「有值」，仍加密儲存。
    """
    if plaintext is None:
        return None
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str | None) -> str | None:
    """
    將 Fernet token 解密為明文字串。
    - None 輸入 → None 輸出。
    - 若 token 無效（被竄改或金鑰不符），回傳 None 並靜默失敗，
      避免洩漏錯誤細節；上層應視需求記錄警告。
    """
    if ciphertext is None:
        return None
    try:
        return _fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # 金鑰輪換期間舊密文或資料損壞時安全降級
        return None
