# coding: utf-8

from .core import BodyWriter
import os
import shutil
import pytz
from dateutil.tz import tzlocal
import logging

log = logging.getLogger()

class BodyNikola(BodyWriter):
    def line_code_begin(self, lang, **kw):
        self.output.append("```{}".format(lang))

    def line_code_end(self, **kw):
        self.output.append("```")

    def line_include_map(self, **kw):
        if self.lineno != 1:
            log.warn("%s:%s: found map tag not in first line", self.post.relpath, self.lineno)

    def line_text(self, **kw):
        self.output.append(self.line)

    def line_multi(self, parts, **kw):
        res = []
        for name, kw in parts:
            res.append(getattr(self, name)(**kw))
        self.output.append("".join(res))

    def part_img(self, fname, alt, **kw):
        return '![{alt}]({fname})'.format(fname=fname, alt=alt)

    def part_internal_link(self, text, target, **kw):
        return '[{text}]({{{{< relref "{target}.md" >}}}})'.format(text=text, target=target)

    def part_text(self, text):
        return text

    def part_directive(self, text):
        log.warn("%s:%s: found unsupported custom tag [[%s]]", self.post.relpath, self.lineno, text)
        return "[[{}]]".format(text)


class NikolaWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, blog):
        for post in blog.posts.values():
            self.write_post(blog.root, post)

        for static in blog.static.values():
            self.write_static(blog.root, static)

    def write_static(self, src_root, static):
        dst = os.path.join(self.root, static.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(src_root, static.relpath), dst)

    def write_post(self, src_root, post):
        writer = BodyNikola(post)
        post.parse_body(writer)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, post.relpath + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wt") as out:
            print("<!--", file=out)
            if post.title is not None:
                print(".. title: {}".format(post.title), file=out)
            if post.tags:
                print(".. tags: {}".format(", ".join(sorted(post.tags))), file=out)
            if post.date is not None:
                tz = tzlocal()
                ts = post.date.astimezone(tz)
                offset = tz.utcoffset(ts)
                offset_sec = (offset.days * 24 * 3600 + offset.seconds)
                offset_hrs = offset_sec // 3600
                offset_min = offset_sec % 3600
                if offset:
                    tz_str = ' UTC{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
                else:
                    tz_str = ' UTC'
                print(".. date: {}".format(ts.strftime("%Y-%m-%d %H:%M:%S") + tz_str), file=out)
            print("-->", file=out)
            print(file=out)
            out.write("\n")
            writer.write(out)

