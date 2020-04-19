import re
import csv
from datetime import datetime

import pywikibot
from dateutil.parser import parse as parse_dt

re_covid = re.compile(r'COVID|[Cc]oronavirus')
re_month = re.compile(r'(?:January|February|March|April|May|June|July|August|Septemper|October|November|December)')
re_year = re.compile(r'(?:19|20)[0-9][0-9]')
re_date = re.compile(r'(?:[1-3]?[0-9]\s{0}|{0}\s[1-3]?[0-9]),?\s{1}'.format(re_month.pattern, re_year.pattern))
re_birth_death = re.compile(r'({0}|{1})\s?(?:-|–|&ndash;)\s?({0})'.format(re_date.pattern, re_year.pattern))

def scan_cat(site, catname, limit=None):
    res = []
    num_failed = 0
    cat = pywikibot.Category(site, catname)
    for a in cat.articles():
        if a.is_categorypage() or not a.exists():
            continue
        title = a.title()
        if 'List of ' in title or 'Deaths in' in title:
            continue
        print('Retrieving article', title)
        text = a.text
        m = re_birth_death.search(text)
        if not m:
            print('Cannot extract birth/death from', a)
            num_failed += 1
            continue
        birth, death = m.groups()
        try:
            birth = parse_dt(birth).date()
            death = parse_dt(death).date()
        except ValueError:
            print('Failed to parse date from', a)
            num_failed += 1
            continue
        covid = (re_covid.search(text)) is not None
        created = a.oldest_revision.timestamp.date()
        print(title, birth, death, covid, created)
        res.append([title, birth, death, covid, created])
        if limit is not None and len(res)>=limit:
            print("Limit reached")
            break
    print ("Num successful:", len(res), " failed:", num_failed)
    return res

if __name__ == "__main__":
    site = pywikibot.Site('en', 'wikipedia')
    for year in [2020, 2019]:
        print("*** {} DEATHS ***".format(year))
        data = scan_cat(site, 'Category:{} deaths'.format(year))
        with open('deaths{}.csv'.format(year), 'w') as f:
            w = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            w.writerow(['Name', 'Birth', 'Death', 'Covid', 'Created'])
            for row in data:
                w.writerow(row)
