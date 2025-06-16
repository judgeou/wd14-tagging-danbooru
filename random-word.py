import random
from nltk.corpus import wordnet as wn
import nltk

# 选择词性（名词：'n'，动词：'v'，形容词：'a'，副词：'r'）
word_type = 'n'  # 名词
n = 10  # 要随机选择的单词数

# 从WordNet中获取所有该词性单词的集合
words_n = list(wn.all_synsets('n'))
words_a = list(wn.all_synsets('a'))
words_v = list(wn.all_synsets('v'))

# word.definition()
# 打印单词及其定义
while True:
    # 随机选择N个
    random_words_n = random.sample(words_n, n)
    random_words_a = random.sample(words_a, n)
    random_words_v = random.sample(words_v, n)

    random_words_a2 = random.sample(words_a, n)
    random_words_n2 = random.sample(words_n, n)

    for index, word in enumerate(random_words_n):
        word_n = random_words_n[index]
        word_a = random_words_a[index]
        word_v = random_words_v[index]
        word_a2 = random_words_a2[index]
        word_n2 = random_words_n2[index]

        name_n = word_n.lemmas()[0].name()
        name_a = word_a.lemmas()[0].name()
        name_v = word_v.lemmas()[0].name()
        name_a2 = word_a2.lemmas()[0].name()
        name_n2 = word_n2.lemmas()[0].name()

        print(f'{name_a} {name_n} {name_v} {name_a2} {name_n2}')
    input('enter')
