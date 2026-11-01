# mkdocs-macros 1.5.0: modules, hidden delimiters, strict builds (2026-11-01)

Question: can one Markdown file read as plain Markdown on GitHub (macros hidden in HTML comments) while the MkDocs
site renders the macros from a Python module that imports repo packages (`reactions.director`), and fail the build
on any macro error?

Sources: mkdocs-macros-plugin source at tag v1.5.0 (`MP/` = https://github.com/fralau/mkdocs-macros-plugin/blob/v1.5.0/,
commit 0536f4d), its docs (`RTD/` = https://mkdocs-macros-plugin.readthedocs.io/en/latest/, built from `MP/webdoc/docs/`),
Jinja 3.1.6 source (`J/` = https://github.com/pallets/jinja/blob/3.1.6/src/jinja2/) and API docs
(https://jinja.palletsprojects.com/en/stable/api/), PyPI JSON, and test builds in a scratch venv (mkdocs 1.6.1,
mkdocs-macros-plugin 1.5.0, Jinja 3.1.6, mkdocs-same-dir 0.1.5, Python 3.12), all read or run 2026-11-01.

## Answers

1. A `main.py` beside `mkdocs.yml` with `define_env(env)`; resolved against the **config file's dir**, not
   `docs_dir`. The project root is **not** put on `sys.path` for a `main.py` file: under the `mkdocs` console script
   `import reactions.director` fails, and the plugin **swallows that ImportError** as "No default module `main` found"
   (open issue #285). Fix: `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` at the top of `main.py`
   (or run `python -m mkdocs`, or install the package).
2. `j2_block_start_string`, `j2_block_end_string`, `j2_variable_start_string`, `j2_variable_end_string` (since 0.4.0,
   2020), `j2_comment_start_string`, `j2_comment_end_string` (released in 1.2.0; the docs say 1.0.7). `<!--{%`/`%}-->`,
   `<!--{{`/`}}-->`, `<!--{#`/`#}-->` work (tested). Jinja only requires the three start strings to differ.
3. Default is lax: a macro error renders an error page and logs a WARNING; `--strict` turns that into
   "Aborted with 1 warnings" (exit 1). `on_error_fail: true` exits 100 on its own. But the default
   `on_undefined: keep` prints an undefined variable as `{{ name }}` with **no warning**, so `--strict` passes; set
   `on_undefined: strict`.
4. `render_by_default: true` (default) renders every page; `render_macros: false` in front matter always wins;
   with `render_by_default: false` only pages with `render_macros: true` (or `force_render_paths`) render.
5. Yes: the whole page source is one Jinja template, fenced code included. With default delimiters
   `${{ secrets.X }}` fails the page (`'secrets' is undefined`). With the `<!--{{` delimiters it passes through untouched.
6. No ordering issue: macros, search and same-dir share no event. same-dir 0.1.5 now depends on `properdocs` and pins
   `mkdocs<=1.6.1`; with `docs_dir: .` it copies non-Markdown files in subfolders (e.g. `reactions/*.py`) into the site.

## Findings

1. **Module loading.** Options `module_name` (default `main`) and `modules` (installed "pluglets")
   (MP/mkdocs_macros/plugin.py#L119-L155; RTD/#configuration-of-the-plugin). The module is looked up in
   `project_dir` = dirname of `config_file_path` (MP/mkdocs_macros/plugin.py#L243-L247); "a path relative to the
   directory of the config file" is allowed, e.g. `module_name: include/source_code` (RTD/macros/#local-module).
   A `.py` file is loaded with `spec_from_file_location` + `exec_module`, with no `sys.path` change; only a package
   directory inserts its parent dir into `sys.path` (MP/mkdocs_macros/util.py#L173-L206, changed in 1.5.0 for #278,
   MP/CHANGELOG.md#L7-L9). The plugin calls `module.define_env(env)` (plus optional `on_pre_page_macros`,
   `on_post_page_macros`, `on_post_build`), and raises NameError if none exist (MP/mkdocs_macros/plugin.py#L498-L557).
   In `define_env`, `env.variables['x'] = ...` (or `env.variables.x`) and the `@env.macro` / `@env.filter` decorators
   register names (RTD/macros/#the-define_env-function). Modules load last in `on_config`, after `extra:` and
   `include_yaml`, so they win (MP/mkdocs_macros/plugin.py#L742-L781).
2. **The swallowed import error.** `_load_modules` wraps the import and `define_env` call in `except ImportError`; for the
   default name `main` it only logs INFO "No default module `main` found" and carries on
   (MP/mkdocs_macros/plugin.py#L584-L599). A ModuleNotFoundError raised by `main.py` itself hits that branch. Open
   issue: https://github.com/fralau/mkdocs-macros-plugin/issues/285 (2026-04-09). Reproduced: `mkdocs build` from the
   project dir printed `sys.path[0]` = the venv's `bin`, the INFO line, then failed only later on
   `'table' is undefined`. Python puts the script's dir first on `sys.path`, or the cwd for `-m module`
   (https://docs.python.org/3/library/sys_path_init.html), so `python -m mkdocs build` from the repo root imported it.
   The `sys.path.insert` at the top of `main.py` worked under both (`__file__` is set by `spec_from_file_location`).
3. **Delimiter options.** Every non-empty `j2_*` option is passed to `jinja2.Environment` with the prefix stripped
   (MP/mkdocs_macros/plugin.py#L828-L846). Docs: RTD/rendering/#solution-5-altering-the-syntax-of-jinja2-for-mkdocs-macros
   ("New in 1.0.7: parameters `j2_comment_start_string` and `j2_comment_end_string`"; the maintainers warn they will not
   help with custom markers). History: block/variable markers in commit ac912e0 (2020-02-22), first tag v0.4.0;
   comment markers in #208 (2024-02-17), first tag v1.2.0 and listed under 1.2.0 in MP/CHANGELOG.md#L29-L37.
   **Conflict:** the docs say 1.0.7, the changelog and tags say 1.2.0; either way 1.5.0 has them. `j2_extensions` is
   new in 1.4.1 (MP/CHANGELOG.md#L11-L13).
4. **Jinja constraints.** `_environment_config_check` asserts
   `block_start_string != variable_start_string != comment_start_string` (J/environment.py#L126-L141). As written it
   checks block≠variable and variable≠comment, not block≠comment. The lexer orders the start tokens by length, longest
   first (J/lexer.py#L213-L245), so a shared `<!--{` prefix is fine. Parameter list:
   https://jinja.palletsprojects.com/en/stable/api/#jinja2.Environment.
5. **Hidden-delimiter test (passed `--strict`).** With the six `<!--{…` / `…}-->` options:
   `Value: <!--{{ table.stop }}-->` → `Value: nod`; `<!--{# hidden #}-->` → nothing; a
   `<!--{% for k, v in table.items() %}-->` … `<!--{% endfor %}-->` list rendered; a fence containing
   `${{ secrets.X }}`, `{{ not_jinja }}` and `{% raw %}` came out verbatim; a plain `<!-- note -->` stayed a comment.
   GitHub hides HTML comments
   (https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#hiding-content-with-comments).
   Caveat (inferred from the GFM spec, not tested on github.com): a line that *starts* with `<!--` opens an HTML block
   that runs to the line containing `-->` (https://github.github.com/gfm/#html-blocks, condition 2). So on GitHub,
   Markdown after a macro at the start of a line (`<!--{{ x }}--> **bold**`) is passed through as raw HTML, and
   `**bold**` is not rendered. Keep macros mid-line or alone on their line. MkDocs is unaffected (the comment is gone
   before Markdown runs; tested). On GitHub the value is simply missing, so the sentence has to read without it.
6. **Error behaviour** (`render`, MP/mkdocs_macros/plugin.py#L697-L718). Any exception during rendering is formatted
   into an error page (MP/mkdocs_macros/errors.py#L10-L25) and logged at WARNING through the `mkdocs.plugins.*` logger
   (MP/mkdocs_macros/util.py#L33, #L67-L86), which MkDocs `--strict` counts. With `on_error_fail: true` it calls
   `exit(100)` (ERROR_MACRO). Docs: RTD/troubleshooting/#instructing-mkdocs-macros-to-fail-in-case-of-error,
   RTD/troubleshooting/#instructing-mkdocs-to-fail-in-case-of-any-warning, RTD/advanced/ ("From version 1.1.2").
   Test results (exit code):

   | page | defaults | `--strict` | `on_error_fail` |
   |---|---|---|---|
   | macro raises | 0, error page, 1 WARNING | 1, "Aborted with 1 warnings in strict mode!" | 100 |
   | Jinja syntax error | 0, error page | 1 | 100 (same path) |
   | undefined `nope` | 0, prints `{{ nope }}`, no warning | **0** | 0 |
   | undefined `nope.x` | 0, error page | 1 | 100 |
   | undefined `nope`, `on_undefined: strict` | 0, error page | 1 | 100 |

7. **`on_undefined`** maps `keep`→DebugUndefined (default), `silent`→Undefined, `strict`→StrictUndefined,
   `lax`→LaxUndefined (MP/mkdocs_macros/plugin.py#L67-L81, #L828-L832; RTD/troubleshooting/#what-happens-if-a-variable-is-undefined).
   DebugUndefined prints a hard-coded `{{ name }}` whatever the custom delimiters (J/runtime.py#L1007-L1036), so with
   `<!--{{` delimiters a typo shows up on the site as literal `{{ name }}`. `silent` gives a blank, also without a
   warning (tested). For CI: `on_undefined: strict` plus `--strict` or `on_error_fail: true`.
8. **Opt-in/opt-out.** `render_by_default` (bool, default true) (MP/mkdocs_macros/plugin.py#L128). In `render`: front
   matter `render_macros: false` returns the page unrendered before anything else, even when forced. If
   `render_by_default` is false, a page renders only with `render_macros: true` or a `force_render_paths` match
   (gitwildmatch, relative to docs_dir). The front-matter values also become template variables
   (MP/mkdocs_macros/plugin.py#L664-L693). The old `ignore_macros` front-matter key raises ValueError
   (RTD/rendering/#solution-1-opt-out-exclude-one-page-from-the-rendering-process, #solution-2-opt-in-specify-which-pages-must-be-rendered).
9. **Whole page, code fences included.** `on_page_markdown` renders the full Markdown source string as one template;
   the page title is rendered too if it contains a start marker (MP/mkdocs_macros/plugin.py#L935-L980). The docs say
   it outright: fencing "will not prevent their interpretation, because this macros plugin intentionally ignores
   them" (RTD/rendering/#two-cautions). Test with default delimiters: a fenced `${{ secrets.X }}` →
   `UndefinedError: 'secrets' is undefined`, WARNING, `--strict` exit 1. A fenced `${{ github.ref }}` without
   `--strict` → exit 0 with an error page shipped. Escapes are `{% raw %}`, `render_macros: false`, or other delimiters
   (RTD/rendering/#solutions).
10. **Plugin order.** MkDocs calls each event in `plugins:` order unless a plugin sets `event_priority`
    (https://github.com/mkdocs/mkdocs/blob/1.6.1/docs/dev-guide/plugins.md, "Event Priorities"); none of the three sets
    one. Macros uses on_config, on_pre_build, on_nav, on_serve, on_page_markdown, on_post_build; same-dir only
    `on_files` plus a monkeypatch of `Dir.post_validation` in `__init__`; search uses on_config, on_pre_build,
    on_page_context, on_post_build (mkdocs/contrib/search/__init__.py#L65-L95). Search indexes the rendered page, so
    it sees macro output. Tested with `docs_dir: .`, `- search`, `- same-dir`, `- macros` in both orders: identical
    sites, `README.md` → `index.html` with macros rendered, `v=nod` in `search_index.json`.
    RTD/#declaration-of-the-macros-plugin: list `search` explicitly once `plugins:` exists. No macros or same-dir
    issue mentions the other (GitHub issue search).
11. **same-dir 0.1.5 side notes** (https://github.com/oprypin/mkdocs-same-dir, PyPI). It requires
    `mkdocs<=1.6.1,>=1.2` and `properdocs>=1.6.5` (released 2026-04-17). Run from the `mkdocs` executable, it prints
    a stderr banner "MkDocs may break support for all existing plugins…", silenced by `DISABLE_MKDOCS_2_WARNING=true`;
    that banner did not count as a `--strict` warning. Its `on_files` drops non-Markdown files at the docs root (so
    `main.py` is not published) but keeps everything in subfolders: the test site shipped `reactions/__init__.py` and
    `reactions/director.py`. Use MkDocs `exclude_docs` for code folders.
12. **Release.** PyPI `mkdocs-macros-plugin` latest is 1.5.0, uploaded 2025-11-13T08:08:53Z; 1.5.0's only fix is
    package import outside the source dir (#278) (https://pypi.org/pypi/mkdocs-macros-plugin/json; MP/CHANGELOG.md#L7-L9).
