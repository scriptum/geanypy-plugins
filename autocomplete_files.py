#!/usr/bin/env python
#-*- coding:utf-8 -*-

import geany
from glob import iglob, glob
import os
import re

from gettext import gettext as _

gsc = geany.scintilla
gsc.WORDSTARTPOSITION = 2266
gsc.AUTOCSHOW = 2100
gsc.AUTOCCANCEL = 2101
gsc.AUTOCACTIVE = 2102

def simple_callback(f):
    return f

def cpp_callback(f):
    return f if os.path.splitext(f)[1] in ('.h', '') else None

# TODO: cross-platform?
INCLUDE="/usr/include"

class AutocompleteFilePlugin(geany.Plugin):

    __plugin_name__ = _("Autocomplete file names")
    __plugin_description__ = _("Autocompletion based on existing files")
    __plugin_version__ = "0.1"
    __plugin_author__ = "Pavel Roschin <rpg89(at)post(dot)ru>"

    word_regexp = re.compile("[^\s'\"<>()\[\],!=*]+$")
    completions_limit = 30

    lang_rules = {
        "C": {
            "dir": INCLUDE+":"+INCLUDE+"/*/",
            "regexp": "\s*#\s*include",
            "callback": cpp_callback
        },
        "C++": {
            "dir": INCLUDE+":"+INCLUDE+"/*/:"+INCLUDE+"/c++/*:"+INCLUDE+"/c++/*/*/",
            "regexp": "\s*#\s*include",
            "callback": cpp_callback
        },
        "Spec": {
            "dir": "../SOURCES",
            "regexp": "\s*(?:Source|Patch)"
        },
        "Python": {
            "dir": os.path.dirname(os.__file__),
            "regexp": "\s*(?:import|from) ",
            "callback": lambda f: os.path.splitext(f)[0]
        }
    }

    def relpath(self, path, line):
        """
        Complete relative path. It also completes include for C/C++ and import
        for python.
        """
        paths = {}
        doc = geany.document.get_current()
        docpath = doc.real_path
        if not docpath:
            docdir = "."
        else:
            docdir = os.path.dirname(docpath)
        dirs = [docdir]
        lang = False
        callback = simple_callback
        # rules based on languages and regexps
        if doc.file_type.name in self.lang_rules:
            el = self.lang_rules[doc.file_type.name]
            if el["regexp"].search(line):
                for d in el["dirs"]:
                    if os.path.isabs(d):
                        dirs.append(d)
                    else:
                        dirs.append(os.path.join(docdir, d))
                if "callback" in el:
                    callback = el["callback"]
                lang = True
        starts_with_quote = line[len(line)-len(path)-1] in ['"', '<', '\'']
        if len(path) < 3 and not lang:
            return
        for d in dirs:
            p = os.path.join(d, path)
            pos = len(d) + 1
            if d[-1:] == os.path.sep:
                pos -= 1
            for i in iglob(p + '*'):
                f = callback(i[pos:])
                if f:
                    yield f

    def abspath(self, path):
        """
        Complete absolute path (Linux only).
        """
        if len(path) == 1: return # skip trivial "/"
        if path[1] == '/': return # // is a comment
        return iglob(path + '*')

    def get_current_line(self, sci):
        """
        Get current line (string). If position is more than 100, return None.
        """
        start = sci.get_position_from_line(sci.get_current_line())
        end = sci.get_current_position()
        col = sci.get_col_from_position(end)
        if start == end or col > 100:
            return None
        return sci.get_contents_range(start, end)

    def editor_cb(self, obj, editor, notification):
        """
        Callback for every character added to editor
        """
        if notification.nmhdr.code != gsc.CHAR_ADDED:
            return False
        sci = editor.scintilla
        line = self.get_current_line(sci)
        if not line: return False
        match = self.word_regexp.search(line)
        if not match: return False
        path = match.group(0)
        it = self.abspath(path) if path[0] == '/' else self.relpath(path, line)
        paths = {}
        for i in it:
            paths[i] = True
            if len(paths) > self.completions_limit: break
        if len(paths) == 0: return False
        sci.send_text_message(gsc.AUTOCSHOW, len(path), '\n'.join(paths.keys()))

    def __init__(self):
        geany.Plugin.__init__(self)
        geany.signals.connect("editor-notify", self.editor_cb)
        for lang in self.lang_rules:
            el = self.lang_rules[lang]
            el["dirs"] = []
            for d in el["dir"].split(':'):
                el["dirs"] += glob(d)
            el["regexp"] = re.compile(el["regexp"])
