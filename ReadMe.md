# 🧾 Restitutor

[![PyPI - Version](https://img.shields.io/pypi/v/restitutor?logo=pypi&label=PyPI)](https://pypi.org/project/restitutor/)
[![Test Workflow Status](https://img.shields.io/github/actions/workflow/status/KurtBoehm/restitutor/test.yml?logo=github&label=Tests)](https://github.com/KurtBoehm/restitutor/actions/workflows/test.yml)

An opinionated formatter for reStructuredText (reST) files.

Restitutor parses `.rst` files with `docutils`, reconstructs them from the AST, and writes them back in a normalized, consistent style. It aims to be safe, predictable, and friendly to tooling and code review.

## ✨ Features

- Normalizes general reStructuredText structure:
  - Headings with consistent adornments
  - Paragraph spacing
  - Bullet and enumerated lists
  - Definition lists and field lists
  - Option lists (CLI style options and descriptions)
- Preserves and re-emits several Sphinx-style constructs:
  - `.. toctree::`
  - `.. currentmodule::`
  - Cross-reference roles like `:func:`, `:class:`, `:mod:`, `:ref:`, `:term:`, `:envvar:`, etc.
  - Generic text roles like `:emphasis:`, `:literal:`, `:strong:`
  - Breathe directives such as `.. doxygenclass::`, `.. doxygenfunction::`, etc.
  - C++ domain directives such as `.. cpp:function::`, `.. cpp:class::`, etc.
- Enhanced table handling:
  - Grid tables are reflowed with consistent borders and spacing
  - `.. list-table::` tables are preserved as list-table directives
  - Optional preservation of blank-line spacing between list-table rows
  - `.. table::` directives are reconstructed around grid tables, with `:widths:` preserved
- Handles inline markup:
  - `*emphasis*`, `**strong**`, ``inline literals``
  - Hyperlinks and cross-references (including anonymous targets)
  - Substitutions (definitions and uses: `.. |name| replace::` and `|name|`)
  - Inline maths via `:math:`
- Renders block-level constructs:
  - Literal/code blocks (both `::` and `.. code:: lang` / `.. code-block:: lang`)
  - Images (`.. image::`)
  - Generic admonitions (`.. admonition:: Title`)
  - Standard admonitions (`.. note::`, `.. warning::`, `.. tip::`, etc.)
  - Maths blocks (`.. math::`).
  - Line blocks (`| line`)
  - Footnotes and citations (`.. [#]_`, `.. [label]` and corresponding references)

The formatter currently targets a subset of docutils/Sphinx nodes.
If it encounters unknown or unsupported nodes, it fails loudly rather than silently corrupting the output.

## 📦 Installation

Restitutor requires Python 3.12+ and is available on PyPI:

```bash
pip install restitutor
```

## 🧑‍💻 Usage

The package installs a console script `restitute` with the following interface:

```text
restitute [-i|--in-place] [-c|--clean] RST [RST ...]
```

- `RST`  
  One or more paths to `.rst` files to process.

- `-i, --in-place`  
  Rewrite the given `.rst` files in-place instead of printing to `stdout`.

- `-c, --clean`  
  Normalize newlines.

  By default, Restitutor preserves blank-line counts between rows in `.. list-table::` tables.
  With `--clean`, extra blank lines are removed for a cleaner, but less faithful, representation.

## 📚 Examples

```bash
# Format one or more `.rst` files and print to stdout
restitute docs/index.rst
restitute docs/index.rst docs/usage.rst

# Rewrite files in place
restitute -i docs/index.rst
restitute --in-place docs/*.rst

# Normalize newlines between `list-table` rows
restitute -i --clean docs/*.rst
```

## 🧠 How it works

At a high level:

1. `docutils.core.publish_doctree()` parses the input `.rst` into a `nodes.document` AST.
2. Restitutor registers a set of custom directives and roles so that Sphinx-like constructs are captured as specific node types:
   - `TocTreeNode` for `.. toctree::`
   - `CurrentModuleNode` for `.. currentmodule::`
   - `XRefNode` for cross-reference roles
   - `MarkingListTable` wraps the `list-table` directive and annotates the resulting table with metadata to reconstruct it
   - `MarkingTable` wraps `.. table::` and preserves title/width information
   - Several `Doxy*Node` types for Breathe/Doxygen directives
   - `CppNode` for C++ domain directives like `.. cpp:function::`
3. `ast_to_rst()` recursively walks the doctree and emits reStructuredText, guided by a formatting context (`FmtCtx`) that tracks indentation and list prefixes.
4. The resulting text is either printed or written back to the original file.

### Headings

Headings use a fixed adornment sequence:

```python
ADORNMENTS = ["#", "*", "=", "-", "^"]
```

Level 0 and 1 use overline/underline; deeper levels use underline only:

```rst
#############
 Top Heading
#############

************
 Subheading
************

Title
=====

Subtitle
--------

Minor
^^^^^
```

### Lists

Bullet and enumerated lists are normalized to a consistent style:

- Bullet lists use `-`
- Enumerations preserve style where possible (`1.`, `a.`, `A.`, Roman numerals, `#.` auto-numbered, etc.)
- Definition lists and field lists are emitted in canonical reST form
- Option lists keep CLI options and descriptions tightly aligned

### Tables

- Grid tables are rendered with full borders and aligned columns.
- `.. list-table::` tables are preserved as `.. list-table::`; options like `:header-rows:` and `:widths:` are preserved.
- `.. table::` directives are reconstructed around grid tables, including optional `:widths:`.
- Without `--clean`, Restitutor preserves the number of blank lines between top-level list-table rows.

## ⚠️ Caveats and Limitations

- Only a subset of docutils/Sphinx nodes is supported. Unsupported nodes raise `RuntimeError` during formatting.
- There is no test suite yet.

## 🧩 API (Internal)

The project is currently focused on the CLI. The main internal entry points are:

- `format_rst(rst_source: str, *, clean: bool = True) -> str`  
  Parse and re-emit a full reST document from a string.
- `ast_to_rst(buf: Buffer, node: nodes.Node, ctx: FmtCtx, preproc: PreprocessInfo) -> None`  
  Convert a docutils node (usually a whole `document`) back into reStructuredText, appending to a buffer.
- `FmtCtx`  
  A dataclass controlling indentation and list-formatting context.

These APIs are internal and may change without notice.

## 🤝 Contributing

Issues and pull requests are welcome at:

- Issues: <https://github.com/KurtBoehm/restitutor/issues>
- Repository: <https://github.com/KurtBoehm/restitutor>

If you encounter

- crashes on particular `.rst` input,
- incorrect rendering of supported constructs,
- or want support for additional Sphinx/directive features,

please open an issue with a minimal reproducer (input `.rst` and observed vs expected output).

## 📜 Licence

Restitutor is licensed under the Mozilla Public Licence 2.0, provided in [`License`](https://github.com/KurtBoehm/restitutor/blob/main/License).
