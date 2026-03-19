# Restitutor

An opinionated formatter for reStructuredText (reST) files.

Restitutor parses `.rst` files with `docutils`, reconstructs them from the AST, and writes them back in a normalized, consistent style. It aims to be safe, predictable, and friendly to tooling and code review.

## Features

- Normalizes general reStructuredText structure:
  - Headings with consistent adornments
  - Paragraph spacing
  - Bullet and enumerated lists
- Preserves and re-emits several Sphinx-style constructs:
  - `.. toctree::`
  - `.. currentmodule::`
  - Cross-reference roles like `:func:`, `:class:`, `:mod:`, `:ref:`, `:term:`, etc.
  - Breathe directives such as `.. doxygenclass::`, `.. doxygenfunction::`, etc.
- Enhanced table handling:
  - Grid tables are reflowed with consistent borders and spacing
  - `.. list-table::` tables are preserved as list-table directives
  - Optional preservation of blank-line spacing between list-table rows
- Handles inline markup:
  - `*emphasis*`, `**strong**`, `inline literals`
  - Hyperlinks and cross-references
- Renders:
  - Literal/code blocks (`::` and `.. code:: lang`)
  - Images (`.. image::`)
  - Generic admonitions (`.. admonition:: Title`)
  - Line blocks (`| line`)

The formatter currently targets a subset of docutils/Sphinx nodes.
If it encounters unknown or unsupported nodes, it fails loudly rather than silently corrupting the output.

## Installation

Restitutor requires Python 3.12+ and is available on PyPI:

```bash
pip install restitutor
```

## Usage

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

## Examples

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

## How it works

At a high level:

1. `docutils.core.publish_doctree()` parses the input `.rst` into a `nodes.document` AST.
2. Restitutor registers a set of custom directives and roles so that Sphinx-like constructs are captured as specific node types:
   - `TocTreeNode` for `.. toctree::`
   - `CurrentModuleNode` for `.. currentmodule::`
   - `XRefNode` for cross-reference roles
   - `MarkingListTable` wraps the `list-table` directive and annotates the resulting table with metadata to reconstruct it.
   - Several `Doxy*Node` types for Breathe directives
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
- Enumerations preserve style where possible (`1.`, `a.`, `A.`, Roman numerals, etc.)

### Tables

- Grid tables are rendered with full borders and aligned columns.
- `.. list-table::` tables are preserved as `.. list-table::`; options like `:header-rows:` and `:widths:` are preserved.
- Without `--clean`, Restitutor preserves the number of blank lines between top-level list-table rows.

## Caveats and limitations

- Only a subset of docutils/Sphinx nodes is supported. Unsupported nodes raise `RuntimeError` during formatting.
- There is no test suite yet.

## API (internal)

The project is currently focused on the CLI. The main internal entry points are:

- `ast_to_rst(node: nodes.Node, ctx: FmtCtx) -> str`  
  Convert a docutils node (usually a whole `document`) back into reStructuredText.

- `FmtCtx`  
  A dataclass controlling indentation and list-formatting context.

These APIs are internal and may change without notice.

## Contributing

Issues and pull requests are welcome at:

- Issues: <https://github.com/KurtBoehm/restitutor/issues>
- Repository: <https://github.com/KurtBoehm/restitutor>

If you encounter

- crashes on particular `.rst` input,
- incorrect rendering of supported constructs,
- or want support for additional Sphinx/directive features,

please open an issue with a minimal reproducer (input `.rst` and observed vs expected output).

## Licence

Restitutor is licensed under the Mozilla Public Licence 2.0, provided in [`License`](https://github.com/KurtBoehm/restitutor/blob/main/License).
