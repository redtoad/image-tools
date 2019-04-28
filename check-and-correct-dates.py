
"""
Usage: check-and-correct-date.py DIR

Checks whether an image is chronologically in the right place.
This assumes the following directory stucture:

        <ROOT>
        ├── 2005
        │   ├── 0503
        │   ├── 0509 - tarvel
        │   ├── ...
        ├── 2008
        ├── 2011
        ├── 2012
        │   ├── 1201
        │   ├── 1202
        │   ├── 1204 wedding
        │   │   ├── photographer
        │   │   ├── Max
        │   │   │   ├── pics
        │   │   │   └── movies
        │   │   ├── Mom
        │   │   ├── Dad
        │   └── ...
        │

"""

import datetime
import os
import re
import sys

from exif import Image
import termcolor

import pytest

RED = r'\033[0;31m'
NC = r'\033[0m'

def check_date(img):
    with open(img, 'rb') as image_file:
        path_ts = guess_date_from_path(img)
        to_datetime = lambda ts: datetime.datetime.strptime(ts, '%Y:%m:%d %H:%M:%S')
        try:
            my_image = Image(image_file)
            img_ts = to_datetime(my_image.datetime)
            precise_enough = path_ts.is_precise() and abs((img_ts - path_ts.as_datetime()).seconds) > 2
            if img_ts not in path_ts and precise_enough:
                termcolor.cprint('! %s  %s  %s' % (img_ts, path_ts, img), 'red', attrs=['bold'])
            else:
                termcolor.cprint('  %s  %s  %s' % (img_ts, path_ts, img))
        except (IOError, KeyError, AttributeError) as e:
            termcolor.cprint('E %s  %s  %s  Error: %s' % ('.... .. .. .. .. ..', path_ts, img, e), 'red', attrs=['bold'])


class ApproxDate(object):

    def __init__(self, year: int, month: int = None, day: int = None, hour: int = None, minute: int = None, second: int = None):
        self.year, self.month, self.day = year, month, day
        self.hour, self.minute, self.second = hour, minute, second

    def is_precise(self):
        is_not_none = lambda x: x is not None
        return all(map(is_not_none, [self.year, self.month, self.day, self.hour, self.minute, self.second]))

    def as_datetime(self) -> datetime.datetime:
        if not self.is_precise():
            raise ValueError("Not precise enough to be converted to datetime!")
        return datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)

    def __contains__(self, ts):
        if isinstance(ts, ApproxDate):
            if ts == self:
                return True

            # pairwise comparison of values
            # Example:
            # ts = 2019-10-17 10:23:18
            # slf: 2019-10-17 10:23:18 -> ts contained
            #      2019-10-17 10:23:XX -> ts contained
            #      2019-10-17 10:XX:XX -> ts contained
            #      2019-10-17 XX:XX:XX -> ts contained
            #      2019-10-XX XX:XX:XX -> ts contained
            #      2019-XX-XX XX:XX:XX -> ts contained

            self_values = [self.year, self.month, self.day, self.hour, self.minute, self.second]
            other_values = [ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second]
            for slf, oth in zip(self_values, other_values):
                if slf is None and oth is not None:
                    return True
                elif slf is not None and oth is None:
                    return False
                if slf != oth:
                    return False
            # strictly speaking not necessary as we test for equality first
            return True

        if isinstance(ts, datetime.datetime):
            return ApproxDate(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second) in self

        if isinstance(ts, datetime.date):
            return ApproxDate(ts.year, ts.month, ts.day) in self

        return False

    def __eq__(self, other):
        if self is other:
            return True
        if isinstance(other, ApproxDate):
            if all([
                self.year == other.year,
                self.month == other.month,
                self.day == other.day,
                self.hour == other.hour,
                self.minute == other.minute,
                self.second == other.second
            ]):
                return True
        return False

    MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

    def __str__(self):
        values = (self.year, self.month, self.day, self.hour, self.minute, self.second)
        escaped = ['..' if val is None else '{:02d}'.format(val) for val in values]
        return '{}-{}-{} {}:{}:{}'.format(*escaped)

    def __repr__(self):
        if self.hour is not None:
            return '<ApproxDate "%s-%s-%s %s:%s:%s">' % (self.year, self.month, self.day, self.hour, self.minute, self.second)
        elif self.day is not None:
            return '<ApproxDate "somewhen on %s">' % datetime.date(self.year, self.month, self.day)
        elif self.month is not None:
            return '<ApproxDate "somewhen in %s %s">' % (self.MONTHS[self.month-1], self.year)
        else:
            return '<ApproxDate "somewhen in %s">' % (self.year, )


def test_approxdate_isprecise():
    assert ApproxDate(2019, 12, 14, 9, 45, 12).is_precise()
    assert ApproxDate(2019, 12, 14, 9, 0, 12).is_precise()
    assert not ApproxDate(2019, 12, 14, 9).is_precise()
    assert not ApproxDate(2019, 12, 14).is_precise()
    assert not ApproxDate(2019, 12).is_precise()
    assert not ApproxDate(2019).is_precise()


@pytest.mark.parametrize("one,two", [
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9, 45, 12)),
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9, 45)),
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9)),
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14)),
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12)),
    (ApproxDate(2019, 12, 14, 9, 45, 12), ApproxDate(2019)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9, 45, 12)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9, 45)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14, 9)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12, 14)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019, 12)),
    (datetime.datetime(2019, 12, 14, 9, 45, 12), ApproxDate(2019)),
    (datetime.date(2019, 12, 14), ApproxDate(2019, 12, 14)),
    (datetime.date(2019, 12, 14), ApproxDate(2019, 12)),
    (datetime.date(2019, 12, 14), ApproxDate(2019)),
])
def test_approxdate_isin(one, two):
    assert one in two


PATTERS = [
    re.compile(r'^(?:IMG|VID|PANO)_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})(?:_\d+)?\.(?:jpg|mpg|mp4)', re.I),  # Nexus 5/5X
    re.compile(r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) (?P<hour>\d{2})\.(?P<minute>\d{2})\.(?P<second>\d{2})(?:-\d+)?\.(?:jpg|png)', re.I),  # Wildfire S/Samsung
    re.compile(r'^(?:IMG|VID)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-WA\d+\.(jpe?g|mp4)', re.I),  # WhatsApp
    re.compile(r'^(?:IMG|VID)-\d{8}-WA\d+ \((?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2})_(?P<minute>\d{2})_(?P<second>\d{2})\.\d+\)\.(jpe?g|mp4)', re.I),  # WhatsApp
]

PATH_MONTH_REG = re.compile('^(?P<year>\d{2})(?P<month>01|02|03|04|05|06|07|08|09|10|11|12)')
PATH_YEAR_REG = re.compile('^\d{4}$')


def guess_date_from_path(path):
    """
    Extracts date from path.
    """
    root, base = os.path.split(path)

    for reg in PATTERS:
        m = reg.match(base)
        if m is not None:
            matches = m.groupdict()
            keys = ['year', 'month', 'day', 'hour', 'minute', 'second']
            values = [int(matches[key]) for key in keys if matches.get(key) is not None]
            return ApproxDate(*values)

    while root:
        root, base = os.path.split(root)

        m = PATH_MONTH_REG.match(base)
        if m is not None:
            year = 1900 + int(m.group('year'))
            if year < 1970: year += 100
            month = int(m.group('month'))
            return ApproxDate(year, month)

        m = PATH_YEAR_REG.match(base)
        if m is not None:
            year = int(base)
            if year < 1970: year += 100
            return ApproxDate(year)

    return None


@pytest.mark.parametrize('inp,out', [
    ('IMG_20140604_074913.jpg', ApproxDate(2014, 6, 4, 7, 49, 13)),  # Nexus 5/5X/MHA
    ('2014-12-29 12.53.54.jpg', ApproxDate(2014, 12, 29, 12, 53, 54)),  # HTC Wildfire S
    ('2013-08-15 14.27.57.jpg', ApproxDate(2013, 8, 15, 14, 27, 57)),  # Samsung i9000
    ('IMG-20120803-WA0001.jpg', ApproxDate(2012, 8, 3)),  # WhatsApp
    ('IMG-20170730-WA0000 (2017-10-14T07_59_05.000).jpg', ApproxDate(2017, 10, 14, 7, 59, 5)),  # WhatsApp
    ('2012/1204 - Hochzeit/Mama Ursula/BILD0325.JPG', ApproxDate(2012, 4)),
    ('2017/Foto-DVD der Eulengruppe 2017/Turnen/IMG_7565.JPG', ApproxDate(2017)),
    ('DSC_2098.JPG', None),
])
def test_guess_date_from_path(inp, out):
    assert guess_date_from_path(inp) == out


if __name__ == '__main__':
    dir = sys.argv[1]
    for root, dirs, file_names in os.walk(dir):
        file_names.sort()
        for file_name in file_names:
            if file_name.lower().endswith(('jpg', 'png')):
                img_path = os.path.join(root, file_name)
                check_date(img_path)

