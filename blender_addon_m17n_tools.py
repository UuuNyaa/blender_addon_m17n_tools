# -*- coding: utf-8 -*-
# Copyright 2021 UuuNyaa <UuuNyaa@gmail.com>
# This file is part of blender_addon_m17n_tools.

# blender_addon_m17n_tools is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# blender_addon_m17n_tools is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import argparse
import importlib.machinery
import importlib.util
import io
import os
import sys
import tokenize
from dataclasses import dataclass
from types import ModuleType
from typing import Dict, List, Set, Tuple, Union

PACKAGE_PATH = os.path.dirname(__file__)


@dataclass
class PoEntry:
    message: str
    comment: str


Translations = Dict[str, Dict[str, Dict[str, str]]]


def main(args: Union[List[str], None] = None):
    parser = argparse.ArgumentParser()
    subpersers = parser.add_subparsers(dest='subcommand')
    parser_generate = subpersers.add_parser('generate', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_generate.add_argument('-o', '--output_python_file_path', type=str, help='path of the output file')
    parser_generate.add_argument('-k', '--keywords', type=str, default='_', help='space-separated list of keywords to look for in addition to the defaults (may be repeated multiple times)')
    parser_generate.add_argument('--default_locale', type=str, default='en_US', help='default locale')
    parser_generate.add_argument('--default_context', type=str, default='*', help='default context')
    parser_generate.add_argument('--no_output_utilities', const=True, default=False, action='store_const', help='do not output utility functions')
    parser_generate.add_argument('input_python_file_paths', type=str, nargs='+', help='input python file paths (allow files as well as directories)')

    parser_analyze = subpersers.add_parser('analyze', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_analyze.add_argument('input_python_file_paths', type=str, nargs='+', help='input python file paths (allow files as well as directories)')
    parser_analyze.add_argument('-k', '--keywords', type=str, default='_', help='space-separated list of keywords to look for in addition to the defaults (may be repeated multiple times)')

    options = parser.parse_args(sys.argv[1:] if args is None else args)

    if options.subcommand == 'generate':
        generate(
            options.input_python_file_paths,
            options.output_python_file_path,
            options.keywords,
            options.default_locale,
            options.default_context,
            options.no_output_utilities,
        )
    elif options.subcommand == 'analyze':
        analyze(
            options.input_python_file_paths,
            options.keywords,
        )
    else:
        parser.print_help()


def generate(input_python_file_paths: List[str], output_python_file_path: str, keywords: str, default_locale: str, default_context: str, no_output_utilities: bool):
    msgid_poentry = parse_potext(get_potext(input_python_file_paths, keywords))
    locale_msgid_context_msgstr = read_translations(output_python_file_path, default_locale)

    generated_lines: List[str] = []

    append_header(generated_lines, no_output_utilities)
    append_translation_dict(generated_lines, msgid_poentry, locale_msgid_context_msgstr, default_context, default_locale)
    append_footer(generated_lines)

    with open(output_python_file_path, 'w') if output_python_file_path else sys.stdout as output_file:
        for line in generated_lines:
            output_file.write(line)
            output_file.write('\n')


def analyze(input_python_file_paths: List[str], keywords: str):
    print('parse files...', end='', file=sys.stderr)
    msgid_poentry = parse_potext(get_potext(input_python_file_paths, keywords))
    print('done', file=sys.stderr)

    msgids = list(msgid_poentry.keys())
    msgid_count = len(msgids)
    calculate_count = int((msgid_count * (msgid_count-1))/2)
    print(f'Number of distinct messages: {msgid_count}', file=sys.stderr)

    count = 0
    # python3 ../blender_addon_m17n_tools/blender_addon_m17n_tools.py analyze   13.67s user 0.02s system 89% cpu 15.275 total
    edit_distances: Dict[Tuple[int, int], int] = {}
    for left_index in range(1, msgid_count):
        for right_index in range(left_index):
            edit_distances[(left_index, right_index)] = edit_distance(msgids[left_index], msgids[right_index])
            count += 1
        print(f'\rcalculate edit distances... {count}/{calculate_count}', end='', file=sys.stderr)
    print(' done', file=sys.stderr)

    for (left_index, right_index), distance in sorted(edit_distances.items(), key=lambda e: e[1]):
        if distance > 15:
            break
        left = msgids[left_index]
        right = msgids[right_index]
        print(f'distance: {distance}')
        print('\t')
        print(msgid_poentry[left].comment)
        print(left)
        print('\t')
        print(msgid_poentry[right].comment)
        print(right)
        print('-----')



def min_distance(s1: str, s2: str, n: int, m: int, dp: List[List[int]]) -> int:
    """see: https://www.geeksforgeeks.org/edit-distance-dp-5/"""
    # pylint: disable=invalid-name

    # If any string is empty,
    # return the remaining characters of other string
    if n == 0:
        return m

    if m == 0:
        return n

    # To check if the recursive tree
    # for given n & m has already been executed
    if dp[n][m] != -1:
        return dp[n][m]

    # If characters are equal, execute
    # recursive function for n-1, m-1
    if s1[n - 1] == s2[m - 1]:
        if dp[n - 1][m - 1] == -1:
            dp[n][m] = min_distance(s1, s2, n - 1, m - 1, dp)
            return dp[n][m]
        dp[n][m] = dp[n - 1][m - 1]
        return dp[n][m]

    # If characters are nt equal, we need to
    # find the minimum cost out of all 3 operations.
    if dp[n - 1][m] != -1:
        m1 = dp[n - 1][m]
    else:
        m1 = min_distance(s1, s2, n - 1, m, dp)

    if dp[n][m - 1] != -1:
        m2 = dp[n][m - 1]
    else:
        m2 = min_distance(s1, s2, n, m - 1, dp)

    if dp[n - 1][m - 1] != -1:
        m3 = dp[n - 1][m - 1]
    else:
        m3 = min_distance(s1, s2, n - 1, m - 1, dp)

    dp[n][m] = 1 + min(m1, min(m2, m3))
    return dp[n][m]

def edit_distance(s1: str, s2: str) -> int:
    # pylint: disable=invalid-name

    n = len(s1)
    m = len(s2)
    dp = [[-1 for i in range(m + 1)] for j in range(n + 1)]
    return min_distance(s1, s2, n, m, dp)


def append_translation_dict(output: List[str], msgid_poentry: Dict[str, PoEntry], locale_msgid_context_msgstr: Translations, context: str, default_locale: str):
    output.append('translation_dict = {')
    for locale, msgid_context_msgstr in locale_msgid_context_msgstr.items():
        for msgid, poentry in msgid_poentry.items():
            context_msgstr = msgid_context_msgstr.setdefault(msgid, {})

            if len(context_msgstr) == 1:
                target_context = list(context_msgstr.keys())[0]
            else:
                target_context = context

            if not context_msgstr.get(target_context):
                context_msgstr[target_context] = poentry.message

        output.append(f'  "{locale}": {{')
        for msgid, poentry in msgid_poentry.items():
            output.append(f'    {poentry.comment}')
            for context, msgstr in msgid_context_msgstr[msgid].items():
                output.append(f'    ("{context}", "{msgid}"): "{msgstr if locale != default_locale else msgid}",')

        for msgid in msgid_context_msgstr.keys() - msgid_poentry.keys():
            output.append('    #: MISSING')
            for context, msgstr in msgid_context_msgstr[msgid].items():
                output.append(f'    ("{context}", "{msgid}"): "{msgstr if locale != default_locale else msgid}",')

        output.append('  },')
    output.append('}')


def append_header(output: List[str], no_output_utilities: bool):
    output.append('''# -*- coding: utf-8 -*-
# This file can be automatically generated by blender_addon_m17n_tools.
# See: https://github.com/UuuNyaa/blender_addon_m17n_tools
# It can (should) also be put in a different, specific py file.
''')

    if not no_output_utilities:
        output.append('''import bpy

def _(msgid: str) -> str:
  return msgid

def register():
  bpy.app.translations.register(__name__, translation_dict)

def unregister():
  bpy.app.translations.unregister(__name__)
''')

    output.append('''# ##### BEGIN AUTOGENERATED I18N SECTION #####
# NOTE: You can safely move around this auto-generated block (with the begin/end markers!),
#       and edit the translations by hand.
#       Just carefully respect the format of the tuple!
''')


def append_footer(output: List[str]):
    output.append('# ##### END AUTOGENERATED I18N SECTION #####')


def parse_potext(potext: str) -> Dict[str, PoEntry]:
    msgid_poentry: Dict[str, PoEntry] = {}
    msgid: str = ''
    comment: str = ''
    for line in potext.splitlines():
        if line.startswith('#: '):
            comment = line
        elif line.startswith('msgid "'):
            msgid = line[len('msgid "'):-1]
        elif line.startswith('msgstr "'):
            msgstr = line[len('msgstr "'):-1]
            if msgid == '' and msgstr == '':
                continue
            msgid_poentry[msgid] = PoEntry(msgstr, comment)
    return msgid_poentry


def read_translations(python_file_name: str, default_locale: str) -> Translations:
    BpyMessageKey = Tuple[str, str]
    BpyTranslations = Dict[BpyMessageKey, str]
    BpyTranslationDict = Dict[str, BpyTranslations]

    translation_dict: BpyTranslationDict = {default_locale: {}}

    if python_file_name and os.path.isfile(python_file_name):
        def read_translation_dict(python_file_name: str) -> BpyTranslationDict:
            with open(python_file_name, 'r') as file:
                scope = {}
                exec(file.read(), globals(), scope)  # pylint: disable=exec-used
                return scope['translation_dict']

        translation_dict = read_translation_dict(python_file_name)

    locale_msgid_context_msgstr: Translations = {}
    for locale, translations in translation_dict.items():
        msgid_context_msgstr = locale_msgid_context_msgstr.setdefault(locale, {})
        for (context, msgid), msgstr in translations.items():
            context_msgstr = msgid_context_msgstr.setdefault(msgid, {})
            context_msgstr[context] = msgstr

    return locale_msgid_context_msgstr


def get_potext(input_python_file_paths: List[str], keywords: str):
    def new_token_eater(keywords):
        class TokenEaterOptions:
            # constants
            GNU = 1
            SOLARIS = 2
            # defaults
            extractall = 0
            escape = 0
            keywords = []
            outpath = ''
            outfile = 'messages.pot'
            writelocations = 1
            locationstyle = GNU
            verbose = 0
            width = sys.maxsize
            excludefilename = ''
            docstrings = 0
            nodocstrings = {}
            toexclude = []

        token_eater_options = TokenEaterOptions()
        token_eater_options.keywords.extend(keywords.split(' '))

        def load_pygettext() -> ModuleType:
            loader = importlib.machinery.SourceFileLoader('pygettext', os.path.join(PACKAGE_PATH, 'externals', 'pygettext', 'pygettext.py'))
            pygettext = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
            loader.exec_module(pygettext)
            return pygettext

        pygettext = load_pygettext()
        pygettext.make_escapes(not token_eater_options.escape)
        token_eater = pygettext.TokenEater(token_eater_options)
        return token_eater

    def feed(token_eater, file_path):
        with open(file_path, mode='rt') as file:
            try:
                token_eater.set_filename(file.name)
                tokens = tokenize._tokenize(file.readline, encoding=None)  # pylint: disable=protected-access
                for _token in tokens:
                    token_eater(*_token)
            except tokenize.TokenError as ex:
                print(f'{ex.args[0]}: {file.name}, line {ex.args[1][0]}, column {ex.args[1][1]}', file=sys.stderr)

    token_eater = new_token_eater(keywords)
    for python_file_path in input_python_file_paths:
        if os.path.isfile(python_file_path):
            feed(token_eater, python_file_path)
            continue

        for root, _, files in os.walk(python_file_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                feed(token_eater, os.path.join(root, file))

    with io.StringIO() as po_text_io:
        token_eater.write(po_text_io)
        po_text = po_text_io.getvalue()

    return po_text


if __name__ == '__main__':
    main()
