#!/usr/bin/env python

import sys
import os
import os.path
import logging

from webfont_generator.util import remove_suffix
from webfont_generator.error import Error
from webfont_generator.operations import FontFile
from webfont_generator.dependencies import FORMATS_SET, convert_files
from webfont_generator.css import generate_css

VERSION = '1.3.0-dev'

def usage(out):
    out.write('''\
Usage: generate-webfonts [options] <input-file> ...

  Convert font files to web-friendly font formats.

Arguments:
  <input-file> ...
                At least one input font file. Recognized formats are:
                  ttf, woff, woff2, eot, svg, otf
                Given this list of input files, the converter will attempt to
                satisfy the output format requirements by copying matching
                input files and converting files to fill in the gaps.

Options:
  -o --output <dir>
                Destination directory for converted files. Even if only inline
                fonts are generated, a destination directory is needed to hold
                intermediate files.
  -f --format <formats>
                Comma-separated list of output formats.
                Possible formats are:
                  ttf, woff, woff2, eot, svg, otf
                Any format suffixed with `:inline` will cause the font to be
                inlined in the CSS file as a base64-encoded data URL, rather
                than a URL to a file.
                The default format list is: eot,woff2,woff,ttf,svg
  -c --css <file>
                Name of generated CSS file. Use `-` for stdout. Omit to
                generate no CSS.
  -p --prefix <prefix>
                Prefix of file paths in the generated CSS. Default is the name
                of the output directory.
  --font-family <name>
                Name of the font family used in the CSS file. Default is the
                base name of the first input file.
  --verbose     Show verbose output while running.
  --version     Display version.
  -h --help     Show this help message.
''')

def main():
    # Parse command line arguments
    input_file_names = []
    output_formats_str = None
    output_dir = None
    css_file_name = None
    prefix_str = None
    font_family = None
    be_verbose = False
    args = sys.argv[:0:-1]
    while args:
        arg = args.pop()
        if arg == '-o' or arg == '--output':
            output_dir = args.pop()
        elif arg == '-f' or arg == '--format':
            output_formats_str = args.pop()
        elif arg == '-c' or arg == '--css':
            css_file_name = args.pop()
        elif arg == '-p' or arg == '--prefix':
            prefix_str = args.pop()
        elif arg == '--font-family' or arg == '--family':
            font_family = args.pop()
        elif arg == '--verbose':
            be_verbose = True
        elif arg == '-v' or arg == '--version':
            sys.stdout.write(VERSION + '\n')
            sys.exit(0)
        elif arg == '-h' or arg == '--help':
            usage(sys.stdout)
            sys.exit(0)
        elif arg == '--':
            input_file_names.extend(reversed(args))
            break
        else:
            input_file_names.append(arg)
    # Require the presence of input files and an output directory
    if not input_file_names or output_dir is None:
        usage(sys.stderr)
        sys.exit(1)
    # Deduce the formats of the input files
    input_files = []
    for input_file_name in input_file_names:
        name, ext = os.path.splitext(input_file_name)
        ext = ext[1:]
        if ext not in FORMATS_SET:
            if ext:
                print('Unrecognized input format: %r\n' % ext, file=sys.stderr)
            else:
                print('Cannot determine format of %r\n' % input_file_name, file=sys.stderr)
            usage(sys.stderr)
            sys.exit(1)
        input_files.append(FontFile(input_file_name, name, ext))
    # Parse output formats, or use defaults if not specified
    if output_formats_str is None:
        output_formats = ['eot', 'woff2', 'woff', 'ttf', 'svg']
        parsed_output_formats = [(f, False) for f in output_formats]
    else:
        output_formats = output_formats_str.split(',')
        # Check if any formats are suffixed with `:inline`
        parsed_output_formats = list(map(
            lambda f: remove_suffix(f, ':inline'), output_formats))
        # Check for unrecognized formats
        unrecognized_formats = set(f for f, inline in parsed_output_formats) - FORMATS_SET
        if unrecognized_formats:
            print('Unrecognized output formats: %s\n' % ', '.join(unrecognized_formats), file=sys.stderr)
            usage(sys.stderr)
            sys.exit(1)
    # Check if CSS will be generated
    do_generate_css = css_file_name is not None
    if do_generate_css:
        # If no prefix is specified, use a default
        if prefix_str is None:
            output_dir_parts = output_dir.split(os.sep)
            if not output_dir_parts[-1]:
                output_dir_parts.pop()
            if output_dir_parts:
                output_dir_parts.append('')
            prefix_str = '/'.join(output_dir_parts)
        # If no font family name is specified, use a default
        if font_family is None:
            font_family = os.path.splitext(os.path.basename(input_file_names[0]))[0]
    # Configure the logger for verbosity
    logger = logging.getLogger('webfont-generator')
    logger.addHandler(logging.StreamHandler())
    if be_verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    # Generate files for all requested output formats, even the inline
    # ones, since inlining requires the contents of the output files
    # anyway
    output_formats = set(f for f, inline in parsed_output_formats)
    try:
        output_files = convert_files(input_files, output_dir, output_formats, logger)
        if do_generate_css:
            if css_file_name == '-':
                css_fout = sys.stdout
            else:
                css_fout = open(css_file_name, 'w')
            with css_fout:
                generate_css(css_fout, parsed_output_formats, output_files,
                    prefix_str, font_family)
    except Error as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
