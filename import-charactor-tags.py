import json

with open('tags/tags.json', 'r', encoding='utf-8') as file:
    with open('tags/tag_charactor.txt', 'w', encoding='utf-8') as wfile:
        for line in file:
            row = json.loads(line)
            if (row['category'] == 4 and row['is_deprecated'] == False):
                wfile.write(row['name'] + '\n')