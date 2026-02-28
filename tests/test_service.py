import os
import tempfile
from src.approval_system import init_db, create_user, send_letter, list_pending_for_role, act_on_letter, get_letter


def test_full_flow():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        init_db(path)
        # create users matching DEFAULT_ROUTE order
        roles = [
            "SRC",
            "Faculty",
            "HOD",
            "Dean",
            "Students Affairs Officer",
            "Dean of Student Affairs",
            "Vice Chancellor",
        ]
        users = {}
        for i, r in enumerate(roles):
            uid = create_user(path, f"u{i}", r)
            users[r] = uid

        sender = create_user(path, "sender", "Faculty Association")
        lid = send_letter(path, sender, "Test", "Please approve")

        # iterate approvals
        for r in roles:
            pending = list_pending_for_role(path, r)
            assert any(p["letter_id"] == lid for p in pending)
            # act: approve
            out = act_on_letter(path, lid, users[r], "approve", comments=f"ok by {r}")
            assert out["letter"]["status"] in ("pending", "approved")

        # final letter should be approved
        final = get_letter(path, lid)
        assert final["letter"]["status"] == "approved"
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
