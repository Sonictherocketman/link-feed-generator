""" An IRC log parser that extracts any links from designated channels
author: Brian Schrader
since: 2016-07-11
"""

from collections import namedtuple
from time import sleep
import argparse
import glob
import hashlib
import sys, os, re

from dateutil.parser import parse as dt_parse
from lxml import objectify, etree, html
from lxml.builder import E
from parse import parse
from pygtail import Pygtail

from lib import PyRSS2Gen


LogLine = namedtuple('LogLine', 'timestamp user link')

log_format = '[{timestamp}] <{user}> {message}\n'

link_regex = re.compile(r"(http(s)?://[^ ]+)")


class NoSuchFormatterException(Exception):
    pass


import contextlib


def get_log_line(line, format):
    parsed = parse(format, line)
    if parsed:
        link = get_link(parsed['message'])
        if link:
            message = link_regex.sub(r'<a href="\1">\1</a>', parsed['message'])
            return LogLine(dt_parse(parsed['timestamp']),
                    parsed['user'], message)


def get_link(text):
    """ Given a string of text, return the first link found or None """
    matches = re.match(link_regex, text)
    if matches:
        return matches.group(0)


def rfc822(timestamp):
    return timestamp.strftime("%a, %d %b %Y %H:%M:%S %z")


def get_elements_from_old_xml(existing):
    root = etree.fromstring(existing.encode('utf-8'))
    channel = root.xpath('//channel')[0]
    elements = [
        { child.tag: child.text for child in item }
        for item in channel.iterchildren()
    ]
    return [e for e in elements if e]


def get_text_from_file(filename):
    if os.path.isfile(filename):
        with open(filename) as out:
            return out.read()
    else:
        return ''


# Begin Formatters


def xml_formatter(existing, line):
    elements = get_elements_from_old_xml(existing) if existing else []
    rss = PyRSS2Gen.RSS2(
        title='IRC Log Links',
        description='A collection of links extracted from logs.',
        link='',

        items = [
            PyRSS2Gen.RSSItem(
                title=line.user,
                description=line.link,
                pubDate=line.timestamp
                )
        ] + [PyRSS2Gen.RSSItem(**item) for item in elements]

    )
    return rss.to_xml()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('input',
            help='An path to the given channel\'s logs.')
    parser.add_argument('-o', '--output',
            help='An output file to write.',
            default='-')
    parser.add_argument('-s', '--offset',
            help='An offset file location.',
            default=None)
    parser.add_argument('--output-format',
            help='The output format. Options: xml\n'
            'More coming soon.'
            'Default: %(default)s',
            default='xml')
    parser.add_argument('-f', '--format',
            help='The format of incomming messages.'
            'See this spec for more info: \n'
            'https://github.com/r1chardj0n3s/parse#format-specification\n'
            'Default: %(default)s',
            default=log_format)
    args = parser.parse_args()


    if args.output_format == 'xml':
        formatter = xml_formatter
    if not formatter:
        raise NoSuchFormatterException("No format called %s" % format)

    # Find the most recent file.

    files = sorted(glob.glob('%s/*' % args.input))
    if not files:
        print("No files found.")
        return

    latest = files[-1]
    offset_file = (args.offset
            if args.offset
            else '/tmp/%s' % hashlib.md5(latest.encode('utf-8')).hexdigest())

    # Parse the logs.

    try:
        for line in Pygtail(latest, offset_file=offset_file):
            parsed_line = get_log_line(line, args.format)
            if parsed_line:
                text = get_text_from_file(args.output)
                with open(args.output, 'w') as out:
                    out.write(formatter(text, parsed_line))
    except AttributeError as e:
        print('ERROR: Could not open log file %s' % latest)


if __name__ == '__main__':
    main()
