# coding: utf-8
import os
import re
import datetime
import json
import logging
import pytz

log = logging.getLogger()


class Ctimes:
    def __init__(self, fname):
        self.by_relpath = {}
        for fname, ctime in self.parse(fname):
            self.by_relpath[fname] = ctime

    def parse(self, fname):
        with open(fname, "rt") as fd:
            data = json.load(fd)
            for fname, info in data.items():
                yield fname, info["ctime"]


class Page:
    def __init__(self, site, relpath, ctime=None):
        # Site that owns this page
        self.site = site

        # Relative path of the page, without .mdwn extension
        self.relpath = relpath[:-5]

        # Source file name
        self.src = None

        # Page date
        if ctime is not None:
            self.date = pytz.utc.localize(datetime.datetime.utcfromtimestamp(ctime))
        else:
            self.date = None

        # Page title
        self.title = None

        # Page tags
        self.tags = set()

        # Page content lines original markdown
        self.body = []

        # Rules used to match metadata lines
        self.meta_line_rules = [
            (re.compile(r"^#\s*(?P<title>.+)"), self.parse_title),
            (re.compile(r"^\[\[!tag (?P<tags>[^\]]+)\]\]"), self.parse_tags),
            (re.compile(r'^\[\[!meta date="(?P<date>\d+-\d+-\d+)"\]\]'), self.parse_date),
        ]

        # Rules used to match whole lines
        self.body_line_rules = [
            (re.compile(r'^\[\[!format (?P<lang>\S+) """'), "line_code_begin"),
            (re.compile(r"^\[\[!format (?P<lang>\S+) '''"), "line_code_begin"),
            (re.compile(r'^"""\]\]'), "line_code_end"),
            (re.compile(r"^'''\]\]"), "line_code_end"),
            (re.compile(r"^\[\[!map"), "line_include_map"),
        ]

        # Rules used to parse directives
        self.body_directive_rules = [
            (re.compile(r'!img (?P<fname>\S+) alt="(?P<alt>[^"]+)"'), "part_img"),
            (re.compile(r"(?P<text>[^|]+)\|(?P<target>[^\]]+)"), "part_internal_link"),
        ]

    def resolve_link_relpath(self, target):
        target = target.lstrip("/")
        root = self.relpath
        while True:
            target_relpath = os.path.join(root, target)
            abspath = os.path.join(self.site.root, target_relpath)
            if os.path.exists(abspath):
                return target_relpath
            if os.path.exists(abspath + ".mdwn"):
                return target_relpath
            if not root or root == "/":
                return None
            root = os.path.dirname(root)

    def resolve_link_title(self, target_relpath):
        # Resolve mising text from target page title
        dest_page = self.site.pages.get(target_relpath, None)
        if dest_page is not None:
            return dest_page.title
        else:
            return None

    def parse_title(self, line, title, **kw):
        if self.title is None:
            self.title = title
            # Discard the main title
            return None
        else:
            return line

    def parse_tags(self, line, tags, **kw):
        for t in tags.split():
            if t.startswith("tags/"):
                t = t[5:]
            self.tags.add(t)
        # Line is discarded
        return None

    def parse_date(self, line, date, **kw):
        self.date = pytz.utc.localize(datetime.datetime.strptime(date, "%Y-%m-%d"))
        return None

    def read(self, src):
        self.src = src
        if self.date is None:
            self.date = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))
        with open(src, "rt") as fd:
            for lineno, line in enumerate(fd, 1):
                self.lineno = lineno
                line = line.rstrip()

                # Search entire body lines for whole-line metadata directives
                for regex, func in self.meta_line_rules:
                    mo = regex.match(line)
                    if mo:
                        line = func(line, **mo.groupdict())
                        break

                if line is not None:
                    self.body.append((lineno, line))


    def parse_body_line(self, lineno, line, dest):
        # Search entire body lines for whole-line directives
        for regex, func in self.body_line_rules:
            mo = regex.match(line)
            if mo:
                getattr(dest, func)(**mo.groupdict())
                return

        # Split the line looking for ikiwiki directives
        re_directive = re.compile(r"\[\[([^\]]+)\]\]")
        parts = re_directive.split(line)
        if len(parts) == 1:
            dest.line_text()
            return

        res = []
        for idx, p in enumerate(parts):
            if idx % 2 == 0:
                res.append(("part_text", { "text": p }))
            else:
                res.append(self.parse_body_directive(lineno, p))
        dest.line_multi(res)

    def parse_body_directive(self, lineno, text):
        for regex, func in self.body_directive_rules:
            mo = regex.match(text)
            if mo:
                return func, mo.groupdict()

        # Just target names in [[..]] resolve as links
        target_relpath = self.resolve_link_relpath(text)
        if target_relpath is not None:
            title = self.resolve_link_title(target_relpath)
            if title is None: title = text
            return "part_internal_link", { "text": title, "target": text }

        return "part_directive", { "text": text }

    def parse_body(self, dest):
        for lineno, line in self.body:
            dest.start_line(lineno, line)
            self.parse_body_line(lineno, line, dest)


class Static:
    def __init__(self, site, relpath, ctime):
        self.site = site
        self.relpath = relpath
        self.ctime = ctime


class Site:
    def __init__(self, root):
        self.root = root

        # Extra ctime information
        self.ctimes = None

        # Markdown pages
        self.pages = {}

        # Static files
        self.static = {}

    def load_extrainfo(self, pathname):
        self.ctimes = Ctimes(pathname)

    def read_years(self):
        for d in os.listdir(self.root):
            if not re.match(r"^\d{4}$", d): continue
            self.read_tree(d)

    def read_talks(self):
        talks_dir = os.path.join(self.root, "talks")
        if not os.path.isdir(talks_dir): return
        self.read_tree("talks")

    def read_tree(self, relpath):
        log.info("Loading directory %s", relpath)
        abspath = os.path.join(self.root, relpath)
        for f in os.listdir(abspath):
            absf = os.path.join(abspath, f)
            if os.path.isdir(absf):
                self.read_tree(os.path.join(relpath, f))
            elif f.endswith(".mdwn"):
                self.read_page(os.path.join(relpath, f))
            elif os.path.isfile(absf):
                self.read_static(os.path.join(relpath, f))

    def _instantiate(self, Resource, relpath):
        if self.ctimes is not None:
            ctime = self.ctimes.by_relpath.get(relpath, None)
        else:
            ctime = None
        return Resource(self, relpath, ctime)

    def read_page(self, relpath):
        log.info("Loading page %s", relpath)
        page = self._instantiate(Page, relpath)
        page.read(os.path.join(self.root, relpath))
        self.pages[relpath] = page

    def read_static(self, relpath):
        log.info("Loading static file %s", relpath)
        static = self._instantiate(Static, relpath)
        self.static[relpath] = static


class BodyWriter:
    def __init__(self, page):
        self.page = page
        self.lineno = None
        self.line = None
        self.output = []

    def start_line(self, lineno, line):
        self.lineno = lineno
        self.line = line

    def write(self, out):
        for line in self.output:
            print(line, file=out)

    def is_empty(self):
        for line in self.output:
            if line:
                return False
        return True

    def line_code_begin(self, lang, **kw):
        pass

    def line_code_end(self, **kw):
        pass

    def line_include_map(self, **kw):
        if self.lineno != 1:
            log.warn("%s:%s: found map tag not in first line", self.page.relpath, self.lineno)

    def line_text(self, **kw):
        pass

