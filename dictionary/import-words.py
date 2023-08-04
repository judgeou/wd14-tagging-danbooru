from bs4 import BeautifulSoup
import sqlite3
import os
import io

def getdb (dbname = './dictionary/data/words.db'):
    conn = sqlite3.connect(dbname)
    conn.row_factory = sqlite3.Row
    return conn

html_dir = r'F:\project\wd14-tagging-danbooru\dictionary\data'
html_files = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith(".html")]

with getdb() as conn:

    for i in range(len(html_files)):
        html_file = html_files[i]
        
        with io.open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            c = conn.cursor()
            
            for p in soup.find_all('p'):
                word = p.b.string
                type = p.i.string
                description = p.get_text()
                
                c.execute('INSERT INTO words (word, type, description) VALUES (?,?,?)', (word, type, description))

            c.close()
    conn.commit()