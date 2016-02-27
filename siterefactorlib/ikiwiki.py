# coding: utf-8

from .core import BodyWriter, MarkdownPage
import json
import os
import re
import shutil
import logging

log = logging.getLogger()

class IkiwikiMarkdown(BodyWriter):
    def generate_codebegin(self, el):
        self.chunks.append("[[!format {lang} '''\n".format(lang=el.lang))

    def generate_codeend(self, el):
        self.chunks.append("''']]\m")

    def generate_ikiwikimap(self, el):
        self.chunks.append("[[!map {content}]]\n".format(content=el.content))

    def generate_inlineimage(self, el):
        if el.target is None:
            self.chunks.append("(missing image: {alt})".format(alt=el.text))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            self.chunks.append('[[!img {fname} alt="{alt}"]]'.format(fname=path, alt=el.text))

    def generate_internallink(self, el):
        if el.target is None:
            self.chunks.append(el.text)
        elif el.target.TYPE == "markdown":
            path = os.path.relpath(el.target.relpath_without_extension, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath_without_extension
            self.chunks.append('[[{text}|{target}.mdwn]]'.format(text=el.text, target=path))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath
            self.chunks.append('[[{text}|{target}]]'.format(text=el.text, target=path))

    def generate_directive(self, el):
        super().generate_directive(el)
        self.chunks.append("[[{}]]".format(el.content))


class IkiwikiWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def write(self, site):
        # Relocate yyyy/* under blog/
        for relpath, page in list(site.pages.items()):
            if re.match(r"^\d{4}/", relpath):
                site.relocate(page, os.path.join("blog", relpath))

        # Remove leading spaces from markdown content
        for page in site.pages.values():
            if page.TYPE != "markdown": continue
            while page.body and page.body[0].is_blank:
                page.body.pop(0)

        # Generate output
        for page in site.pages.values():
            getattr(self, "write_" + page.TYPE)(page)

        # Generate tag indices
        tags = set()
        tags.update(*(x.tags for x in site.pages.values()))
        for tag in tags:
            dst = os.path.join(self.root, "tags", tag + ".mdwn")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wt") as out:
                desc = site.tag_descriptions.get(tag, None)
                if desc is None:
                    desc = [tag.capitalize() + "."]
                for line in desc:
                    print(line, file=out)
                print(file=out)
                print('[[!inline pages="link(tags/{tag})" show="10"]]'.format(tag=tag), file=out)

        # Generate index of tags
        dst = os.path.join(self.root, "tags/index.mdwn")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wt") as out:
            print('[[!pagestats pages="tags/*"]]', file=out)
            print('[[!inline pages="tags/*"]]', file=out)

    def write_static(self, page):
        dst = os.path.join(self.root, page.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(page.site.root, page.orig_relpath), dst)

    def write_markdown(self, page):
        writer = IkiwikiMarkdown()
        writer.read(page)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, page.relpath_without_extension + ".mdwn")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        with open(dst, "wt") as out:
            if page.date is not None:
                print('[[!meta date="{date}"]]'.format(date=page.date_as_iso8601), file=out)
            if page.tags:
                print("[[!tag {tags}]]".format(
                    tags=" ".join("tags/{tag}".format(tag=tag) for tag in sorted(page.tags))), file=out)
            if page.title is not None:
                print("# {title}".format(title=page.title), file=out)
            out.write("\n")
            writer.write(out)

        for relpath in page.aliases:
            dst = os.path.join(self.root, relpath)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wt") as out:
                if page.date is not None:
                    print('[[!meta date="{date}"]]'.format(date=page.date_as_iso8601), file=out)
                print('[[!meta redir="{relpath}"]]'.format(relpath=page.relpath_without_extension + ".mdwn"), file=out)

