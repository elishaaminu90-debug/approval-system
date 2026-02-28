"""Approval system core package."""

from .service import (
    init_db,
    create_user,
    send_letter,
    list_pending_for_role,
    list_all_letters,
    act_on_letter,
    get_letter,
    get_letter_history,
    resend_letter,
)

__all__ = [
    "init_db",
    "create_user",
    "send_letter",
    "list_pending_for_role",
    "list_all_letters",
    "act_on_letter",
    "get_letter",
    "get_letter_history",
    "resend_letter",
]