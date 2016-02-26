# coding: utf-8

from .core import BodyWriter
import os
import shutil
import json
import logging

log = logging.getLogger()

class BodyChecker(BodyWriter):
    def line_multi(self, parts, **kw):
        for name, kw in parts:
            getattr(self, name)(**kw)

    def part_img(self, fname, alt, **kw):
        pass

    def part_internal_link(self, text, target, **kw):
        target_relpath = self.page.resolve_link_relpath(target)
        if target_relpath is None:
            log.warn("%s: no target file found for link target %s", self.page.relpath, target)

    def part_text(self, text):
        pass

    def part_directive(self, text):
        log.warn("%s: Unsupported directive [[%s]]", self.page.relpath, text)


class Checker:
    def __init__(self):
        self.count_static = 0
        self.count_pages = 0

    def write(self, site):
        for page in site.pages.values():
            self.write_page(site.root, page)

        for static in site.static.values():
            self.write_static(site.root, static)

        print("{} pages, {} static files".format(self.count_pages, self.count_static))

    def write_static(self, src_root, static):
        self.count_static += 1

    def write_page(self, src_root, page):
        self.count_pages += 1

        writer = BodyChecker(page)
        page.parse_body(writer)
