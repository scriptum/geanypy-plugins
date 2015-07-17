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
	c_include_dir = "/usr/include"
	def editor_cb(self, obj, editor, nt):
		if nt.nmhdr.code != gsc.CHAR_ADDED:
			return False
		sci = editor.scintilla
		ssm = sci.send_message
		line = sci.get_current_line()
		start = sci.get_position_from_line(line)
		end = sci.get_current_position()
		col = sci.get_col_from_position(end)
		if start == end or col > 100:
			return False
		text = sci.get_contents_range(start, end)
		match = re.search('[^\s\'"<>()\[\]]+$', text)
		if not match:
			return False
		path = match.group(0)
		paths = {}
		if path[0] == '/':
			for i in glob.iglob(path + '*'):
				paths[i] = True
				if len(paths) > 10: break
		else:
			#try to search paths from current document directory
			starts_with_quote = text[len(text)-len(path)-1] in ['"', '<', '\'']
			if len(path) < 3 and not starts_with_quote:
				return False
			doc = geany.document.get_current()
			docpath = doc.real_path
			if not docpath:
				docdir = "."
			else:
				docdir = os.path.dirname(docpath)
			dirs = [docdir]
			lang_python = False
			lang_c = False
			if doc.file_type.name in ("C", "C++"):
				if re.match("\s*#\s*include", text):
					if doc.file_type.name == "C++":
						dirs += glob.glob('/usr/include/c++/*')
					dirs.append(self.c_include_dir)
					lang_c = True
			elif doc.file_type.name == "Python":
				if re.match("\s*(?:import|from)", text):
					dirs.append(self.python_dir)
					lang_python = True
			for d in dirs:
				if len(paths) > 10: break
				p = os.path.join(d, path)
				pos = len(d) + 1
				for i in glob.iglob(p + '*'):
					if lang_python and d == self.python_dir:
						paths[os.path.splitext(i[pos:])[0]] = True
					if lang_c and d == self.c_include_dir:
						if i[-2:] == ".h":
							paths[i[pos:]] = True
					else:
						paths[i[pos:]] = True
					if len(paths) > 10: break
		if len(paths) == 0:
			return False
		sci.send_text_message(gsc.AUTOCSHOW, len(path), '\n'.join(paths.keys()))
		# print "\n".join(paths)

	def __init__(self):
		geany.Plugin.__init__(self)
		geany.signals.connect("editor-notify", self.editor_cb)
		self.python_dir = os.path.dirname(os.__file__)
