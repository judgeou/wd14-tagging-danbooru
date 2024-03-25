from datetime import datetime
import re

url = 'http://static12.hentai-cosplays.com/upload/20230718/338/345592/79.jpg'

ext = url.split('/')[-1].split('.')[-1]

print(ext)