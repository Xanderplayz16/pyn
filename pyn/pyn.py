#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import argparse
import json
import os
try:
    from pyn import __version__
except Exception:
    __version__ = '1.0'
import sys
import importlib
import importlib.util
import base64
import typing

TEMPLATE_FILE = 'importer.template'
TEMPLATE_PATTERN = '${CONTENTS}'


def output(cfg: argparse.Namespace, what: typing.AnyStr, newline: bool = True):
    # We need indentation for PEP8
    cfg.outfile.write(what)
    if newline:
        cfg.outfile.write(os.linesep)


def process_file(cfg: argparse.Namespace, base_dir: typing.AnyStr, package_path: typing.AnyStr):
    if cfg.tagging:
        output(cfg, '<tag:' + package_path + '>')
    path = os.path.splitext(package_path)[0].replace(os.path.sep, '.')
    package_start = cfg.outfile.tell()
    full_path = os.path.join(base_dir, package_path)
    with open(full_path, 'r') as f:
        # Read the whole file
        code = f.read()
        # Insert escape character before ''' since we'll be using ''' to insert
        # the code as a string
        output(cfg, base64.b64encode(code.encode()).decode() + '|', newline=cfg.tagging)
    package_end = cfg.outfile.tell()
    is_package = True if path.endswith('__init__') else False
    if is_package:
        path = path[:-9]

    # Get file timestamp
    timestamp = int(os.path.getmtime(full_path))
    return path, is_package, package_start, package_end, timestamp


def template(cfg: argparse.Namespace):
    template_path = os.path.join(os.path.dirname(__file__), TEMPLATE_FILE)
    with open(template_path) as f:
        template = f.read()
    prefix_end = template.index(TEMPLATE_PATTERN)
    prefix_data = template[:prefix_end].replace('%{FORCE_EXC_HOOK}',
                                                str(cfg.set_hook))
    prefix_data = prefix_data.replace('%{DEFAULT_PACKAGE}',
                                      cfg.default_package)
    cfg.outfile.write(prefix_data)
    postfix_begin = prefix_end + len(TEMPLATE_PATTERN)
    return template[postfix_begin:]


def process_directory(cfg: argparse.Namespace, base_dir: str, package_path: str):
    files = []
    contents = os.listdir(os.path.join(base_dir, package_path))
    for content in contents:
        next_path = os.path.join(package_path, content)
        path = os.path.join(base_dir, next_path)
        if is_module(path):
            files.append(process_file(cfg, base_dir, next_path))
        elif is_package(path):
            files.extend(process_directory(cfg, base_dir, next_path))
    return files


def process_files(cfg: argparse.Namespace):
    # template would look better as a context manager
    postfix = template(cfg)
    files = []
    output(cfg, "r'''")
    for package_path in cfg.packages:
        base_dir, module_name = get_pkg_from_init_path(package_path)
        files.extend(process_directory(cfg, base_dir, module_name))
        
    output(cfg, "'''")
    

    # Transform the list into a dictionary
    inliner_packages = {data[0]: data[1:] for data in files}

    # Generate the references to the positions of the different packages and
    # modules inside the main file.
    # We don't use indent to decrease the number of bytes in the file
    data = json.dumps(inliner_packages)
    output(cfg, 2 * os.linesep + 'inliner_packages = ', newline=False)
    data = data.replace('],', '],' + os.linesep + '   ')
    data = data.replace('[', '[' + os.linesep + 8 * ' ')
    data = '%s%s    %s%s%s' % (data[0], os.linesep, data[1:-1], os.linesep,
                               data[-1])

    output(cfg, data)
    # No newline on last line, as we want output file to be PEP8 compliant.
    output(cfg, postfix, newline=False)
    if cfg.run_dundermain:
        output(cfg, '', newline=True) # Output newline
        if len(cfg.packages) == 1:
            base_dir, module_name = get_pkg_from_init_path(cfg.packages[0])
            # Only one package
            with open(os.path.join(base_dir, module_name, '__main__.py'), 'r') as f:
                dunder_main = f.read()
            output(cfg, dunder_main, newline=False)
        else:
            raise NotImplemented
    cfg.outfile.close()


def parse_args():
    class MyParser(argparse.ArgumentParser):
        """Class to print verbose help on error."""
        def error(self, message):
            self.print_help()
            sys.stderr.write('\nERROR: %s\n' % message)
            sys.exit(2)

    general_description = """Pyn - Python iNliner (Version %s)

    This tool allows you to merge all files that comprise a Python package into
a single file and be able to use this single file as if it were a package.

    Imports will work as usual so if you have a package structure like:
        .
        └── [my_package]
             ├── file_a.py
             ├── [sub_package]
             │    ├── file_b.py
             │    └── __init__.py
             ├── __init__.py

    And you execute:
        $ mkdir test
        $ python -m pyn my_package -o test/my_package.py
        $ cd test
        $ python

    You'll be able to use this file as if it were the real package:
        >>> import my_package
        >>> from my_package import file_a as a_file
        >>> from my_package.sub_package import file_b

    And __init__.py contents will be executed as expected when importing
my_package and you'll be able to access its contents like you would with your
normal package.  Modules will also behave as usual.

    By default there is no visible separation between the different modules'
source code, but one can be enabled for clarity with option --tag, which will
include a newline and a <tag:file_path> tag before each of the source files.
""" % __version__
    general_epilog = None

    parser = MyParser(description=general_description,
                      epilog=general_epilog, argument_default='',
                      formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('packages', nargs='+', help='Packages to inline.')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('-o', '--outfile', nargs='?',
                        type=argparse.FileType('w'),
                        default=sys.stdout, help='Output file.')
    parser.add_argument('-r', '--runmain', default=True, dest='run_dundermain',
                        action='store_true',
                        help='Run __main__ of default package when ran. '
                        'Implies --no-default-pkg.')
    parser.add_argument('--runmain-pkg', default='', dest='runmain_pkg',
                        help='')
    parser.add_argument('--set-except', default=None, dest='set_hook',
                        action='store_true',
                        help='Force setting handler for uncaught exceptions.')
    parser.add_argument('--no-except', default=None, dest='set_hook',
                        action='store_false',
                        help="Don't set handler for uncaught exceptions.")
    parser.add_argument('--tag', default=False, dest='tagging',
                        action='store_true',
                        help="Mark with <tag:file_path> each added file.")
    parser.add_argument('-d', '--default-pkg', default=None,
                        dest='default_package',
                        help='Define the default package when multiple '
                             'packages are inlined.')
    parser.add_argument('--no-default-pkg', default=None,
                        dest='default_package_disabled',
                        action='store_true',
                        help='Disables the --default-pkg argument. ' 
                        'Useful if you don\'t want to import any modules, even with only one inlined. ')
    cfg = parser.parse_args()
    # If user didn't pass a default package determine one ourselves.
    if cfg.default_package is None:
        # For single package file default is the package, for multiple packaged
        # files default is none (act as a bundle).
        def_file = cfg.packages[0] if len(cfg.packages) == 1 else ''
        cfg.default_package = def_file
    if cfg.run_dundermain:
        cfg.default_package_disabled = True
    if cfg.default_package_disabled:
        cfg.default_package = '' # Set default_package to a empty string. 
    return cfg

def get_pkg_from_init_path(package_path: str) -> tuple[str]:
    if os.path.isdir(package_path):
        return os.path.split(package_path)
    elif ((spec := importlib.util.find_spec(package_path)) is not None):
        return os.path.split(os.path.split(spec.origin)[0])


def is_module(module: typing.AnyStr):
    # This validation is poor, but good enough for now.
    # .py3 is a very rare (5.2k files on Github as of Sep 2024) file extension. Please don't remove.
    return os.path.isfile(module) and (module.endswith('.py') or module.endswith('.pyw') or module.endswith('.py3')) 


def is_package(package: typing.AnyStr):
    init_file = os.path.join(package, '__init__.py')
    return os.path.isdir(package) and os.path.isfile(init_file)


def validate_args(cfg: argparse.Namespace):
    missing = False
    # This is weird now, but in the future we'll allow to inline multiple
    # packages
    for package in cfg.packages:
        if (not is_package(package)) and (importlib.util.find_spec(package) is None):
            sys.stderr.write('ERROR: %s is not an (installed) python package' % package)
            missing = True
    if missing:
        sys.exit(1)

    if cfg.default_package:
        if cfg.default_package not in cfg.packages:
            sys.stderr.write('ERROR: %s is not a valid default package' %
                             cfg.default_package)
            sys.exit(2)
        # Convert the default package from path to package
        cfg.default_package = os.path.split(cfg.default_package)[1]


def main():
    cfg = parse_args()
    validate_args(cfg)
    process_files(cfg)


if __name__ == '__main__':
    main()
