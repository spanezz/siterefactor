# coding: utf-8

from .core import BodyWriter, MarkdownPage
import json
import os
import re
import shutil
import logging

log = logging.getLogger()

class HugoMarkdown(BodyWriter):
    def generate_codebegin(self, el):
        self.chunks.append("{{{{< highlight {} >}}}}".format(el.lang))

    def generate_codeend(self, el):
        self.chunks.append("{{< /highlight >}}")

    def generate_ikiwikimap(self, el):
        pass

    def generate_inlineimage(self, el):
        if el.target is None:
            self.chunks.append("(missing image: {alt})".format(alt=el.text))
        else:
            #path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            path = el.target.relpath
            self.chunks.append('{{{{< figure src="/{fname}" alt="{alt}" >}}}}'.format(fname=path, alt=el.text))

    def generate_internallink(self, el):
        if el.target is None:
            self.chunks.append(el.text)
        elif el.target.TYPE == "markdown":
            #path = os.path.relpath(el.target.relpath_without_extension, os.path.dirname(el.page.relpath))
            self.chunks.append('[{text}]({{{{< relref "{target}.md" >}}}})'.format(text=el.text, target=el.target.relpath_without_extension))
        else:
            self.chunks.append('[{text}](/{target})'.format(text=el.text, target=el.target.relpath))

    def generate_directive(self, el):
        super().generate_directive(el)
        self.chunks.append("[[{}]]".format(el.content))


class HugoWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, site):
        # Relocate yyyy/* under blog/
        for relpath, page in list(site.pages.items()):
            if re.match(r"^\d{4}/", relpath):
                site.relocate(page, os.path.join("blog", relpath))

        # Generate output
        for page in site.pages.values():
            getattr(self, "write_" + page.TYPE)(page)

    def write_static(self, page):
        dst = os.path.join(self.root, "content", page.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(page.site.root, page.orig_relpath), dst)

    def write_markdown(self, page):
        writer = HugoMarkdown()
        writer.read(page)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, "content", page.relpath_without_extension + ".md")
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
