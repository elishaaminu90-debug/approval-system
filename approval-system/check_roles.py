import sqlite3

conn = sqlite3.connect("approval.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, name, role FROM users")
users = cur.fetchall()

print("\nCurrent users in system:")
print("-" * 50)
for user in users:
    print(f"ID: {user['id']}, Name: {user['name']}, Role: {user['role']}")

conn.close()
