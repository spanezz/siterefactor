# coding: utf-8

from .core import BodyWriter
import json
import os
import shutil
import logging

log = logging.getLogger()

class BodyHugo(BodyWriter):
    def __init__(self, page):
        super().__init__(page)
        #self.is_blog = bool(re.match(r"^\d{4}/", page))

    def line_code_begin(self, lang, **kw):
        self.output.append("{{{{< highlight {} >}}}}".format(lang))

    def line_code_end(self, **kw):
        self.output.append("{{< /highlight >}}")

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
        dest = self.page.resolve_link_relpath(target)
        reldest = os.path.relpath(dest, self.page.relpath)
        if os.path.exists(os.path.join(self.page.site.root, dest)):
            return '[{text}]({{{{< relref "{target}" >}}}})'.format(text=text, target=reldest)
        else:
            return '[{text}]({{{{< relref "{target}.md" >}}}})'.format(text=text, target=reldest)

    def part_text(self, text):
        return text

    def part_directive(self, text):
        log.warn("%s:%s: found unsupported custom tag [[%s]]", self.page.relpath, self.lineno, text)
        return "[[{}]]".format(text)


class HugoWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, site):
        for page in site.pages.values():
            self.write_page(site.root, page)

        for static in site.static.values():
            self.write_static(site.root, static)

    def write_static(self, src_root, static):
        dst = os.path.join(self.root, "content", static.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(src_root, static.relpath), dst)

    def write_page(self, src_root, page):
        writer = BodyHugo(page)
        page.parse_body(writer)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, "content", page.relpath + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        meta = {}
        if page.title is not None:
            meta["title"] = page.title
        if page.tags:
            meta["tags"] = sorted(page.tags)
        if page.date is not None:
            meta["date"] = page.date.strftime("%Y-%m-%d")

        with open(dst, "wt") as out:
            json.dump(meta, out, indent=2)
            out.write("\n")
            writer.write(out)
