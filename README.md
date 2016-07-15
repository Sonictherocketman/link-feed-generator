Log Linker
==========

*A script that extracts links found in tailing log files, and adds them to an
RSS feed.*

## Installation

```bash
$ git clone https://github.com/Sonictherocketman/link-feed-generator.git
$ cd link-feed-generator
$ pip install -r requirements.txt
$ python3 link-feed-generator.py -o my-feed.xml /path/to/log/or/log/dir
```

## Getting Help

```bash
$ python3 link-feed-generator.py --help
```

**Note** When running the script on a directory of logs, only the last log in
the sorted list of logs will be tailed.
