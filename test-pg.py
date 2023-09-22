import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to your postgres DB
conn = psycopg2.connect("dbname=postgres user=dan", cursor_factory=RealDictCursor)

# Open a cursor to perform database operations
cur = conn.cursor()

# Execute a query
sqlstr = f'''
select id from tags_s where tag like %s
'''
cur.execute(sqlstr, ('%blue_archive\\\\)',))

# Retrieve query results
records = cur.fetchall()

print(records)