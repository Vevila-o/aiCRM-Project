"""
Utility helpers for authenticating employees stored in the legacy `User` table.
"""
from __future__ import annotations

from typing import Optional, Tuple

from myCRM.models import User
import hashlib
from django.db.models import Max


def authenticate_user(username: str, password: str) -> Optional[User]:
  
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return None

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return None

    # Stored passwords historically may be plaintext. We'll support both
    # legacy plaintext and new SHA1-hashed passwords. If plaintext matches,
    # migrate the stored password to the hashed form.
    def _sha1(p: str) -> str:
        return hashlib.sha1(p.encode("utf-8")).hexdigest()

    stored = (user.password or "")
    candidate_hashed = _sha1(password)

    if stored == candidate_hashed:
        return user

    # if stored equals plaintext (legacy), migrate to hashed
    if stored == password:
        user.password = candidate_hashed
        try:
            user.save()
        except Exception:
            # ignore save issues: authentication still succeeds
            pass
        return user

    return None


def create_user(username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """Create a new User with SHA1-hashed password.

    Returns a tuple (user, error_message). On success error_message is None.
    """
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return None, '使用者名稱或密碼不得為空'

    if User.objects.filter(username=username).exists():
        return None, '帳號已存在'

    hashed = hashlib.sha1(password.encode("utf-8")).hexdigest()

    # Attempt to determine next userid if table does not auto-increment
    max_row = User.objects.aggregate(Max('userid'))
    next_id = (max_row.get('userid__max') or 0) + 1

    user = User(userid=next_id, username=username, password=hashed)
    try:
        user.save()
        return user, None
    except Exception as e:
        # 寫入暫存日誌，方便開發時檢查
        try:
            import os
            log_path = os.path.join(os.getcwd(), 'registration_error.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"create_user error for '{username}': {e}\n")
        except Exception:
            pass
        return None, str(e)

