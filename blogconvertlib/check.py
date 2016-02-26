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
        target_relpath = self.resolve_link_relpath(target)
        if target_relpath is None:
            log.warn("%s: no target file found for link target %s", self.post.relpath, target)

    def part_text(self, text):
        pass

    def part_directive(self, text):
        log.warn("%s: Unsupported directive [[%s]]", self.post.relpath, text)


class Checker:
    def __init__(self):
        self.count_static = 0
        self.count_posts = 0

    def write(self, blog):
        for post in blog.posts.values():
            self.write_post(blog.root, post)

        for static in blog.static.values():
            self.write_static(blog.root, static)

        print("{} posts, {} static files".format(self.count_posts, self.count_static))

    def write_static(self, src_root, static):
        self.count_static += 1

    def write_post(self, src_root, post):
        self.count_posts += 1

        writer = BodyChecker(post)
        post.parse_body(writer)
