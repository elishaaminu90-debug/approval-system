"""Simple CLI to interact with the approval system for manual testing."""
import argparse
from pathlib import Path
from src.approval_system import (
    init_db,
    create_user,
    send_letter,
    list_pending_for_role,
    list_all_letters,
    act_on_letter,
    get_letter,
    get_letter_history,
)
import json


def main():
    p = argparse.ArgumentParser(prog="approval-cli")
    p.add_argument("--db", default="approval.db", help="path to sqlite db")
    sub = p.add_subparsers(dest="cmd")

    # Init command
    a = sub.add_parser("init", help="Initialize database")

    # User commands
    cu = sub.add_parser("create-user", help="Create a new user")
    cu.add_argument("name", help="User's full name")
    cu.add_argument("role", help="User's role (e.g., Faculty, HOD, Dean, etc.)")

    # Letter commands
    sl = sub.add_parser("send", help="Send a new letter")
    sl.add_argument("sender_id", type=int, help="ID of the sender (must be Faculty Association)")
    sl.add_argument("title", help="Letter title")
    sl.add_argument("body", help="Letter body content")

    lp = sub.add_parser("list-pending", help="List pending letters for a role")
    lp.add_argument("role", help="Role to check pending letters for")

    la = sub.add_parser("list-all", help="List all letters")
    la.add_argument("--user-id", type=int, help="Filter by user ID (optional)")

    act = sub.add_parser("act", help="Act on a letter (approve/reject)")
    act.add_argument("letter_id", type=int, help="ID of the letter")
    act.add_argument("actor_id", type=int, help="ID of the acting user")
    act.add_argument("action", choices=["approve", "reject"], help="Action to take")
    act.add_argument("--comments", default="", help="Comments on the decision")
    act.add_argument("--recommendations", help="Recommendations for improvement")

    show = sub.add_parser("show", help="Show letter details")
    show.add_argument("letter_id", type=int, help="ID of the letter")

    history = sub.add_parser("history", help="Show letter history")
    history.add_argument("letter_id", type=int, help="ID of the letter")

    args = p.parse_args()
    db_path = args.db

    try:
        if args.cmd == "init":
            init_db(db_path)
            print(f"✅ Database initialized: {db_path}")
            print("\nValid roles:", ", ".join([
                "Faculty Association", "SRC", "Faculty", "HOD", "Dean",
                "Students Affairs Officer", "Dean of Student Affairs", "Vice Chancellor"
            ]))

        elif args.cmd == "create-user":
            uid = create_user(db_path, args.name, args.role)
            print(f"✅ User created with ID: {uid}")

        elif args.cmd == "send":
            lid = send_letter(db_path, args.sender_id, args.title, args.body)
            print(f"✅ Letter created with ID: {lid}")
            print("\nApproval route:")
            for i, role in enumerate(["SRC", "Faculty", "HOD", "Dean", 
                                     "Students Affairs Officer", "Dean of Student Affairs", 
                                     "Vice Chancellor"]):
                print(f"  {i+1}. {role}")

        elif args.cmd == "list-pending":
            rows = list_pending_for_role(db_path, args.role)
            if not rows:
                print(f"No pending letters for role: {args.role}")
            else:
                print(f"\n📨 Pending letters for {args.role}:")
                for r in rows:
                    print(f"\nID: {r['letter_id']}")
                    print(f"Title: {r['title']}")
                    print(f"From: {r['sender_name']}")
                    print(f"Sent: {r['created_at']}")
                    print(f"Step: {r['step_index'] + 1} of ?")

        elif args.cmd == "list-all":
            rows = list_all_letters(db_path, args.user_id)
            if not rows:
                print("No letters found")
            else:
                print(f"\n📋 Letters:")
                for r in rows:
                    print(f"\nID: {r['id']}")
                    print(f"Title: {r['title']}")
                    print(f"From: {r['sender_name']}")
                    print(f"Status: {r['status']}")
                    print(f"Sent: {r['created_at']}")

        elif args.cmd == "act":
            out = act_on_letter(
                db_path, 
                args.letter_id, 
                args.actor_id, 
                args.action,
                args.comments,
                args.recommendations
            )
            print(f"✅ Action recorded")
            print(f"\nLetter status: {out['letter']['status']}")
            if out['letter']['status'] == 'pending':
                next_step = out['current_step']
                print(f"Next approver: {next_step['role']}")

        elif args.cmd == "show":
            letter = get_letter(db_path, args.letter_id)
            print(f"\n📄 Letter ID: {letter['letter']['id']}")
            print(f"Title: {letter['letter']['title']}")
            print(f"From: {letter['letter']['sender_name']} ({letter['letter']['sender_role']})")
            print(f"Body: {letter['letter']['body']}")
            print(f"Status: {letter['letter']['status']}")
            print(f"Sent: {letter['letter']['created_at']}")
            print(f"\nApproval Steps:")
            for step in letter['steps']:
                status_icon = "✅" if step['status'] == 'approved' else "❌" if step['status'] == 'rejected' else "⏳"
                actor = f" by {step['actor_name']}" if step['actor_name'] else ""
                comments = f"\n      Comments: {step['comments']}" if step['comments'] else ""
                print(f"  {status_icon} Step {step['step_index'] + 1}: {step['role']}{actor}{comments}")

        elif args.cmd == "history":
            history = get_letter_history(db_path, args.letter_id)
            print(f"\n📜 History for letter ID: {args.letter_id}")
            for entry in history:
                status_icon = "✅" if entry['status'] == 'approved' else "❌" if entry['status'] == 'rejected' else "⏳"
                actor = f" by {entry['actor_name']}" if entry['actor_name'] else ""
                date = f" on {entry['acted_at']}" if entry['acted_at'] else ""
                comments = f"\n      Comments: {entry['comments']}" if entry['comments'] else ""
                print(f"\n  {status_icon} Step {entry['step_index'] + 1}: {entry['role']}{actor}{date}{comments}")

        else:
            p.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()