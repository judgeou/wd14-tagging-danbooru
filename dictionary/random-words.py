import sqlite3
import clipboard

def getdb (dbname = './dictionary/data/words.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

while True:
    with getdb() as conn:
        c = conn.cursor()

        c.execute('SELECT word from words order by random() limit 5')
        rows = c.fetchall()
        result = ''

        for row in rows:
            result += row['word'] + ', '

        print(result)
        clipboard.copy(result)

        c.close()
    input('press enter')