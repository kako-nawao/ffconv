#!/usr/bin/python
__author__ = 'kako'

import argparse

from .file_processor import FileProcessor


parser = argparse.ArgumentParser(description='Convert media files')

parser.add_argument('input', type=str, help='Name of the input file to convert')
parser.add_argument('profile', type=str, help='Name of the profile to use (roku, etc)')
parser.add_argument('--output', type=str, help='Name of the merged output file, if '
                                               'not supplied original file is removed')

args = parser.parse_args()


def process():
    print('ffconv 0.0.1 -----------')

    processor = FileProcessor(args.input, args.output, args.profile)
    try:
        processor.process()

    except Exception as e:
        print('Error: {}'.format(e))
        fname = 'ffconv-failed.log'
        return_code = 1

    else:
        fname = 'ffconv-success.log'
        return_code = 0

    with open(fname, 'a') as f:
        f.write('{}\n'.format(args.input))

    print('')
    exit(return_code)
