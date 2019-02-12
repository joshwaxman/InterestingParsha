from pymongo import MongoClient
from collections import OrderedDict
from typing import Dict
import re
client = MongoClient()
db = client.sefaria

parshiot = db.parshiot
p = OrderedDict()
stop_list = "Yom Sukkot Pesach Rosh Shabbat Atzeret Shavuot -".split()
for parsha in parshiot.find():
    name = parsha['parasha']
    if not any(word in name for word in stop_list) or name == "Lech-Lecha":
        ref = parsha['ref']
        sefer, span = ref.split()
        start, end = span.split('-')
        start_ch, start_v = start.split(':')
        if ':' in end:
            end_ch, end_v = end.split(':')
        else:
            end_ch = start_ch
            end_v = end
        p[name] = (sefer, int(start_ch), int(start_v), int(end_ch), int(end_v))

texts = db.texts

# find out how many verses in the parasha
verse_count = dict()
for parsha, t in p.items():
    sefer, start_ch, start_v, end_ch, end_v = t
    search = dict(versionTitle="Tanach with Ta'amei Hamikra", title=sefer)
    book = texts.find_one(search)

    # how many pesukim in *first* chapter. Since start with 0, offset by 1
    # we might begin in the middle of the chapter, so subtract the start_v
    count = len(book['chapter'][start_ch-1]) - start_v + 1
    for ch in range(start_ch+1, end_ch): # middle chapters
        count += len(book['chapter'][ch-1])

    # how many pesukim in the *last chapter*.
    if start_ch != end_ch:
        count += end_v

    verse_count[parsha] = count


def count_interesting(p: Dict, commentary: str) -> Dict:
    # how many verses were interesting to Rashi in the parasha
    d = dict()
    for parsha, t in p.items():
        sefer, start_ch, start_v, end_ch, end_v = t
        search = dict(versionTitle="On Your Way", title=commentary + ' on ' + sefer)
        book = texts.find_one(search)

        # for Rashbam, look here:
        if commentary == 'Rashbam': # look for alternative
            search = dict(versionTitle=re.compile('[Dd]aat'), title=commentary + ' on ' + sefer)
            book = texts.find_one(search)

        if book is None:
            print('error, book not found!')

        # how many "interesting" pesukim in *first* chapter.
        # Since start with 0, offset by 1
        # we might begin in the middle of the chapter, so subtract the start_v
        interesting_pesukim = 0
        num_commentaries = 0

        if isinstance(book['chapter'], list):
            the_book = book['chapter']
        elif isinstance(book['chapter'], dict):
            the_book = book['chapter']['default']

        first_chapter = the_book[start_ch-1]
        for verse in range(start_v-1, len(first_chapter)):
            if len(first_chapter[verse]) > 0:
                interesting_pesukim += 1
                num_commentaries += len(first_chapter[verse])

        for ch in range(start_ch+1, end_ch): # middle chapters
            try:
                chapter = the_book[ch-1]
            except:
                x = 2
            for v in range(len(chapter)):
                if len(chapter[v]) > 0:
                    interesting_pesukim += 1
                    num_commentaries += len(chapter[v])

        # last chapter
        if start_ch != end_ch:
            chapter = the_book[end_ch - 1]
            # sometimes commentaries are truncated if they don't comment on last verse
            # therefore, should only go until the min end_v and actual len
            for v in range(min(end_v, len(chapter))):
                if len(chapter[v]) > 0:
                    interesting_pesukim += 1
                    num_commentaries += len(chapter[v])

        d[parsha] = (interesting_pesukim, num_commentaries, interesting_pesukim / verse_count[parsha], num_commentaries / verse_count[parsha])
    return d

rashi = count_interesting(p, 'Rashi')
ibn_ezra = count_interesting(p, 'Ibn Ezra')
ramban = count_interesting(p, 'Ramban')
rashbam = count_interesting(p, 'Rashbam')
sforno = count_interesting(p, 'Sforno')
print('rashi', rashi)
print('ibn_ezra', ibn_ezra)
print('ramban', ramban)
print('rashbam', rashbam)
print('sforno', sforno)

import csv

with open('interesting.csv', mode='w', newline='') as interesting_file:
    writer = csv.writer(interesting_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow('Sidra, Number of Verses, '
                    'Rashi Verse Count, Rashi Comments, Rashi Verse Ratio, Rashi Comment Ratio, '
                    'Ibn Ezra Verse Count, Ibn Ezra Comments, Ibn Ezra Verse Ratio, Ibn Ezra Comment Ratio, '
                    'Ramban Verse Count, Ramban Comments, Ramban Verse Ratio, Ramban Comment Ratio, '
                    'Rashbam Verse Count, Rashbam Comments, Rashbam Verse Ratio, Rashbam Comment Ratio, '
                    'Sforno Verse Count, Sforno Comments, Sforno Verse Ratio, Sforno Comment Ratio'.split(', '))
    for parsha in p:
        writer.writerow([parsha, verse_count[parsha],
                         rashi[parsha][0], rashi[parsha][1], rashi[parsha][2], rashi[parsha][3],
                         ibn_ezra[parsha][0], ibn_ezra[parsha][1], ibn_ezra[parsha][2], ibn_ezra[parsha][3],
                         ramban[parsha][0], ramban[parsha][1], ramban[parsha][2], ramban[parsha][3],
                         rashbam[parsha][0], rashbam[parsha][1], rashbam[parsha][2], rashbam[parsha][3],
                         sforno[parsha][0], sforno[parsha][1], sforno[parsha][2], sforno[parsha][3]
                         ])

# versionTitle
# :
# "On Your Way"
#{title: /Rashi on Exodus/, language: 'he'}