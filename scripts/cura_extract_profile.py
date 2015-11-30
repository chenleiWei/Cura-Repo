import fileinput
import re
import string
from zlib import decompress
from base64 import b64decode

RE_LINE = re.compile('\s*;\s*CURA_PROFILE_STRING:(.+)')


def parse_line(line):
    match = RE_LINE.match(line)
    if match:
        return match.groups()[0]
    else:
        return None


def decode_profile(data):
    return decompress(b64decode(data))


def parse_profile(text):
    return text.translate(string.maketrans('\f\b', '\n\n'))


def main(argv=None):
    if argv is None:
        argv = sys.argv
    for line in fileinput.input(argv):
        data = parse_line(line)
        if data:
            decoded = decode_profile(data)
            profile = parse_profile(decoded)
            print(profile)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
