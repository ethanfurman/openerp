# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#.apidoc title: Utilities: tools.misc

"""
Miscellaneous tools used by OpenERP.
"""
from __future__ import print_function

from functools import wraps
import cProfile
import subprocess
import logging
import os
import pytz
import socket
import stonemark as sm
import sys
import threading
import time
import zipfile
from aenum import Enum, NoAlias as EnumNoAlias, Unique as EnumUnique, MultiValue as EnumMultiValue
from collections import defaultdict
from datetime import datetime, timedelta
from dbf.data_types import Date, IsoDay, RelativeDay
from itertools import islice, izip
from lxml import etree
from which import which
from threading import local

try:
    from html2text import html2text
except ImportError:
    html2text = None

from config import config
from cache import *

# get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are moved to loglevels until we refactor tools.
from openerp.loglevels import get_encodings, ustr, exception_to_unicode
# stupid pyflakes
get_encodings, ustr, exception_to_unicode, EnumNoAlias, EnumUnique, EnumMultiValue

_logger = logging.getLogger(__name__)

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (etree._Comment, etree._ProcessingInstruction, etree.CommentBase, etree.PIBase)

def find_in_path(name):
    try:
        return which(name)
    except IOError:
        return None

def find_pg_tool(name):
    path = None
    if config['pg_path'] and config['pg_path'] != 'None':
        path = config['pg_path']
    try:
        return which(name, path=path)
    except IOError:
        return None

def exec_pg_command(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    args2 = (prog,) + args

    return subprocess.call(args2)

def exec_pg_command_pipe(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    # on win32, passing close_fds=True is not compatible
    # with redirecting std[in/err/out]
    pop = subprocess.Popen((prog,) + args, bufsize= -1,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          close_fds=(os.name=="posix"))
    return pop.stdin, pop.stdout

def exec_command_pipe(name, *args):
    prog = find_in_path(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    # on win32, passing close_fds=True is not compatible
    # with redirecting std[in/err/out]
    pop = subprocess.Popen((prog,) + args, bufsize= -1,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          close_fds=(os.name=="posix"))
    return pop.stdin, pop.stdout

#----------------------------------------------------------
# python stdlib replacements
#----------------------------------------------------------

from __builtin__ import issubclass as stdlib_issubclass

def issubclass(target, allowed):
    if not isinstance(allowed, tuple):
        allowed = (allowed, )
    try:
        return stdlib_issubclass(target, allowed)
    except TypeError:
        return False


#----------------------------------------------------------
# File paths
#----------------------------------------------------------
#file_path_root = os.getcwd()
#file_path_addons = os.path.join(file_path_root, 'addons')

def file_open(name, mode="r", subdir='addons', pathinfo=False):
    """Open a file from the OpenERP root, using a subdir folder.

    Example::

    >>> file_open('hr/report/timesheer.xsl')
    >>> file_open('addons/hr/report/timesheet.xsl')
    >>> file_open('../../base/report/rml_template.xsl', subdir='addons/hr/report', pathinfo=True)

    @param name name of the file
    @param mode file open mode
    @param subdir subdirectory
    @param pathinfo if True returns tuple (fileobject, filepath)

    @return fileobject if pathinfo is False else (fileobject, filepath)
    """
    import openerp.modules as addons
    adps = addons.module.ad_paths
    rtp = os.path.normcase(os.path.abspath(config['root_path']))

    basename = name

    if os.path.isabs(name):
        # It is an absolute path
        # Is it below 'addons_path' or 'root_path'?
        name = os.path.normcase(os.path.normpath(name))
        for root in adps + [rtp]:
            root = os.path.normcase(os.path.normpath(root)) + os.sep
            if name.startswith(root):
                base = root.rstrip(os.sep)
                name = name[len(base) + 1:]
                break
        else:
            # It is outside the OpenERP root: skip zipfile lookup.
            base, name = os.path.split(name)
        return _fileopen(name, mode=mode, basedir=base, pathinfo=pathinfo, basename=basename)

    if name.replace(os.sep, '/').startswith('addons/'):
        subdir = 'addons'
        name2 = name[7:]
    elif subdir:
        name = os.path.join(subdir, name)
        if name.replace(os.sep, '/').startswith('addons/'):
            subdir = 'addons'
            name2 = name[7:]
        else:
            name2 = name

    # First, try to locate in addons_path
    if subdir:
        for adp in adps:
            try:
                return _fileopen(name2, mode=mode, basedir=adp,
                                 pathinfo=pathinfo, basename=basename)
            except IOError:
                pass

    # Second, try to locate in root_path
    return _fileopen(name, mode=mode, basedir=rtp, pathinfo=pathinfo, basename=basename)


def _fileopen(path, mode, basedir, pathinfo, basename=None):
    name = os.path.normpath(os.path.join(basedir, path))

    if basename is None:
        basename = name
    # Give higher priority to module directories, which is
    # a more common case than zipped modules.
    if os.path.isfile(name) or 'w' in mode:
        fo = open(name, mode)
        if pathinfo:
            return fo, name
        return fo

    # Support for loading modules in zipped form.
    # This will not work for zipped modules that are sitting
    # outside of known addons paths.
    head = os.path.normpath(path)
    zipname = False
    while os.sep in head:
        head, tail = os.path.split(head)
        if not tail:
            break
        if zipname:
            zipname = os.path.join(tail, zipname)
        else:
            zipname = tail
        zpath = os.path.join(basedir, head + '.zip')
        if zipfile.is_zipfile(zpath):
            from cStringIO import StringIO
            zfile = zipfile.ZipFile(zpath)
            try:
                fo = StringIO()
                fo.write(zfile.read(os.path.join(
                    os.path.basename(head), zipname).replace(
                        os.sep, '/')))
                fo.seek(0)
                if pathinfo:
                    return fo, name
                return fo
            except Exception:
                pass
    # Not found
    if name.endswith('.rml'):
        raise IOError('Report %r doesn\'t exist or deleted' % basename)
    raise IOError('File not found: %s' % basename)


#----------------------------------------------------------
# iterables
#----------------------------------------------------------
def flatten(list):
    """Flatten a list of elements into a uniqu list
    Author: Christophe Simonis (christophe@tinyerp.com)

    Examples::
    >>> flatten(['a'])
    ['a']
    >>> flatten('b')
    ['b']
    >>> flatten( [] )
    []
    >>> flatten( [[], [[]]] )
    []
    >>> flatten( [[['a','b'], 'c'], 'd', ['e', [], 'f']] )
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> t = (1,2,(3,), [4, 5, [6, [7], (8, 9), ([10, 11, (12, 13)]), [14, [], (15,)], []]])
    >>> flatten(t)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    """

    def isiterable(x):
        return hasattr(x, "__iter__")

    r = []
    for e in list:
        if isiterable(e):
            map(r.append, flatten(e))
        else:
            r.append(e)
    return r

def reverse_enumerate(l):
    """Like enumerate but in the other sens

    Usage::
    >>> a = ['a', 'b', 'c']
    >>> it = reverse_enumerate(a)
    >>> it.next()
    (2, 'c')
    >>> it.next()
    (1, 'b')
    >>> it.next()
    (0, 'a')
    >>> it.next()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    StopIteration
    """
    return izip(xrange(len(l)-1, -1, -1), reversed(l))

#----------------------------------------------------------
# SMS
#----------------------------------------------------------
# text must be latin-1 encoded
def sms_send(user, password, api_id, text, to):
    import urllib
    url = "http://api.urlsms.com/SendSMS.aspx"
    #url = "http://196.7.150.220/http/sendmsg"
    params = urllib.urlencode({'UserID': user, 'Password': password, 'SenderID': api_id, 'MsgText': text, 'RecipientMobileNo':to})
    urllib.urlopen(url+"?"+params)
    # FIXME: Use the logger if there is an error
    return True

class UpdateableStr(local):
    """ Class that stores an updateable string (used in wizards)
    """

    def __init__(self, string=''):
        self.string = string

    def __str__(self):
        return str(self.string)

    def __repr__(self):
        return str(self.string)

    def __nonzero__(self):
        return bool(self.string)


class UpdateableDict(local):
    """Stores an updateable dict to use in wizards
    """

    def __init__(self, dict=None):
        if dict is None:
            dict = {}
        self.dict = dict

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return str(self.dict)

    def clear(self):
        return self.dict.clear()

    def keys(self):
        return self.dict.keys()

    def __setitem__(self, i, y):
        self.dict.__setitem__(i, y)

    def __getitem__(self, i):
        return self.dict.__getitem__(i)

    def copy(self):
        return self.dict.copy()

    def iteritems(self):
        return self.dict.iteritems()

    def iterkeys(self):
        return self.dict.iterkeys()

    def itervalues(self):
        return self.dict.itervalues()

    def pop(self, k, d=None):
        return self.dict.pop(k, d)

    def popitem(self):
        return self.dict.popitem()

    def setdefault(self, k, d=None):
        return self.dict.setdefault(k, d)

    def update(self, E, **F):
        return self.dict.update(E, F)

    def values(self):
        return self.dict.values()

    def get(self, k, d=None):
        return self.dict.get(k, d)

    def has_key(self, k):
        return self.dict.has_key(k)

    def items(self):
        return self.dict.items()

    def __cmp__(self, y):
        return self.dict.__cmp__(y)

    def __contains__(self, k):
        return self.dict.__contains__(k)

    def __delitem__(self, y):
        return self.dict.__delitem__(y)

    def __eq__(self, y):
        return self.dict.__eq__(y)

    def __ge__(self, y):
        return self.dict.__ge__(y)

    def __gt__(self, y):
        return self.dict.__gt__(y)

    def __hash__(self):
        return self.dict.__hash__()

    def __iter__(self):
        return self.dict.__iter__()

    def __le__(self, y):
        return self.dict.__le__(y)

    def __len__(self):
        return self.dict.__len__()

    def __lt__(self, y):
        return self.dict.__lt__(y)

    def __ne__(self, y):
        return self.dict.__ne__(y)

class currency(float):
    """ Deprecate

    .. warning::

    Don't use ! Use res.currency.round()
    """

    def __init__(self, value, accuracy=2, rounding=None):
        if rounding is None:
            rounding=10**-accuracy
        self.rounding=rounding
        self.accuracy=accuracy

    def __new__(cls, value, accuracy=2, rounding=None):
        return float.__new__(cls, round(value, accuracy))

    #def __str__(self):
    #   display_value = int(self*(10**(-self.accuracy))/self.rounding)*self.rounding/(10**(-self.accuracy))
    #   return str(display_value)

def to_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def get_iso_codes(lang):
    if lang.find('_') != -1:
        if lang.split('_')[0] == lang.split('_')[1].lower():
            lang = lang.split('_')[0]
    return lang

ALL_LANGUAGES = {
        'ab_RU': u'Abkhazian / аҧсуа',
        'ar_SY': u'Arabic / الْعَرَبيّة',
        'bg_BG': u'Bulgarian / български език',
        'bs_BS': u'Bosnian / bosanski jezik',
        'ca_ES': u'Catalan / Català',
        'cs_CZ': u'Czech / Čeština',
        'da_DK': u'Danish / Dansk',
        'de_DE': u'German / Deutsch',
        'el_GR': u'Greek / Ελληνικά',
        'en_CA': u'English (CA)',
        'en_GB': u'English (UK)',
        'en_US': u'English (US)',
        'es_AR': u'Spanish (AR) / Español (AR)',
        'es_BO': u'Spanish (BO) / Español (BO)',
        'es_CL': u'Spanish (CL) / Español (CL)',
        'es_CO': u'Spanish (CO) / Español (CO)',
        'es_CR': u'Spanish (CR) / Español (CR)',
        'es_DO': u'Spanish (DO) / Español (DO)',
        'es_EC': u'Spanish (EC) / Español (EC)',
        'es_ES': u'Spanish / Español',
        'es_GT': u'Spanish (GT) / Español (GT)',
        'es_HN': u'Spanish (HN) / Español (HN)',
        'es_MX': u'Spanish (MX) / Español (MX)',
        'es_NI': u'Spanish (NI) / Español (NI)',
        'es_PA': u'Spanish (PA) / Español (PA)',
        'es_PE': u'Spanish (PE) / Español (PE)',
        'es_PR': u'Spanish (PR) / Español (PR)',
        'es_PY': u'Spanish (PY) / Español (PY)',
        'es_SV': u'Spanish (SV) / Español (SV)',
        'es_UY': u'Spanish (UY) / Español (UY)',
        'es_VE': u'Spanish (VE) / Español (VE)',
        'et_EE': u'Estonian / Eesti keel',
        'fa_IR': u'Persian / فارس',
        'fi_FI': u'Finnish / Suomi',
        'fr_BE': u'French (BE) / Français (BE)',
        'fr_CH': u'French (CH) / Français (CH)',
        'fr_FR': u'French / Français',
        'gl_ES': u'Galician / Galego',
        'gu_IN': u'Gujarati / ગુજરાતી',
        'he_IL': u'Hebrew / עִבְרִי',
        'hi_IN': u'Hindi / हिंदी',
        'hr_HR': u'Croatian / hrvatski jezik',
        'hu_HU': u'Hungarian / Magyar',
        'id_ID': u'Indonesian / Bahasa Indonesia',
        'it_IT': u'Italian / Italiano',
        'iu_CA': u'Inuktitut / ᐃᓄᒃᑎᑐᑦ',
        'ja_JP': u'Japanese / 日本語',
        'ko_KP': u'Korean (KP) / 한국어 (KP)',
        'ko_KR': u'Korean (KR) / 한국어 (KR)',
        'lt_LT': u'Lithuanian / Lietuvių kalba',
        'lv_LV': u'Latvian / latviešu valoda',
        'ml_IN': u'Malayalam / മലയാളം',
        'mn_MN': u'Mongolian / монгол',
        'nb_NO': u'Norwegian Bokmål / Norsk bokmål',
        'nl_NL': u'Dutch / Nederlands',
        'nl_BE': u'Flemish (BE) / Vlaams (BE)',
        'oc_FR': u'Occitan (FR, post 1500) / Occitan',
        'pl_PL': u'Polish / Język polski',
        'pt_BR': u'Portuguese (BR) / Português (BR)',
        'pt_PT': u'Portuguese / Português',
        'ro_RO': u'Romanian / română',
        'ru_RU': u'Russian / русский язык',
        'si_LK': u'Sinhalese / සිංහල',
        'sl_SI': u'Slovenian / slovenščina',
        'sk_SK': u'Slovak / Slovenský jazyk',
        'sq_AL': u'Albanian / Shqip',
        'sr_RS': u'Serbian (Cyrillic) / српски',
        'sr@latin': u'Serbian (Latin) / srpski',
        'sv_SE': u'Swedish / svenska',
        'te_IN': u'Telugu / తెలుగు',
        'tr_TR': u'Turkish / Türkçe',
        'vi_VN': u'Vietnamese / Tiếng Việt',
        'uk_UA': u'Ukrainian / українська',
        'ur_PK': u'Urdu / اردو',
        'zh_CN': u'Chinese (CN) / 简体中文',
        'zh_HK': u'Chinese (HK)',
        'zh_TW': u'Chinese (TW) / 正體字',
        'th_TH': u'Thai / ภาษาไทย',
        'tlh_TLH': u'Klingon',
    }

def scan_languages():
    """ Returns all languages supported by OpenERP for translation

    :returns: a list of (lang_code, lang_name) pairs
    :rtype: [(str, unicode)]
    """
    return sorted(ALL_LANGUAGES.iteritems(), key=lambda k: k[1])

def get_user_companies(cr, user):
    def _get_company_children(cr, ids):
        if not ids:
            return []
        cr.execute('SELECT id FROM res_company WHERE parent_id IN %s', (tuple(ids),))
        res = [x[0] for x in cr.fetchall()]
        res.extend(_get_company_children(cr, res))
        return res
    cr.execute('SELECT company_id FROM res_users WHERE id=%s', (user,))
    user_comp = cr.fetchone()[0]
    if not user_comp:
        return []
    return [user_comp] + _get_company_children(cr, [user_comp])

def mod10r(number):
    """
    Input number : account or invoice number
    Output return: the same number completed with the recursive mod10
    key
    """
    codec=[0,9,4,6,8,2,7,1,3,5]
    report = 0
    result=""
    for digit in number:
        result += digit
        if digit.isdigit():
            report = codec[ (int(digit) + report) % 10 ]
    return result + str((10 - report) % 10)


def human_size(sz):
    """
    Return the size in a human readable format
    """
    if not sz:
        return False
    units = ('bytes', 'Kb', 'Mb', 'Gb')
    if isinstance(sz,basestring):
        sz=len(sz)
    s, i = float(sz), 0
    while s >= 1024 and i < len(units)-1:
        s /= 1024
        i += 1
    return "%0.2f %s" % (s, units[i])

def logged(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from pprint import pformat

        vector = ['Call -> function: %r' % f]
        for i, arg in enumerate(args):
            vector.append('  arg %02d: %s' % (i, pformat(arg)))
        for key, value in kwargs.items():
            vector.append('  kwarg %10s: %s' % (key, pformat(value)))

        timeb4 = time.time()
        res = f(*args, **kwargs)

        vector.append('  result: %s' % pformat(res))
        vector.append('  time delta: %s' % (time.time() - timeb4))
        _logger.debug('\n'.join(vector))
        return res

    return wrapper

class tracker(object):
    from textwrap import wrap
    wrap = staticmethod(wrap)
    from pprint import pformat
    pformat = staticmethod(pformat)
    thread_local_storage = local()
    thread_local_storage.indent = 0
    model = False

    def __init__(self, table=None, recurse=True, compress=False):
        # table -> restrict to certain tables
        # recurse -> show recursive calls to function
        # compress -> show short arguments only (only include dicts with less than 7 entries)
        self.compress = compress
        self.recurse = recurse
        self._seen = defaultdict(int)
        if table is None:
            self.model = []
        else:
            self.model = table.split(',')

    def __call__(self, func):
        _logger.warning('self.model = %r', self.model, )
        cls = self.__class__
        def wrapper(model, cr, *args, **kwds):
            if self.model and model._name not in self.model:
                return func(model, cr, *args, **kwds)
            initialized = getattr(cls.thread_local_storage, 'indent', None)
            if initialized is None:
                cls.thread_local_storage.indent = 0
            self._seen[model] += 1
            if self.recurse or self._seen[model] == 1:
                indent = ' . ' * cls.thread_local_storage.indent
                new_args = []
                for a in args:
                    if self.compress and isinstance(a, dict) and len(a) >= 7:
                        new_args.append('{...}')
                    else:
                        new_args.append(shorten(a))
                new_kwds = shorten(kwds)
                print(
                    '\n{indent}{cls}.{func}(\n'
                    '{indent}    cr,\n'
                    '{indent}    {args},\n'
                    '{indent}    {kwds},\n'
                    '{indent}    )\n'.format(
                    indent=indent,
                    cls=model.__class__.__name__,
                    func=func.__name__,
                    model=model._name,
                    args=(',\n%s    '%indent).join([repr(a) for a in new_args]),
                    kwds=(',\n%s    '%indent).join(['%s=%r' % (k, v) for k, v in new_kwds.items()]),
                    ), file=sys.stdout)
                cls.thread_local_storage.indent += 1
            result = func(model, cr, *args, **kwds)
            if self.recurse or self._seen[model] == 1:
                if isinstance(result, list):
                    formatted_result = cls.wrap(repr(result), 100)
                    formatted_result = ('\n%*s' % (cls.thread_local_storage.indent*3, ' ')).join(formatted_result)
                else:
                    formatted_result = (
                        cls
                        .pformat(result, indent=2, depth=2 if self.compress else None, width=10240)
                        .replace('\n','\n%*s' % (cls.thread_local_storage.indent*3, ' '))
                        )
                print('\n%s<-- %s\n' % (indent, formatted_result))
                cls.thread_local_storage.indent -= 1
            self._seen[model] -= 1
            return result
        return wrapper

    @classmethod
    def log(cls, text, *args):
        indent = ' . ' * cls.thread_local_storage.indent + '> '
        if args:
            text %= args
        print(indent + text)


    # tracker = tracker()

def shorten(d):
    if not isinstance(d, (basestring, dict)):
        return d
    if isinstance(d, dict):
        new_d = {}
        for k, v in d.items():
            new_d[k] = shorten(v)
        return new_d
    if len(d) <= 64:
        return d
    else:
        return d[:7] + '...' + d[-7:]

class profile(object):
    def __init__(self, fname=None):
        self.fname = fname

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            profile = cProfile.Profile()
            result = profile.runcall(f, *args, **kwargs)
            profile.dump_stats(self.fname or ("%s.cprof" % (f.func_name,)))
            return result

        return wrapper

__icons_list = ['STOCK_ABOUT', 'STOCK_ADD', 'STOCK_APPLY', 'STOCK_BOLD',
'STOCK_CANCEL', 'STOCK_CDROM', 'STOCK_CLEAR', 'STOCK_CLOSE', 'STOCK_COLOR_PICKER',
'STOCK_CONNECT', 'STOCK_CONVERT', 'STOCK_COPY', 'STOCK_CUT', 'STOCK_DELETE',
'STOCK_DIALOG_AUTHENTICATION', 'STOCK_DIALOG_ERROR', 'STOCK_DIALOG_INFO',
'STOCK_DIALOG_QUESTION', 'STOCK_DIALOG_WARNING', 'STOCK_DIRECTORY', 'STOCK_DISCONNECT',
'STOCK_DND', 'STOCK_DND_MULTIPLE', 'STOCK_EDIT', 'STOCK_EXECUTE', 'STOCK_FILE',
'STOCK_FIND', 'STOCK_FIND_AND_REPLACE', 'STOCK_FLOPPY', 'STOCK_GOTO_BOTTOM',
'STOCK_GOTO_FIRST', 'STOCK_GOTO_LAST', 'STOCK_GOTO_TOP', 'STOCK_GO_BACK',
'STOCK_GO_DOWN', 'STOCK_GO_FORWARD', 'STOCK_GO_UP', 'STOCK_HARDDISK',
'STOCK_HELP', 'STOCK_HOME', 'STOCK_INDENT', 'STOCK_INDEX', 'STOCK_ITALIC',
'STOCK_JUMP_TO', 'STOCK_JUSTIFY_CENTER', 'STOCK_JUSTIFY_FILL',
'STOCK_JUSTIFY_LEFT', 'STOCK_JUSTIFY_RIGHT', 'STOCK_MEDIA_FORWARD',
'STOCK_MEDIA_NEXT', 'STOCK_MEDIA_PAUSE', 'STOCK_MEDIA_PLAY',
'STOCK_MEDIA_PREVIOUS', 'STOCK_MEDIA_RECORD', 'STOCK_MEDIA_REWIND',
'STOCK_MEDIA_STOP', 'STOCK_MISSING_IMAGE', 'STOCK_NETWORK', 'STOCK_NEW',
'STOCK_NO', 'STOCK_OK', 'STOCK_OPEN', 'STOCK_PASTE', 'STOCK_PREFERENCES',
'STOCK_PRINT', 'STOCK_PRINT_PREVIEW', 'STOCK_PROPERTIES', 'STOCK_QUIT',
'STOCK_REDO', 'STOCK_REFRESH', 'STOCK_REMOVE', 'STOCK_REVERT_TO_SAVED',
'STOCK_SAVE', 'STOCK_SAVE_AS', 'STOCK_SELECT_COLOR', 'STOCK_SELECT_FONT',
'STOCK_SORT_ASCENDING', 'STOCK_SORT_DESCENDING', 'STOCK_SPELL_CHECK',
'STOCK_STOP', 'STOCK_STRIKETHROUGH', 'STOCK_UNDELETE', 'STOCK_UNDERLINE',
'STOCK_UNDO', 'STOCK_UNINDENT', 'STOCK_YES', 'STOCK_ZOOM_100',
'STOCK_ZOOM_FIT', 'STOCK_ZOOM_IN', 'STOCK_ZOOM_OUT',
'terp-account', 'terp-crm', 'terp-mrp', 'terp-product', 'terp-purchase',
'terp-sale', 'terp-tools', 'terp-administration', 'terp-hr', 'terp-partner',
'terp-project', 'terp-report', 'terp-stock', 'terp-calendar', 'terp-graph',
'terp-check','terp-go-month','terp-go-year','terp-go-today','terp-document-new','terp-camera_test',
'terp-emblem-important','terp-gtk-media-pause','terp-gtk-stop','terp-gnome-cpu-frequency-applet+',
'terp-dialog-close','terp-gtk-jump-to-rtl','terp-gtk-jump-to-ltr','terp-accessories-archiver',
'terp-stock_align_left_24','terp-stock_effects-object-colorize','terp-go-home','terp-gtk-go-back-rtl',
'terp-gtk-go-back-ltr','terp-personal','terp-personal-','terp-personal+','terp-accessories-archiver-minus',
'terp-accessories-archiver+','terp-stock_symbol-selection','terp-call-start','terp-dolar',
'terp-face-plain','terp-folder-blue','terp-folder-green','terp-folder-orange','terp-folder-yellow',
'terp-gdu-smart-failing','terp-go-week','terp-gtk-select-all','terp-locked','terp-mail-forward',
'terp-mail-message-new','terp-mail-replied','terp-rating-rated','terp-stage','terp-stock_format-scientific',
'terp-dolar_ok!','terp-idea','terp-stock_format-default','terp-mail-','terp-mail_delete'
]

def icons(*a, **kw):
    global __icons_list
    return [(x, x) for x in __icons_list ]

def extract_zip_file(zip_file, outdirectory):
    zf = zipfile.ZipFile(zip_file, 'r')
    out = outdirectory
    for path in zf.namelist():
        tgt = os.path.join(out, path)
        tgtdir = os.path.dirname(tgt)
        if not os.path.exists(tgtdir):
            os.makedirs(tgtdir)

        if not tgt.endswith(os.sep):
            fp = open(tgt, 'wb')
            fp.write(zf.read(path))
            fp.close()
    zf.close()

def detect_ip_addr():
    """Try a very crude method to figure out a valid external
       IP or hostname for the current machine. Don't rely on this
       for binding to an interface, but it could be used as basis
       for constructing a remote URL to the server.
    """
    def _detect_ip_addr():
        from array import array
        from struct import pack, unpack

        try:
            import fcntl
        except ImportError:
            fcntl = None

        ip_addr = None

        if not fcntl: # not UNIX:
            host = socket.gethostname()
            ip_addr = socket.gethostbyname(host)
        else: # UNIX:
            # get all interfaces:
            nbytes = 128 * 32
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            names = array('B', '\0' * nbytes)
            #print 'names: ', names
            outbytes = unpack('iL', fcntl.ioctl( s.fileno(), 0x8912, pack('iL', nbytes, names.buffer_info()[0])))[0]
            namestr = names.tostring()

            # try 64 bit kernel:
            for i in range(0, outbytes, 40):
                name = namestr[i:i+16].split('\0', 1)[0]
                if name != 'lo':
                    ip_addr = socket.inet_ntoa(namestr[i+20:i+24])
                    break

            # try 32 bit kernel:
            if ip_addr is None:
                ifaces = filter(None, [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)])

                for ifname in [iface for iface in ifaces if iface != 'lo']:
                    ip_addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, pack('256s', ifname[:15]))[20:24])
                    break

        return ip_addr or 'localhost'

    try:
        ip_addr = _detect_ip_addr()
    except Exception:
        ip_addr = 'localhost'
    return ip_addr

# RATIONALE BEHIND TIMESTAMP CALCULATIONS AND TIMEZONE MANAGEMENT:
#  The server side never does any timestamp calculation, always
#  sends them in a naive (timezone agnostic) format supposed to be
#  expressed within the server timezone, and expects the clients to
#  provide timestamps in the server timezone as well.
#  It stores all timestamps in the database in naive format as well,
#  which also expresses the time in the server timezone.
#  For this reason the server makes its timezone name available via the
#  common/timezone_get() rpc method, which clients need to read
#  to know the appropriate time offset to use when reading/writing
#  times.
def get_win32_timezone():
    """Attempt to return the "standard name" of the current timezone on a win32 system.
       @return the standard name of the current win32 timezone, or False if it cannot be found.
    """
    res = False
    if sys.platform == "win32":
        try:
            import _winreg
            hklm = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
            current_tz_key = _winreg.OpenKey(hklm, r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation", 0,_winreg.KEY_ALL_ACCESS)
            res = str(_winreg.QueryValueEx(current_tz_key,"StandardName")[0])  # [0] is value, [1] is type code
            _winreg.CloseKey(current_tz_key)
            _winreg.CloseKey(hklm)
        except Exception:
            pass
    return res

def detect_server_timezone():
    """Attempt to detect the timezone to use on the server side.
       Defaults to UTC if no working timezone can be found.
       @return the timezone identifier as expected by pytz.timezone.
    """
    global SERVER_TIMEZONE, UTC
    try:
        import pytz
        SERVER_TIMEZONE = pytz.timezone('UTC')
        UTC = pytz.timezone('UTC')
    except Exception:
        _logger.error("Python pytz module is not available. "
            "Timezone will be set to UTC by default.")
        return 'UTC'

    # Option 1: the configuration option (did not exist before, so no backwards compatibility issue)
    # Option 2: to be backwards compatible with 5.0 or earlier, the value from time.tzname[0], but only if it is known to pytz
    #           XXX this is no longer used as the timezone is artificially set to UTC
    # Option 3: the environment variable TZ
    #           XXX ditto
    sources = [
            (config['timezone'], 'OpenERP configuration'),
            ]
    # Option 4: OS-specific: /etc/timezone on Unix
    if os.path.exists("/etc/timezone"):
        tz_value = False
        try:
            f = open("/etc/timezone")
            tz_value = f.read(128).strip()
        except Exception:
            pass
        finally:
            f.close()
        sources.append((tz_value,"/etc/timezone file"))
    # Option 5: timezone info from registry on Win32
    if sys.platform == "win32":
        # Timezone info is stored in windows registry.
        # However this is not likely to work very well as the standard name
        # of timezones in windows is rarely something that is known to pytz.
        # But that's ok, it is always possible to use a config option to set
        # it explicitly.
        sources.append((get_win32_timezone(),"Windows Registry"))

    for (value,source) in sources:
        if value:
            try:
                tz = pytz.timezone(value)
                _logger.info("Using timezone %s obtained from %s.", tz.zone, source)
                SERVER_TIMEZONE = pytz.timezone(value)
                return value
            except pytz.UnknownTimeZoneError:
                _logger.warning("The timezone specified in %s (%s) is invalid, ignoring it.", source, value)

    _logger.warning("No valid timezone could be detected, using default UTC "
        "timezone. You can specify it explicitly with option 'timezone' in "
        "the server configuration.")
    SERVER_TIMEZONE = pytz.timezone('UTC')
    return 'UTC'

detect_server_timezone()

def get_server_timezone():
    return "UTC"

def adjust_logging_timezone():
    logger_tz = pytz.timezone(config['timezone'] or detect_server_timezone())
    if logger_tz.zone != 'UTC':
        def converter(secs=None):
            UTC = pytz.timezone('UTC')
            dt = datetime(*time.localtime(secs)[:6])
            dt = UTC.localize(dt).astimezone(logger_tz)
            return dt.timetuple()
        logging.Formatter.converter = staticmethod(converter)


DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT)

# Python's strftime supports only the format directives
# that are available on the platform's libc, so in order to
# be cross-platform we map to the directives required by
# the C standard (1989 version), always available on platforms
# with a C standard implementation.
DATETIME_FORMATS_MAP = {
        '%C': '', # century
        '%D': '%m/%d/%Y', # modified %y->%Y
        '%e': '%d',
        '%E': '', # special modifier
        '%F': '%Y-%m-%d',
        '%g': '%Y', # modified %y->%Y
        '%G': '%Y',
        '%h': '%b',
        '%k': '%H',
        '%l': '%I',
        '%n': '\n',
        '%O': '', # special modifier
        '%P': '%p',
        '%R': '%H:%M',
        '%r': '%I:%M:%S %p',
        '%s': '', #num of seconds since epoch
        '%T': '%H:%M:%S',
        '%t': ' ', # tab
        '%u': ' %w',
        '%V': '%W',
        '%y': '%Y', # Even if %y works, it's ambiguous, so we should use %Y
        '%+': '%Y-%m-%d %H:%M:%S',

        # %Z is a special case that causes 2 problems at least:
        #  - the timezone names we use (in res_user.context_tz) come
        #    from pytz, but not all these names are recognized by
        #    strptime(), so we cannot convert in both directions
        #    when such a timezone is selected and %Z is in the format
        #  - %Z is replaced by an empty string in strftime() when
        #    there is not tzinfo in a datetime value (e.g when the user
        #    did not pick a context_tz). The resulting string does not
        #    parse back if the format requires %Z.
        # As a consequence, we strip it completely from format strings.
        # The user can always have a look at the context_tz in
        # preferences to check the timezone.
        '%z': '',
        '%Z': '',
}

def server_to_local_timestamp(src_tstamp_str, src_format, dst_format, dst_tz_name,
        tz_offset=True, ignore_unparsable_time=True):
    """
    Convert a source timestamp string into a destination timestamp string, attempting to apply the
    correct offset if both the server and local timezone are recognized, or no
    offset at all if they aren't or if tz_offset is false (i.e. assuming they are both in the same TZ).

    WARNING: This method is here to allow formatting dates correctly for inclusion in strings where
             the client would not be able to format/offset it correctly. DO NOT use it for returning
             date fields directly, these are supposed to be handled by the client!!

    @param src_tstamp_str: the str value containing the timestamp in the server timezone.
    @param src_format: the format to use when parsing the server timestamp.
    @param dst_format: the format to use when formatting the resulting timestamp for the local/client timezone.
    @param dst_tz_name: name of the destination timezone (such as the 'tz' value of the client context)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str cannot be parsed
                                   using src_format or formatted using dst_format.

    @return local/client formatted timestamp, expressed in the local/client timezone if possible
            and if tz_offset is true, or src_tstamp_str if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False

    res = src_tstamp_str
    if src_format and dst_format:
        # find out server timezone
        server_tz = get_server_timezone()
        try:
            # dt_value needs to be a datetime.datetime object (so no time.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.strptime(src_tstamp_str, src_format)
            if tz_offset and dst_tz_name:
                try:
                    import pytz
                    src_tz = pytz.timezone(server_tz)
                    dst_tz = pytz.timezone(dst_tz_name)
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
    return res

def all_in(desired, target):
    """
    check if all of the desired objects are in the target
    """
    for d in desired:
        if d not in target:
            return False
    return True

def any_in(desired, target):
    """
    check if any of the desired objects is in the target
    """
    for d in desired:
        if d in target:
            return True
    return False

def split_every(n, iterable, piece_maker=tuple):
    """Splits an iterable into length-n pieces. The last piece will be shorter
       if ``n`` does not evenly divide the iterable length.
       @param ``piece_maker``: function to build the pieces
       from the slices (tuple,list,...)
    """
    iterator = iter(iterable)
    piece = piece_maker(islice(iterator, n))
    while piece:
        yield piece
        piece = piece_maker(islice(iterator, n))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

class upload_data_thread(threading.Thread):
    def __init__(self, email, data, type):
        self.args = [('email',email),('type',type),('data',data)]
        super(upload_data_thread,self).__init__()
    def run(self):
        try:
            import urllib
            args = urllib.urlencode(self.args)
            fp = urllib.urlopen('http://www.openerp.com/scripts/survey.php', args)
            fp.read()
            fp.close()
        except Exception:
            pass

def upload_data(email, data, type='SURVEY'):
    a = upload_data_thread(email, data, type)
    a.start()
    return True

def get_and_group_by_field(cr, uid, obj, ids, field, context=None):
    """ Read the values of ``field´´ for the given ``ids´´ and group ids by value.

       :param string field: name of the field we want to read and group by
       :return: mapping of field values to the list of ids that have it
       :rtype: dict
    """
    res = {}
    for record in obj.read(cr, uid, ids, [field], context=context):
        key = record[field]
        res.setdefault(key[0] if isinstance(key, tuple) else key, []).append(record['id'])
    return res

def get_and_group_by_company(cr, uid, obj, ids, context=None):
    return get_and_group_by_field(cr, uid, obj, ids, field='company_id', context=context)

def stonemark2html(self, cr, uid, ids, field_name, arg, context=None):
    # for use in function fields
    res = {}.fromkeys(ids, False)
    for rec in self.browse(cr, uid, ids, context=context):
        try:
            res[rec['id']] = sm.Document(rec[arg] or '').to_html()
        except Exception:
            _logger.exception('stonemark unable to convert record %d', rec['id'])
            res[rec['id']] = '<pre>' + sm.escape(rec[arg]) + '</pre>'
    return res

# port of python 2.6's attrgetter with support for dotted notation
def resolve_attr(obj, attr):
    for name in attr.split("."):
        obj = getattr(obj, name)
    return obj

def attrgetter(*items):
    if len(items) == 1:
        attr = items[0]
        def g(obj):
            return resolve_attr(obj, attr)
    else:
        def g(obj):
            return tuple(resolve_attr(obj, attr) for attr in items)
    return g

class unquote(str):
    """A subclass of str that implements repr() without enclosing quotation marks
       or escaping, keeping the original string untouched. The name come from Lisp's unquote.
       One of the uses for this is to preserve or insert bare variable names within dicts during eval()
       of a dict's repr(). Use with care.

       Some examples (notice that there are never quotes surrounding
       the ``active_id`` name:

       >>> unquote('active_id')
       active_id
       >>> d = {'test': unquote('active_id')}
       >>> d
       {'test': active_id}
       >>> print d
       {'test': active_id}
    """
    def __repr__(self):
        return self

class UnquoteEvalContext(defaultdict):
    """Defaultdict-based evaluation context that returns
       an ``unquote`` string for any missing name used during
       the evaluation.
       Mostly useful for evaluating OpenERP domains/contexts that
       may refer to names that are unknown at the time of eval,
       so that when the context/domain is converted back to a string,
       the original names are preserved.

       **Warning**: using an ``UnquoteEvalContext`` as context for ``eval()`` or
       ``safe_eval()`` will shadow the builtins, which may cause other
       failures, depending on what is evaluated.

       Example (notice that ``section_id`` is preserved in the final
       result) :

       >>> context_str = "{'default_user_id': uid, 'default_section_id': section_id}"
       >>> eval(context_str, UnquoteEvalContext(uid=1))
       {'default_user_id': 1, 'default_section_id': section_id}

       """
    def __init__(self, *args, **kwargs):
        super(UnquoteEvalContext, self).__init__(None, *args, **kwargs)

    def __missing__(self, key):
        return unquote(key)


class mute_logger(object):
    """Temporary suppress the logging.
    Can be used as context manager or decorator.

        @mute_logger('openerp.plic.ploc')
        def do_stuff():
            blahblah()

        with mute_logger('openerp.foo.bar'):
            do_suff()

    """
    def __init__(self, *loggers):
        self.loggers = loggers

    def filter(self, record):
        return 0

    def __enter__(self):
        for logger in self.loggers:
            logging.getLogger(logger).addFilter(self)

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        for logger in self.loggers:
            logging.getLogger(logger).removeFilter(self)

    def __call__(self, func):
        @wraps(func)
        def deco(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return deco

_ph = object()
class CountingStream(object):
    """ Stream wrapper counting the number of element it has yielded. Similar
    role to ``enumerate``, but for use when the iteration process of the stream
    isn't fully under caller control (the stream can be iterated from multiple
    points including within a library)

    ``start`` allows overriding the starting index (the index before the first
    item is returned).

    On each iteration (call to :meth:`~.next`), increases its :attr:`~.index`
    by one.

    .. attribute:: index

        ``int``, index of the last yielded element in the stream. If the stream
        has ended, will give an index 1-past the stream
    """
    def __init__(self, stream, start=-1):
        self.stream = iter(stream)
        self.index = start
        self.stopped = False
    def __iter__(self):
        return self
    def next(self):
        if self.stopped: raise StopIteration()
        self.index += 1
        val = next(self.stream, _ph)
        if val is _ph:
            self.stopped = True
            raise StopIteration()
        return val

def self_ids(table, cr, uid, ids, context=None):
    return ids

def self_uid(table, cr, uid, ids, context=None):
    return uid

def get_ids(records, *fields):
    """
    field should be a list of browse records or None
    """
    if not records:
        return []
    if not isinstance(records, (tuple, list)):
        records = [records]
    new_records = []
    for field in fields:
        for rec in records:
            if not rec:
                continue
            more = getattr(rec, field)
            if not more:
                continue
            if isinstance(more, (list, tuple)):
                new_records.extend(more)
            else:
                new_records.append(more)
        records = new_records
        new_records = []
    return [r.id for r in records]

def merge_dicts(*dicts):
    """
    return a new dictionary with all keys from all dicts (recursively)
    """
    new = dicts[0].copy()
    for d in dicts[1:]:
        for k, v in d.items():
            seen = new.get(k)
            if isinstance(seen, dict) and not isinstance(v, dict):
                # dict wins
                pass
            elif isinstance(v, dict) and not isinstance(seen, dict):
                # dict still wins
                new[k] = v
            elif isinstance(seen, dict) and isinstance(v, dict):
                # merge 'em
                new[k] = merge_dicts(seen, v)
            else:
                # most recent wins
                new[k] = v
    return new

class OrderBy(unicode):
    "string for pass-through order-by statements"

from xmlrpclib import Marshaller
Marshaller.dispatch[OrderBy] = Marshaller.dump_unicode


def Singleton(cls):
    "transforms class into a Singleton object"
    return cls()

class Sentinel(object):
    "provides better help for sentinels"

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.text)

    def __str__(self):
        return '<%s>' % self.text

@Singleton
class UnInit(Sentinel):
    "a value that hasn't been assigned"

    def __init__(self):
        Sentinel.__init__(self, '???')

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__

class default(object):
    "provides ability to know when a user provides a value"

    def __init__(self, value):
        self._value = value

    def __nonzero__(self):
        return bool(self._value)
    __bool__ = __nonzero__

    def __repr__(self):
        return "<default: %r>" % (self._value, )

    def __str__(self):
        return str(self._value)

    @property
    def value(self):
        return self._value

default_dict = default(dict())
default_list = default(list())
default_tuple = default(tuple())
default_none = default(None)
default_true = default(True)
default_false = default(False)
default_uninit = default(UnInit)

class NamedLock(object):
    "create locks by argument"
    #
    def __init__(self):
        self._locks = {}
        self._own_lock = threading.Lock()
        self._cleanup = 111
    #
    def __call__(self, *args):
        with self._own_lock:
            self._cleanup -= 1
            if not self._cleanup:
                self._cleanup = 111
                for name, lock in list(self._locks.items()):
                    if not lock.locked():
                        # trim it out
                        self._locks.pop(name)
            if args in self._locks:
                lock = self._locks[args]
            else:
                lock = self._locks[args] = threading.Lock()
        return lock


class Bomb(object):
    "helper for testing thread safety"
    #
    _bombs = {}
    #
    def __init__(self, name):
        self._name = name
        if name in self._bombs:
            raise RuntimeError("BOOM!")
        self._bombs[name] = True
    #
    def release(self):
        del self._bombs[self._name]


# periods for domain searches
class Period(timedelta, Enum):
    '''
    different lengths of time
    '''
    _init_ = 'value ordinal period'
    _settings_ = EnumNoAlias
    _ignore_ = 'Period i days'
    Period = vars()
    for i in range(367):
        Period['Day%d' % i] = i, i, 'day'
    for i in range(53):
        Period['Week%d' % i] = i*7, i, 'week'
    for i, days in enumerate((31, 61, 91, 122, 152, 182, 213, 243, 273, 304, 334, 365, 396), start=1):
        Period['Month%d' % i] = days, i, 'month'
    OneDay = Period['Day1']
    OneWeek = Period['Week1']

    def __ge__(self, other):
        cls = self.__class__
        if isinstance(other, (cls, timedelta)):
            return self._value_ >= other
        elif isinstance(other, (int, long)):
            return self.days >= other
        else:
            raise NotImplementedError('cannot compare %s with %s' % (cls.__name__, other.__class__.__name__))

    def __gt__(self, other):
        cls = self.__class__
        if isinstance(other, (cls, timedelta)):
            return self._value_ > other
        elif isinstance(other, (int, long)):
            return self.days > other
        else:
            raise NotImplementedError('cannot compare %s with %s' % (cls.__name__, other.__class__.__name__))

    def __le__(self, other):
        cls = self.__class__
        if isinstance(other, (cls, timedelta)):
            return self._value_ <= other
        elif isinstance(other, (int, long)):
            return self.days <= other
        else:
            raise NotImplementedError('cannot compare %s with %s' % (cls.__name__, other.__class__.__name__))

    def __lt__(self, other):
        cls = self.__class__
        if isinstance(other, (cls, timedelta)):
            return self._value_ < other
        elif isinstance(other, (int, long)):
            return self.days < other
        else:
            raise NotImplementedError('cannot compare %s with %s' % (cls.__name__, other.__class__.__name__))

    def future_period(self, day):
        '''
        return start and stop dates of matching future period
        '''
        today = Date.strptime(day, DEFAULT_SERVER_DATE_FORMAT)
        this_day = IsoDay(today.isoweekday())
        if this_day is IsoDay.MONDAY:
            week_start = today
        else:
            week_start = today.replace(day=RelativeDay.LAST_MONDAY)
        month_start = today.replace(day=1)
        if self.period == 'day':
            start = today + self.value
            stop = start + self.OneDay.days
        elif self.period == 'week':
            start = start + self.value
            stop = week_start + self.OneWeek.days
        elif self.period == 'month':
            start = month_start.replace(delta_month=+self.ordinal)
            stop = start.replace(delta_month=+1)
        else:
            raise ValueError("forgot to update something! (period is %r)" % (self.period,))
        return start.strftime(DEFAULT_SERVER_DATE_FORMAT), stop.strftime(DEFAULT_SERVER_DATE_FORMAT)

    def past_period(self, day):
        '''
        return start and stop dates of matching past period
        '''
        today = Date.strptime(day, DEFAULT_SERVER_DATE_FORMAT)
        this_day = IsoDay(today.isoweekday())
        if this_day is IsoDay.MONDAY:
            week_start = today
        else:
            week_start = today.replace(day=RelativeDay.LAST_MONDAY)
        month_start = today.replace(day=1)
        if self.period == 'day':
            start = today - self.value
            stop = start + self.OneDay.days
        elif self.period == 'week':
            start = week_start - self.value
            stop = start + self.OneWeek.days
        elif self.period == 'month':
            start = month_start.replace(delta_month=-self.ordinal)
            stop = start.replace(delta_month=+1)
        else:
            raise ValueError("forgot to update something! (period is %r)" % (self.period,))
        return start.strftime(DEFAULT_SERVER_DATE_FORMAT), stop.strftime(DEFAULT_SERVER_DATE_FORMAT)

