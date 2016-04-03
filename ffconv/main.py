#!/usr/bin/python
__author__ = 'kako'

import argparse
import logging

from .file_processor import FileProcessor


# Init logger with basic config
logger = logging.getLogger()
logging.basicConfig(format='%(levelname)s:%(message)s')

# Init parser and add params
parser = argparse.ArgumentParser(description='Convert media files')
parser.add_argument('input', type=str,
                    help='Name of the input file to convert')
parser.add_argument('profile', type=str,
                    help='Name of the profile to use (roku, etc)')
parser.add_argument('--output', '-o', type=str,
                    help='Name of the merged output file, if not supplied original file is removed')
parser.add_argument('--debug', '-d', action='store_true',
                    help='Use debug mode, increasing verbosity and skipping clean ups')


def process():
    # Parse arguments
    args = parser.parse_args()

    # Set logger level to debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        # Process
        processor = FileProcessor(args.input, args.output, args.profile)
        processor.process()

    except Exception as e:
        # Error, exit with 1
        logger.critical(e)
        exit(1)

    else:
        # All good, exit with 0
        exit(0)
