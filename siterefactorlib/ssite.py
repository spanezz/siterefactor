# coding: utf-8

from .core import BodyWriter, MarkdownPage
import json
import os
import re
import shutil
import logging

log = logging.getLogger()

class SSiteMarkdown(BodyWriter):
    def generate_codebegin(self, el):
        self.chunks.append("```{lang}\n".format(lang=el.lang))

    def generate_codeend(self, el):
        self.chunks.append("```\n")

    def generate_ikiwikimap(self, el):
        self.chunks.append("[[!map {content}]]\n".format(content=el.content))

    def generate_inlineimage(self, el):
        if el.target is None:
            self.chunks.append("(missing image: {alt})".format(alt=el.text))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            self.chunks.append('![{alt}]({fname})'.format(fname=path, alt=el.text))

    def generate_internallink(self, el):
        if el.target is None:
            if el.text is None:
                log.warn("%s:%s: found link with no text and unresolved target", el.page.relpath, el.lineno)
            else:
                self.chunks.append(el.text)
        elif el.target.TYPE == "markdown":
            path = os.path.relpath(el.target.relpath_without_extension, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath_without_extension
            if el.text is None or el.text == path:
                self.chunks.append('[{target}]({target})'.format(target=path))
            else:
                self.chunks.append('[{text}]({target})'.format(text=el.text, target=path))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath
            if el.text is None:
                self.chunks.append('[{target}]({target})'.format(target=path))
            else:
                self.chunks.append('[{text}]({target})'.format(text=el.text, target=path))

    def generate_directive(self, el):
        super().generate_directive(el)
        self.chunks.append("[[{}]]".format(el.content))


class SSiteWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def output_abspath(self, relpath):
        abspath = os.path.join(self.root, "site", relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

    def write(self, site):
        # Remove leading spaces from markdown content
        for page in site.pages.values():
            if page.TYPE != "markdown": continue
            while page.body and page.body[0].is_blank:
                page.body.pop(0)

        # Generate output
        for page in site.pages.values():
            getattr(self, "write_" + page.TYPE)(page)

        ## Generate tag indices
        #tags = set()
        #tags.update(*(x.tags for x in site.pages.values()))
        #for tag in tags:
        #    dst = os.path.join(self.root, "tags", tag + ".mdwn")
        #    os.makedirs(os.path.dirname(dst), exist_ok=True)
        #    with open(dst, "wt") as out:
        #        desc = site.tag_descriptions.get(tag, None)
        #        if desc is None:
        #            desc = [tag.capitalize() + "."]
        #        for line in desc:
        #            print(line, file=out)
        #        print(file=out)
        #        print('[[!inline pages="link(tags/{tag})" show="10"]]'.format(tag=tag), file=out)

        ## Generate index of tags
        #dst = os.path.join(self.root, "tags/index.mdwn")
        #os.makedirs(os.path.dirname(dst), exist_ok=True)
        #with open(dst, "wt") as out:
        #    print('[[!pagestats pages="tags/*"]]', file=out)
        #    print('[[!inline pages="tags/*"]]', file=out)

    def write_static(self, page):
        dst = self.output_abspath(page.relpath)
        shutil.copy2(page.abspath, dst)

    def write_markdown(self, page):
        writer = SSiteMarkdown()
        writer.read(page)
        if writer.is_empty():
            return

        meta = {}
        if page.title is not None:
            meta["title"] = page.title
        if page.tags:
            meta["tags"] = sorted(page.tags)
        if page.date is not None:
            meta["date"] = page.date.strftime("%Y-%m-%d")

        dst = self.output_abspath(page.relpath_without_extension + ".md")
        with open(dst, "wt") as out:
            json.dump(meta, out, indent=2)
            print(file=out)
            if page.title is not None:
                print("# {title}".format(title=page.title), file=out)
                print(file=out)
            writer.write(out)

        #for relpath in page.aliases:
        #    dst = os.path.join(self.root, relpath)
        #    os.makedirs(os.path.dirname(dst), exist_ok=True)
        #    with open(dst, "wt") as out:
        #        print('[[!meta redir="{relpath}"]]'.format(relpath=page.relpath_without_extension), file=out)
