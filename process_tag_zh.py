import sqlite3

def getdb (dbname = 'danbooru-tag-zh.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

def handle1 ():
    with getdb() as conn:
        c1 = conn.cursor()
        c1.execute('SELECT * FROM "danbooru-0-zh"')
        c2 = conn.cursor()
        
        while True:
            rows = c1.fetchmany(100)
            if not rows:
                break

            for row in rows:
                field3 = row['field3']
                tag = row['field1']
                tag_zh_list = field3.split('|')

                for tag_zh in tag_zh_list:
                    c2.execute(f'INSERT INTO tags (tag, tag_zh) values (?,?)', (tag, tag_zh))
        
        c1.close()
        c2.close()
        conn.commit()

handle1()