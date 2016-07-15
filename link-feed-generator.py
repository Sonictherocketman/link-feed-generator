""" A log parser that extracts any links from designated channels
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

link_regex = re.compile(r".*(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)")

description_format = '%s\nCreated by link-feed-generator.'


class NoSuchFormatterException(Exception):
    pass


def get_log_line(line, format):
    parsed = parse(format, line)
    if parsed:
        link = get_link(parsed['message'])
        if link:
            print('Found link: %s' % link)
            anchor = r'<a href="%s">%s</a>' % (link, link)
            message = parsed['message'].replace(link, anchor)
            return LogLine(dt_parse(parsed['timestamp']),
                    parsed['user'], message)


def get_link(text):
    """ Given a string of text, return the first link found or None """
    matches = re.match(link_regex, text)
    if matches:
        return matches.groups()[0]


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


def get_file(input):
    """ If the input is a file, return it, else return the most recent file
    that matches the pattern given.
    """
    if os.path.isfile(input):
        return input

    if os.path.isdir(input):
        input = '%s/*' % input

    files = sorted(glob.glob(input))

    if not files:
        return None

    print('Multiple log files found. Using: %s' % files[-1])
    return files[-1]


# Begin Formatters


def xml_formatter(existing, line, name='', description=''):
    elements = get_elements_from_old_xml(existing) if existing else []
    rss = PyRSS2Gen.RSS2(
        title=name,
        description=description,
        link='',

        items = [
            PyRSS2Gen.RSSItem(
                guid=hashlib.md5(line.link.encode('utf-8')).hexdigest(),
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
            help='An path to the given channel\'s logs or an '
            'individual log file.')
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
    parser.add_argument('-n', '--name',
            help='A name for the output feed.',
            default='Link Log')
    parser.add_argument('-d', '--description',
            help='A description for the output feed.',
            default='Link Log')
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

    description = description_format % args.description

    # Find the most recent file.

    latest = get_file(args.input)
    if not latest:
        print("No files found.")
        return

    offset_file = (args.offset
            if args.offset
            else '/tmp/link-logger-%s' % hashlib.md5(latest.encode('utf-8')).hexdigest())

    # Parse the logs.
    while True:
        try:
            for line in Pygtail(latest, offset_file=offset_file):
                parsed_line = get_log_line(line, args.format)
                if parsed_line:
                    text = get_text_from_file(args.output)
                    with open(args.output, 'w') as out:
                        out.write(formatter(text, parsed_line, name=args.name,
                            description=description))
            sleep(0.1)
        except AttributeError as e:
            print('ERROR: Could not open log file %s' % latest)
            break


if __name__ == '__main__':
    main()
