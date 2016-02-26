# coding: utf-8

from .core import BodyWriter
import json
import os
import shutil
import pytz
from dateutil.tz import tzlocal
import logging

log = logging.getLogger()

class BodyPelican(BodyWriter):
    def line_code_begin(self, lang, **kw):
        self.output.append("```{}".format(lang))

    def line_code_end(self, **kw):
        self.output.append("```")

    def line_text(self, **kw):
        self.output.append(self.line)

    def line_multi(self, parts, **kw):
        res = []
        for name, kw in parts:
            res.append(getattr(self, name)(**kw))
        self.output.append("".join(res))

    def part_img(self, fname, alt, **kw):
        return '![{alt}]({{attach}}{fname})'.format(fname=fname, alt=alt)

    def part_internal_link(self, text, target, **kw):
        dest = self.post.resolve_link_relpath(target)
        if os.path.exists(os.path.join(self.post.site.root, dest)):
            return '[{text}]({{attach}}{target})'.format(text=text, target=dest)
        else:
            return '[{text}]({{filename}}{target}.md)'.format(text=text, target=dest)

    def part_text(self, text):
        return text

    def part_directive(self, text):
        log.warn("%s:%s: found unsupported custom tag [[%s]]", self.post.relpath, self.lineno, text)
        return "[[{}]]".format(text)


class PelicanWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, site):
        for post in site.posts.values():
            self.write_post(site.root, post)

        for static in site.static.values():
            self.write_static(site.root, static)

    def write_static(self, src_root, static):
        dst = os.path.join(self.root, "content", static.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(src_root, static.relpath), dst)

    def write_post(self, src_root, post):
        writer = BodyPelican(post)
        post.parse_body(writer)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, "content", post.relpath + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        with open(dst, "wt") as out:
            if post.title is not None:
                print("Title: {}".format(post.title), file=out)
            if post.tags:
                print("Tags: {}".format(", ".join(sorted(post.tags))), file=out)
            if post.date is not None:
                tz = tzlocal()
                ts = post.date.astimezone(tz)
                print("Date: {}".format(ts.strftime("%Y-%m-%d %H:%M")), file=out)
            print(file=out)
            writer.write(out)

