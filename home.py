"""MkDocs hook: docs/index.md, the landing page, is the site's root (#280). The docs are the repo itself (same-dir), so
without this it would sit at /docs/; the README, for contributors, stays off the site (mkdocs.yml exclude_docs)."""


def on_files(files, config):
    files.get_file_from_path("docs/index.md").dest_uri = "index.html"
    return files
