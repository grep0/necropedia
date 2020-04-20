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
re_infobox = re.compile(r'\{\{Infobox.*?\n\}\}', re.M|re.S|re.I)
re_birth_date = re.compile(r'\{\{Birth[ _]date(?:\|df=\w+)?\|([0-9]{4}\|[0-9]{1,2}\|[0-9]{1,2})[|}]', re.I)
re_birth_year = re.compile(r'\{\{Birth[ _]year\|([0-9]{4})[|}]', re.I)
re_death_date = re.compile(r'\{\{Death[ _]date(?: and age)?(?:\|df=\w+)?\|([0-9]{4}\|[0-9]{1,2}\|[0-9]{1,2})[|}]', re.I)
re_infobox_birth = re.compile(r'birth_date\s*=\s*({0}|{1}|{2}|{3})'.format(re_date.pattern, re_year.pattern, re_birth_date.pattern, re_birth_year.pattern), re.I)
re_infobox_death = re.compile(r'death_date\s*=\s*({0}|{1})'.format(re_date.pattern, re_death_date.pattern), re.I)

def interpret(text):
    birth = death = None
    m = re_infobox.search(text)
    if m:
        infobox = m.group(0)
        #print(infobox)
        mm = re_infobox_birth.search(infobox)
        if mm:
            if mm.group(2):
                birth = mm.group(2).replace('|','-')
            elif mm.group(3):
                birth = mm.group(3)
            else:
                birth = mm.group(1)
            #print("birth", birth)
        mm = re_infobox_death.search(infobox)
        if mm:
            if mm.group(2):
                death = mm.group(2).replace('|','-')
            else:
                death = mm.group(1)
            #print("death", death)
        text = text[:m.start()] + text[m.end():]
    if not birth or not death:
        m = re_birth_death.search(text)
        if not m:
            raise ValueError('Cannot extract birth/death')
        birth, death = m.groups()
    try:
        birth = parse_dt(birth).date()
        death = parse_dt(death).date()
    except ValueError:
        raise ValueError('Cannot parse date')
    covid = (re_covid.search(text)) is not None
    return birth, death, covid


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
        try:
            birth, death, covid = interpret(text)
        except ValueError as e:
            print('Failed to parse {} : {}'.format(a, e))
            continue
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
