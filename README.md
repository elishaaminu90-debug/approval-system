Approval System (Pure Python)
=================================

This small project implements a simple approval-letter workflow in pure Python, backed by SQLite.

Quick start
-----------

1. Initialize DB:

```bash
python cli.py --db approval.db init
```

2. Create users (roles must match steps):

```bash
python cli.py --db approval.db create-user Alice "Faculty Association"
python cli.py --db approval.db create-user Bob SRC
```

3. Send a letter:

```bash
python cli.py --db approval.db send 1 "Event request" "Please approve this event"
```

4. List pending for a role and act:

```bash
python cli.py --db approval.db list-pending HOD
python cli.py --db approval.db act 1 3 approve --comments "Looks good"
```

You can run the tests with `pytest`.
