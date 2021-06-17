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
import traceback
from dataclasses import dataclass
from types import ModuleType
from typing import Dict, List, Tuple

PACKAGE_PATH = os.path.dirname(__file__)


def load_pygettext() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader('pygettext', os.path.join(PACKAGE_PATH, 'externals', 'pygettext', 'pygettext.py'))
    pygettext = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(pygettext)
    return pygettext


class TokenEaterOptions:
    # constants
    GNU = 1
    SOLARIS = 2
    # defaults
    extractall = 0  # FIXME: currently this option has no effect at all.
    escape = 0
    keywords = ['_', 'bl_label_']
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


def main(args: List[str] = []):
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keywords', type=str, default='', help='space-separated list of keywords to look for in addition to the defaults (may be repeated multiple times)')
    parser.add_argument('--no_default_keywords', const=True, default=False, action='store_const', help='do not include the default keywords')
    parser.add_argument('-o', '--output_file', type=str, help='name of the output file')
    parser.add_argument('-c', '--context', type=str, default='*', help='space-separated list of "keyword=context" to look for in addition to the defaults (may be repeated multiple times)')
    parser.add_argument('--no_output_utilities', const=True, default=False, action='store_const', help='do not output utility functions')
    parser.add_argument('--default_locale', type=str, default='en_US', help='default locale')
    parser.add_argument('input_paths', type=str, nargs='+', help='name of the input paths (allow files as well as directories)')

    options = parser.parse_args(sys.argv[1:] if len(args) == 0 else args)

    token_eater_options = TokenEaterOptions()
    if options.no_default_keywords:
        token_eater_options.keywords = []

    token_eater_options.keywords.extend(options.keywords.split(' '))

    pygettext = load_pygettext()
    pygettext.make_escapes(not token_eater_options.escape)
    token_eater = pygettext.TokenEater(token_eater_options)

    def eat(file):
        try:
            with open(file, mode='rt') as fp:
                try:
                    token_eater.set_filename(fp.name)
                    tokens = tokenize._tokenize(fp.readline, encoding=None)
                    for _token in tokens:
                        token_eater(*_token)
                except tokenize.TokenError as e:
                    print(f'{e.args[0]}: {fp.name}, line {e.args[1][0]}, column {e.args[1][1]}', file=sys.stderr)
        except Exception as e:
            traceback.print_exc()

    for input_path in options.input_paths:
        if os.path.isfile(input_path):
            eat(input_path)
            continue

        for root, _, files in os.walk(input_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                eat(os.path.join(root, file))

    with io.StringIO() as po_text_io:
        token_eater.write(po_text_io)
        po_text = po_text_io.getvalue()

    translation_dict: Dict[str, Dict[Tuple[str, str], str]] = {options.default_locale: {}}
    if options.output_file and os.path.isfile(options.output_file):
        with open(options.output_file, 'r') as file:
            scope = {}
            exec(file.read(), globals(), scope)
            translation_dict = scope['translation_dict']

    locale_msgid_context_msgstr: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {}
    for locale, translations in translation_dict.items():
        msgid_context_msgstr = locale_msgid_context_msgstr.setdefault(locale, {})
        for (context, msgid), msgstr in translations.items():
            context_msgstr = msgid_context_msgstr.setdefault(msgid, {})
            context_msgstr[context] = msgstr

    comment: str = ''
    context: str = options.context

    @dataclass
    class PoEntry:
        message: str
        comment: str

    msgid_poentry: Dict[str, PoEntry] = {}
    for line in po_text.splitlines():
        if line.startswith('#: '):
            comment = line
        elif line.startswith('msgid "'):
            msgid = line[len('msgid "'):-1]
        elif line.startswith('msgstr "'):
            msgstr = line[len('msgstr "'):-1]
            if msgid == '' and msgstr == '':
                continue
            msgid_poentry[msgid] = PoEntry(msgstr, comment)

    generated_lines: List(str) = []

    generated_lines.append('''# -*- coding: utf-8 -*-
# This file can be automatically generated by blender_addon_m17n_tools.
# See: https://github.com/UuuNyaa/blender_addon_m17n_tools
# It can (should) also be put in a different, specific py file.
''')

    if not options.no_output_utilities:
        generated_lines.append('''import bpy

def _(msgid: str) -> str:
  return msgid

def register():
  bpy.app.translations.register(__name__, translation_dict)

def unregister():
  bpy.app.translations.unregister(__name__)
''')

    generated_lines.append('''# ##### BEGIN AUTOGENERATED I18N SECTION #####
# NOTE: You can safely move around this auto-generated block (with the begin/end markers!),
#       and edit the translations by hand.
#       Just carefully respect the format of the tuple!
''')

    generated_lines.append('translation_dict = {')

    for locale, msgid_context_msgstr in locale_msgid_context_msgstr.items():
        for msgid, poentry in msgid_poentry.items():
            context_msgstr = msgid_context_msgstr.setdefault(msgid, {})

            if len(context_msgstr) == 1:
                target_context = list(context_msgstr.keys())[0]
            else:
                target_context = context

            if not context_msgstr.get(target_context):
                context_msgstr[target_context] = poentry.message

        generated_lines.append(f'  "{locale}": {{')
        for msgid, poentry in msgid_poentry.items():
            generated_lines.append(f'    {poentry.comment}')
            for context, msgstr in msgid_context_msgstr[msgid].items():
                generated_lines.append(f'    ("{context}", "{msgid}"): "{msgstr if locale != options.default_locale else msgid}",')

        for msgid in msgid_context_msgstr.keys() - msgid_poentry.keys():
            generated_lines.append('    #: MISSING')
            for context, msgstr in msgid_context_msgstr[msgid].items():
                generated_lines.append(f'    ("{context}", "{msgid}"): "{msgstr if locale != options.default_locale else msgid}",')

        generated_lines.append('  },')

    generated_lines.append('}')
    generated_lines.append('# ##### END AUTOGENERATED I18N SECTION #####')

    with open(options.output_file, 'w') if options.output_file else sys.stdout as output_file:
        for line in generated_lines:
            output_file.write(line)
            output_file.write('\n')


if __name__ == '__main__':
    main()
