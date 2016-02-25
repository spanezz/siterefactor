# coding: utf-8

from .core import BodyWriter
import json
import os
import shutil
import logging

log = logging.getLogger()

class BodyHugo(BodyWriter):
    def line_code_begin(self, lang, **kw):
        self.output.append("{{{{< highlight {} >}}}}".format(lang))

    def line_code_end(self, **kw):
        self.output.append("{{< /highlight >}}")

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
        return '{{{{< figure src="{fname}" alt="{alt}" >}}}}'.format(fname=fname, alt=alt)

    def part_internal_link(self, text, target, **kw):
        return '[{text}]({{{{< relref "{target}.md" >}}}})'.format(text=text, target=target)

    def part_text(self, text):
        return text

    def part_directive(self, text):
        log.warn("%s:%s: found unsupported custom tag [[%s]]", self.post.relpath, self.lineno, text)
        return "[[{}]]".format(text)


class HugoWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, blog):
        for post in blog.posts.values():
            self.write_post(blog.root, post)

        for static in blog.static.values():
            self.write_static(blog.root, static)

    def write_static(self, src_root, static):
        dst = os.path.join(self.root, "content", static.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(src_root, static.relpath), dst)

    def write_post(self, src_root, post):
        writer = BodyHugo(post)
        post.parse_body(writer)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, "content", post.relpath + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        meta = {}
        if post.title is not None:
            meta["title"] = post.title
        if post.tags:
            meta["tags"] = sorted(post.tags)
        if post.date is not None:
            meta["date"] = post.date.strftime("%Y-%m-%d")

        with open(dst, "wt") as out:
            json.dump(meta, out, indent=2)
            out.write("\n")
            writer.write(out)
