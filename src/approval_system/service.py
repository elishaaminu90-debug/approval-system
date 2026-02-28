"""Core service functions for creating and routing letters."""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from .db import get_conn, init_db as db_init

DEFAULT_ROUTE = [
    "SRC",
    "Faculty",
    "HOD",
    "Dean",
    "Students Affairs Officer",
    "Dean of Student Affairs",
    "Vice Chancellor",
]

VALID_ROLES = set(DEFAULT_ROUTE + ["Faculty Association", "Student", "SRC", "Staff"])


def init_db(path: str) -> None:
    """Initialize database with tables."""
    db_init(path)


def create_user(db_path: str, name: str, role: str) -> int:
    """Create a new user with given role."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Valid roles: {', '.join(VALID_ROLES)}")
    
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Check if user already exists with same name and role
    cur.execute("SELECT id FROM users WHERE name = ? AND role = ?", (name, role))
    existing = cur.fetchone()
    if existing:
        conn.close()
        raise ValueError(f"User '{name}' with role '{role}' already exists")
    
    cur.execute("INSERT INTO users(name, role) VALUES(?, ?)", (name, role))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def send_letter(
    db_path: str, 
    sender_id: int, 
    title: str, 
    body: str, 
    route: Optional[List[str]] = None
) -> int:
    """Send a new letter for approval."""
    # Validate sender exists and has correct role
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id = ?", (sender_id,))
    sender = cur.fetchone()
    if not sender:
        conn.close()
        raise ValueError(f"Sender with id {sender_id} not found")
    
    if sender["role"] not in VALID_ROLES:
        conn.close()
        raise ValueError(f"Invalid sender role: {sender['role']}")
    
    route = route or DEFAULT_ROUTE
    now = datetime.utcnow().isoformat()
    
    cur.execute(
        """INSERT INTO letters(title, body, sender_id, created_at, status, current_step) 
           VALUES(?, ?, ?, ?, 'pending', 0)""",
        (title, body, sender_id, now),
    )
    lid = cur.lastrowid
    
    for idx, role in enumerate(route):
        cur.execute(
            "INSERT INTO steps(letter_id, step_index, role) VALUES(?, ?, ?)", 
            (lid, idx, role)
        )
    
    conn.commit()
    conn.close()
    return lid


def _get_step(conn, letter_id: int, step_index: int):
    """Get a specific step for a letter."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM steps WHERE letter_id=? AND step_index=?", 
        (letter_id, step_index)
    )
    return cur.fetchone()


def list_pending_for_role(db_path: str, role: str) -> List[Dict[str, Any]]:
    """List all pending letters for a specific role."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            s.*, 
            l.title, 
            l.body, 
            l.sender_id, 
            l.created_at, 
            l.status as letter_status,
            u.name as sender_name
        FROM steps s
        JOIN letters l ON l.id = s.letter_id
        JOIN users u ON u.id = l.sender_id
        WHERE s.role = ? AND s.status = 'pending' AND l.status = 'pending'
        ORDER BY l.created_at
        """,
        (role,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_all_letters(db_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all letters (sent/received) for a user."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    if user_id:
        # Get letters sent by user or where user is an approver
        cur.execute(
            """
            SELECT DISTINCT l.*, u.name as sender_name
            FROM letters l
            JOIN users u ON u.id = l.sender_id
            LEFT JOIN steps s ON s.letter_id = l.id
            WHERE l.sender_id = ? OR s.actor_id = ?
            ORDER BY l.created_at DESC
            """,
            (user_id, user_id),
        )
    else:
        # Get all letters
        cur.execute(
            """
            SELECT l.*, u.name as sender_name
            FROM letters l
            JOIN users u ON u.id = l.sender_id
            ORDER BY l.created_at DESC
            """
        )
    
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def act_on_letter(
    db_path: str, 
    letter_id: int, 
    actor_id: int, 
    action: str, 
    comments: Optional[str] = None,
    recommendations: Optional[str] = None
) -> Dict[str, Any]:
    """Actor approves, rejects or merely comments on a pending step.
    
    action: 'approve', 'reject', or 'comment'
    comments: Optional comments on the decision
    recommendations: Optional recommendations for improvement
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Get letter
    cur.execute("SELECT * FROM letters WHERE id = ?", (letter_id,))
    letter = cur.fetchone()
    if not letter:
        conn.close()
        raise ValueError("Letter not found")
    
    # Get actor
    cur.execute("SELECT * FROM users WHERE id = ?", (actor_id,))
    user = cur.fetchone()
    if not user:
        conn.close()
        raise ValueError("Actor not found")

    # handle comment action separately (does not advance or close steps)
    now = datetime.utcnow().isoformat()
    if action == 'comment':
        # allow anyone except students to comment
        if user['role'].lower() == 'student':
            conn.close()
            raise ValueError("Students are not permitted to comment")
        # find current step for letter
        current_step = letter['current_step']
        step = _get_step(conn, letter_id, current_step)
        if not step:
            conn.close()
            raise ValueError("No approval step found to comment on")
        full_comments = comments or ''
        if recommendations:
            full_comments += f"\nRecommendations: {recommendations}"
        # append comment with actor info and timestamp
        existing = step.get('comments') or ''
        new_comment = f"[{now}] {user['name']} ({user['role']}): {full_comments}"
        combined = existing + ('\n' if existing else '') + new_comment
        cur.execute(
            """UPDATE steps SET comments=? WHERE id=?""",
            (combined, step['id'])
        )
        conn.commit()
        result = get_letter(db_path, letter_id)
        conn.close()
        return result
    
    # existing approval/rejection logic follows
    # Check if letter is already finalized
    if letter["status"] in ["approved", "rejected"]:
        conn.close()
        raise ValueError(f"Letter already {letter['status']}")
    
    # Get current step
    current_step = letter["current_step"]
    step = _get_step(conn, letter_id, current_step)
    if not step:
        conn.close()
        raise ValueError("No approval step found")
    
    if step["status"] != "pending":
        conn.close()
        raise ValueError("Step already acted on")
    
    # Role validation
    if user["role"] != step["role"]:
        conn.close()
        raise ValueError(f"User role '{user['role']}' cannot act on step role '{step['role']}'")

    now = datetime.utcnow().isoformat()
    full_comments = comments or ""
    if recommendations:
        full_comments += f"\nRecommendations: {recommendations}"
    
    if action == "approve":
        # Update current step
        cur.execute(
            """UPDATE steps 
               SET status='approved', actor_id=?, comments=?, acted_at=? 
               WHERE id=?""",
            (actor_id, full_comments, now, step["id"]),
        )
        
        # Check if there are more steps
        cur.execute("SELECT COUNT(1) as c FROM steps WHERE letter_id = ?", (letter_id,))
        total = cur.fetchone()["c"]
        next_index = current_step + 1
        
        if next_index >= total:
            # All steps approved
            cur.execute(
                "UPDATE letters SET status='approved', current_step = ? WHERE id=?", 
                (current_step, letter_id)
            )
        else:
            # Move to next step
            cur.execute(
                "UPDATE letters SET current_step = ? WHERE id = ?", 
                (next_index, letter_id)
            )
            
    elif action == "reject":
        # Update current step as rejected
        cur.execute(
            """UPDATE steps 
               SET status='rejected', actor_id=?, comments=?, acted_at=? 
               WHERE id=?""",
            (actor_id, full_comments, now, step["id"]),
        )
        # Mark letter as rejected
        cur.execute(
            "UPDATE letters SET status='rejected', current_step = ? WHERE id=?", 
            (current_step, letter_id)
        )
        # Notify sender that their letter was rejected
        notify_sender(db_path, letter_id, full_comments)
    else:
        conn.close()
        raise ValueError("Unknown action. Use 'approve' or 'reject'")

    conn.commit()
    
    # Return updated letter with all steps
    result = get_letter(db_path, letter_id)
    conn.close()
    return result


def notify_sender(db_path: str, letter_id: int, reason: str) -> None:
    """Send a notification to the original sender about rejection.
    This is currently a stub; in a real system it might send an email.
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT sender_id FROM letters WHERE id = ?", (letter_id,))
    row = cur.fetchone()
    if row:
        sender_id = row["sender_id"]
        print(f"Notification: letter {letter_id} rejected; notifying user {sender_id}. Reason: {reason}")
    conn.close()


def resend_letter(db_path: str, letter_id: int, sender_id: int, title: str, body: str) -> None:
    """Allow sender to update content and reset letter for approval.
    Only permitted if the sender_id matches and letter is rejected.
    This resets all steps to pending and status to pending.
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT sender_id, status FROM letters WHERE id = ?", (letter_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError("Letter not found")
    if row["sender_id"] != sender_id:
        conn.close()
        raise ValueError("Not authorized to resend this letter")
    if row["status"] != "rejected":
        conn.close()
        raise ValueError("Only rejected letters can be resent")
    cur.execute("UPDATE letters SET title = ?, body = ?, status = 'pending', current_step = 0 WHERE id = ?", (title, body, letter_id))
    cur.execute("UPDATE steps SET status='pending', actor_id=NULL, comments=NULL, acted_at=NULL WHERE letter_id = ?", (letter_id,))
    conn.commit()
    conn.close()


def get_letter(db_path: str, letter_id: int) -> Dict[str, Any]:
    """Get a letter with all its approval steps."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Get letter with sender info
    cur.execute(
        """
        SELECT l.*, u.name as sender_name, u.role as sender_role
        FROM letters l
        JOIN users u ON u.id = l.sender_id
        WHERE l.id = ?
        """,
        (letter_id,),
    )
    letter = cur.fetchone()
    if not letter:
        conn.close()
        raise ValueError("Letter not found")
    
    # Get all steps with actor info
    cur.execute(
        """
        SELECT s.*, u.name as actor_name, u.role as actor_role
        FROM steps s
        LEFT JOIN users u ON u.id = s.actor_id
        WHERE s.letter_id = ?
        ORDER BY s.step_index
        """,
        (letter_id,),
    )
    steps = [dict(r) for r in cur.fetchall()]
    
    # Get current pending step info
    current_step_info = None
    if letter["status"] == "pending":
        for step in steps:
            if step["step_index"] == letter["current_step"]:
                current_step_info = {
                    "role": step["role"],
                    "status": step["status"]
                }
                break
    
    conn.close()
    return {
        "letter": dict(letter),
        "steps": steps,
        "current_step": current_step_info,
        "total_steps": len(steps)
    }


def get_letter_history(db_path: str, letter_id: int) -> List[Dict[str, Any]]:
    """Get the complete history of a letter (all actions taken)."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT 
            s.step_index,
            s.role,
            s.status,
            s.comments,
            s.acted_at,
            u.name as actor_name,
            u.role as actor_role
        FROM steps s
        LEFT JOIN users u ON u.id = s.actor_id
        WHERE s.letter_id = ?
        ORDER BY s.step_index
        """,
        (letter_id,),
    )
    
    history = [dict(r) for r in cur.fetchall()]
    conn.close()
    return history