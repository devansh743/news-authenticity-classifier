import app
import sqlite3

print('db path', app.DB_PATH)
conn = app.get_db_connection()
print(conn.execute('select * from sqlite_master where type="table" and name="users"').fetchall())
print(conn.execute('pragma table_info(users)').fetchall())
try:
    conn.execute('insert into users (username, email, password) values (?,?,?)', ('temp','temp@example.com','x'))
    conn.commit()
    print('insert ok')
    print(conn.execute('select count(*) from users').fetchone())
except Exception as e:
    print('insert error', repr(e))
finally:
    conn.close()
