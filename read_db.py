import sqlite3

DB_PATH = "data/database.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Show tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cur.fetchall())

# Show some students
print("\nStudents:")
for row in cur.execute("SELECT sno, name, father_name, class, contact FROM students LIMIT 10;"):
    print(row)

# Show some users
print("\nUsers:")
for row in cur.execute("SELECT id, username, email FROM users;"):
    print(row)

conn.close()
