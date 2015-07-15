#!/usr/bin/python
__author__ = 'kako'

import argparse

from process import FileProcessor


parser = argparse.ArgumentParser(description='Convert media files')

parser.add_argument('input', type=str, help='Name of the input file to convert')
parser.add_argument('profile', type=str, help='Name of the profile to use (roku, etc)')
parser.add_argument('--output', type=str, help='Name of the merged output file, if '
                                               'not supplied original file is removed')

args = parser.parse_args()


if __name__ == '__main__':
    processor = FileProcessor(args.input, args.output, args.profile)
    result = processor.process()
    print('Done. Processed {streams} streams into {output}'.format(**result))

