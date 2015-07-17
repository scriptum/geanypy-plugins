#!/usr/bin/env python
#-*- coding:utf-8 -*-

import geany, os, re, glob
from gettext import gettext as _

gsc = geany.scintilla
gsc.WORDSTARTPOSITION = 2266
gsc.AUTOCSHOW = 2100
gsc.AUTOCCANCEL = 2101
gsc.AUTOCACTIVE = 2102

class AutocompleteFilePlugin(geany.Plugin):

    __plugin_name__ = _("Autocomplete file names")
    __plugin_description__ = _("Autocompletion based on existing files")
    __plugin_version__ = "0.1"
    __plugin_author__ = "Pavel Roschin <rpg89(at)post(dot)ru>"

    python_dir = None
    c_include_dir = "/usr/include:/usr/include/*/"
    cpp_include_dir = "/usr/include/c++/*:/usr/include/c++/*/*/"

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
        lang_python = False
        lang_c = False
        # print "!!!"
        if doc.file_type.name in ("C", "C++"):
            if re.match("\s*#\s*include", line):
                if doc.file_type.name == "C++":
                    dirs += self.cpp_include_dirs
                dirs += self.c_include_dirs
                lang_c = True
        elif doc.file_type.name == "Python":
            if re.match("\s*(?:import|from)", line):
                dirs.append(self.python_dir)
                lang_python = True
        starts_with_quote = line[len(line)-len(path)-1] in ['"', '<', '\'']
        if len(path) < 3 and not (starts_with_quote or lang_c or lang_python):
            return paths
        for d in dirs:
            if len(paths) > 10: break
            p = os.path.join(d, path)
            pos = len(d) + 1
            if d[-1:] == os.path.sep:
                pos -= 1
            # print d, paths
            for i in glob.iglob(p + '*'):
                # print i[pos:]
                if lang_python:
                    paths[os.path.splitext(i[pos:])[0]] = True
                elif lang_c:
                    f = i[pos:]
                    if os.path.splitext(f)[1] in ('.h', ''):
                        paths[f] = True
                else:
                    paths[i[pos:]] = True
                if len(paths) > 10: break
        return paths

    def abspath(self, path):
        """
        Complete absolute path (Linux only).
        """
        paths = {}
        if len(path) == 1: return paths # skip trivial "/"
        if path[1] == '/': return paths # // is a comment
        for i in glob.iglob(path + '*'):
            paths[i] = True
            if len(paths) > 10: break
        return paths

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

    def editor_cb(self, obj, editor, nt):
        if nt.nmhdr.code != gsc.CHAR_ADDED:
            return False
        sci = editor.scintilla
        line = self.get_current_line(sci)
        if not line: return False
        match = re.search('[^\s\'"<>()\[\],!=]+$', line)
        if not match: return False
        path = match.group(0)
        paths = self.abspath(path) if path[0] == '/' else self.relpath(path, line)
        if len(paths) == 0:
            return False
        sci.send_text_message(gsc.AUTOCSHOW, len(path), '\n'.join(paths.keys()))

    def parse_includes(self, paths):
        res = []
        for d in paths.split(':'):
            res += glob.glob(d)
        return res

    def __init__(self):
        geany.Plugin.__init__(self)
        geany.signals.connect("editor-notify", self.editor_cb)
        self.python_dir = os.path.dirname(os.__file__)
        self.c_include_dirs = self.parse_includes(self.c_include_dir)
        self.cpp_include_dirs = self.parse_includes(self.cpp_include_dir)
