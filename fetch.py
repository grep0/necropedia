import sys
import re
import csv
from datetime import datetime

import pywikibot
import dateutil.parser

# May all the programming gods forgive me for parsing with regexes
# Extracting date in the formats '13 May 2010' or 'May 13, 2010'
re_month = re.compile(r'(?:January|February|March|April|May|June|July|August|Septemper|October|November|December)')
re_year = re.compile(r'(?:19|20)[0-9][0-9]')
re_date = re.compile(r'(?:[1-3]?[0-9]\s{0}|{0}\s[1-3]?[0-9]),?\s{1}'.format(re_month.pattern, re_year.pattern))
# This is typical form within the article body:
# '''Foo Barsson''' (January 1, 1941 - March 3, 2002)
# We allow the case when only birth year is known, setting the date to mid-year
re_birth_death = re.compile(r'({0}|{1})\s?(?:-|–|{{ndash}})\s?({0})'
        .format(re_date.pattern, re_year.pattern))
# Patterns within infobox:
# {{Birth date|1923|4|5}}
# {{Birth year|1945}}
# {{Death date|2002|11|2}}
re_birth_date = re.compile(r'\{\{Birth[ _]date\s*(?:\|df=\w+)?\|([0-9]{4}\|[0-9]{1,2}\|[0-9]{1,2})\s*[|}]', re.I)
re_birth_year = re.compile(r'\{\{Birth[ _]year\s*\|([0-9]{4})\s*[|}]', re.I)
re_death_date = re.compile(r'\{\{Death[ _]date(?:[ _]and[ _]age)?\s*(?:\|df=\w+)?\|([0-9]{4}\|[0-9]{1,2}\|[0-9]{1,2})\s*[|}]', re.I)
# It could be a pattern above or just a date as described above
re_infobox_birth = re.compile(r'birth_date\s*=\s*({0}|{1}|{2}|{3})'
        .format(re_date.pattern, re_year.pattern, re_birth_date.pattern, re_birth_year.pattern), re.I)
re_infobox_death = re.compile(r'death_date\s*=\s*({0}|{1})'
        .format(re_date.pattern, re_death_date.pattern), re.I)

# Replacing all the &nbsp; with spaces and &ndash; with actual ndash.
# Do we need to replace other characters?
def unescape(text):
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&ndash;', '–')
    return text

# Given the start bracket, find the end bracket and return the text within them
def find_balance_bracket(text, start_pos):
    BRACKETS = { '{':'}', '(':')', '[':']' }
    try:
        sb = text[start_pos]
        eb = BRACKETS[sb]
    except:
        return None
    i=1
    for pos in range(start_pos+1,len(text)):
        if text[pos]==sb:
            i+=1
        elif text[pos]==eb:
            i-=1
            if i==0:
                return text[start_pos:pos+1]
    return None

def parse_date(s):
    # Ensure that default date is July 1 when only year is known
    return dateutil.parser.parse(s, default=datetime(1800,7,1,0,0,0)).date()

# Try to parse the article text to extract birth/death dates
# We fail to parse some well formatted articles, e.g.
#   [[Avraham Barkai]]
#   [[Frank Bielec]]
#   [[Chrystelle Trump Bond]]
#   [[Hans Breuer (physicist)]]
#   [[Frieda Rapoport Caplan]]
def parse_birth_death(text):
    birth = death = None
    # Search for {{Infobox}} as it might be easier to parse
    pos = text.find('{{Infobox')
    if pos>=0:
        infobox = find_balance_bracket(text, pos)
    else:
        infobox = None
    if infobox:
        #print(infobox)
        mm = re_infobox_birth.search(infobox)
        if mm:
            #print('birth', mm)
            if mm.group(2):
                # YYYY|MM|DD
                birth = mm.group(2).replace('|','-')
            elif mm.group(3):
                # Date string
                birth = mm.group(3)
            else:
                # Year only
                birth = mm.group(1)
            #print("birth", birth)
        mm = re_infobox_death.search(infobox)
        if mm:
            #print('death', mm)
            if mm.group(2):
                # YYYY|MM|DD
                death = mm.group(2).replace('|','-')
            else:
                # Date string
                death = mm.group(1)
            #print("death", death)
        # Cut off infobox
        text = text[:pos] + text[pos + len(infobox):]
    if not birth or not death:
        # We failed to extract dates from infobox, trying the body
        m = re_birth_death.search(text)
        if not m:
            raise ValueError('Cannot extract birth/death')
        birth, death = m.groups()
    try:
        birth = parse_date(birth)
        death = parse_date(death)
    except ValueError:
        raise ValueError('Cannot parse date')
    return birth, death

# Irrelevant articles (lists)
re_lists = re.compile('(List of|Deaths in|User:)', re.I)
# Assume "death from COVID" for those who have these magic words in the text
re_covid = re.compile(r'COVID|[Cc]oronavirus')

def scan_cat(site, catname, limit=None):
    res = []
    num_failed = 0
    cat = pywikibot.Category(site, catname)
    for a in cat.articles():
        if a.is_categorypage() or not a.exists():
            continue
        title = a.title()
        if re_lists.search(title):
            continue
        #print('Retrieving article', title)
        text = unescape(a.text)
        try:
            birth, death = parse_birth_death(text)
        except ValueError as e:
            print('Failed to parse {} : {}'.format(a, e))
            num_failed += 1
            continue
        covid = (re_covid.search(text) is not None)
        created = a.oldest_revision.timestamp.date()
        print(repr(title), birth, death, covid, created)
        res.append([title, birth, death, covid, created])
        if limit is not None and len(res)>=limit:
            print("Limit reached")
            break
    print ("Num successful:", len(res), " failed:", num_failed)
    return res

def save_result(data, filename):
    with open(filename, 'w') as f:
        w = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(['Name', 'Birth', 'Death', 'Covid', 'Created'])
        for row in data:
            w.writerow(row)

if __name__ == "__main__":
    years = map(int, sys.argv[1:])
    site = pywikibot.Site('en', 'wikipedia')
    for year in years:
        print("*** {} DEATHS ***".format(year))
        start_scan = datetime.now()
        data = scan_cat(site, 'Category:{} deaths'.format(year))
        print("Scan time:", datetime.now() - start_scan)
        save_result(data, 'deaths{}.csv'.format(year))
