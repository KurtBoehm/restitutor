==============================
reStructuredText Test Document
==============================

:Author:    Example Author
:Date:      2026-03-19
:Version:   1.0
:Copyright: Public Domain

.. contents::
   :local:
   :depth: 2


Section 1: Basic Text
=====================

Paragraphs
----------

This is a normal paragraph. It has several sentences to demonstrate line
wrapping and spacing.  reStructuredText uses blank lines to separate
paragraphs.

This is a second paragraph, separated by a blank line from the first one.

Inline markup
-------------

*Emphasis* can be created with single asterisks, and **strong emphasis**
uses double asterisks.

You can also use ``inline literals`` for code or other text that should
not be interpreted.

Standalone hyperlinks are simple:

- https://www.python.org
- `Inline link to Python <https://www.python.org>`_

Anonymous references work too: `Python home page`__.

__ https://www.python.org


Section 2: Lists
================

Bullet lists
------------

- First bullet item
- Second bullet item with a second paragraph.

  This is the continuation paragraph, indented under the bullet.

- Third bullet item

  - Nested bullet item 1
  - Nested bullet item 2

Enumerated lists
----------------

1. First item
2. Second item
3. Third item

You can also use different markers:

a. Item "a"
b. Item "b"

or automatic numbering:

#. Auto-numbered item one
#. Auto-numbered item two

Definition lists
----------------

term 1
   Definition of term 1 goes here.

term 2
   Definition of term 2 has a longer explanation that spans multiple
   lines.  The definition continues with proper indentation.

   This is a second paragraph of the same definition.


Section 3: Literal Blocks and Code
==================================

Indented literal block
----------------------

A literal block is introduced by a double-colon at the end of the
preceding paragraph::

   This is a literal block.
   It preserves line breaks and indentation.
   No further markup is processed *here*.

Code block with directive
-------------------------

.. code-block:: python

   def fibonacci(n):
       """Return the first n Fibonacci numbers."""
       seq = [0, 1]
       for _ in range(n - 2):
           seq.append(seq[-1] + seq[-2])
       return seq

   if __name__ == "__main__":
       print(fibonacci(10))


Section 4: Tables
=================

Simple table
------------

+------------+-----------+-----------+
| Header 1   | Header 2  | Header 3  |
+============+===========+===========+
| Cell 1,1   | Cell 1,2  | Cell 1,3  |
+------------+-----------+-----------+
| Cell 2,1   | Cell 2,2  | Cell 2,3  |
+------------+-----------+-----------+

Grid table
----------

.. table:: Example Grid Table
   :widths: 20 20 20

   +-------------+-------------+-------------+
   | Column One  | Column Two  | Column Three|
   +=============+=============+=============+
   | Row 1       | Data        | More Data   |
   +-------------+-------------+-------------+
   | Row 2       | Data        | More Data   |
   +-------------+-------------+-------------+


Section 5: Admonitions
======================

.. note::

   This is a note admonition. It draws attention to additional
   information.

.. warning::

   This is a warning. Use it for important cautions.

.. tip::

   You can use tips for best practices and recommendations.

Custom titled admonition
------------------------

.. admonition:: Custom Title

   This is a custom admonition with a specific title.


Section 6: Images and Substitutions
===================================

Images
------

.. image:: https://www.python.org/static/community_logos/python-logo.png
   :alt: Python logo
   :width: 200
   :align: center

Substitution definitions
------------------------

Here is some text with a |substitution| inside.

.. |substitution| replace:: substituted **inline** text


Section 7: Footnotes and Citations
==================================

Footnotes
---------

This sentence has a footnote reference. [1]_

This sentence has an auto-numbered footnote reference. [#]_

.. [1] This is the text of footnote 1.
.. [#] This is an auto-numbered footnote.

Citations
---------

This is a citation reference [Ref01]_. You can list the citations
anywhere in the document.

.. [Ref01] Example reference in a bibliography style format.


Section 8: Fields and Option Lists
==================================

Field lists
-----------

:field name: field body
:another:    another field body

Option lists
------------

Command-line options can be documented like this:

-a, --all  Description of the --all option.

           It goes on and on, down from the door where it began…
-b FILE    Description of the -b option
           that takes a file argument.
-f <[path]file>  Option argument placeholders must start with
                 a letter or be wrapped in angle brackets.
-d <src dest>    Angle brackets are also required if an option
                 expects more than one argument.

Section 9: Directives and Roles
===============================

Literal include (example)
-------------------------

.. code-block:: rst

   .. note::

      This is an example of a directive *inside* a literal code block.

Named hyperlink targets
-----------------------

This is a link to the `Target Section`_ defined later.

Roles
-----

This is an example of using roles: :emphasis:`emphasized text`,
:strong:`strong text`, and :literal:`inline literal` via roles.


Section 10: Target Section
==========================

.. _Target Section:

This section exists to demonstrate internal linking.  The text here is
the target of an earlier hyperlink.
