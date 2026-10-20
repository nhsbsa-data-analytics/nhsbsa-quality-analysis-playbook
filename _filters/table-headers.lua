--[[
Name the headers of a table in the markup, so that a reader who cannot see the table can tell
which column and which row a cell belongs to (WCAG 2.2 success criterion 1.3.1).

Pandoc writes the header row as <th> in <thead> and every body cell as <td>, with no scope on
either. Two things are added here.

Column headers. Each cell of the header row gets scope="col". A <th> in a <thead> is a column
header anyway, so this repeats what the browser works out; it is there so that a table with
row headers states both directions the same way.

Row headers. Most tables in the playbook name each row in its first column: a role, a level, a
step, a document, a term. A sighted reader sees which row they are on. To everybody else it is a
cell like the rest, so a screen reader reads "Not done" or "Level 2" with no word for what it is
the answer to. Where every body cell in the first column is a short label, that column is made the
row header: Pandoc's row_head_columns writes those cells as <th> and scope="row" says what they
head.

A first column counts as labels when the header row names it, and for every row the cell is one
paragraph, not spanning rows or columns, that is either a short piece of text or link (30 words at
most) or a bold label followed by a line break and a description of it, which is how the scoring
tables write a dimension name above its question. That is a test on how the table is built, so
bold is not needed: the role checklists name their steps with plain links and the standards tables
name their clauses in plain text. A first column where a single cell is empty, spans, or runs on
as prose is left as it was, because a header column with one ordinary cell in it would be wrong for
that row. So is a table whose first header cell is empty, which is how a column of tick boxes
or a spacer is written.

Tables with merged cells are left alone: a row header that spans rows needs a different
treatment from this one.

A <th> is set in bold by the browser, so the stylesheet keeps a row header at the weight its
content has: bold where the cell was written bold, and plain where it was not. See the block at
the end of styles.css.

Where this runs matters. _quarto.yml registers it with `at: post-render`, after Quarto's own
filters. Run earlier, with the other user filters, the attributes were set and then lost for every
table that had a link in it: Quarto rebuilds those tables afterwards and does not carry cell
attributes over, so the playbook's tables of links came out without a scope and without a row
header while the tables of plain text had both.
]]

local function is_break(inline)
  return inline.t == 'LineBreak'
    or (inline.t == 'RawInline' and inline.format:match('html') ~= nil
        and inline.text:match('^<br%s*/?>$') ~= nil)
end

local function is_space(inline)
  return inline.t == 'Space' or inline.t == 'SoftBreak'
end

-- A bold label: Strong, or a link whose only content is Strong.
local function is_bold_label(inline)
  if inline.t == 'Strong' then
    return true
  end
  if inline.t == 'Link' then
    local content = inline.content
    return #content == 1 and content[1].t == 'Strong'
  end
  return false
end

-- The most words a label may run to. Past this a cell is a sentence, and a row header that reads a
-- sentence out before every cell beside it costs more than it tells.
local MAX_LABEL_WORDS = 30

local function word_count(text)
  local _, n = text:gsub('%S+', '')
  return n
end

-- One paragraph of inline content, in a cell that does not span.
local function single_paragraph(cell)
  if cell.row_span ~= 1 or cell.col_span ~= 1 then
    return nil
  end
  local blocks = cell.contents
  if #blocks ~= 1 or (blocks[1].t ~= 'Plain' and blocks[1].t ~= 'Para') then
    return nil
  end
  return blocks[1]
end

-- A bold label, then a line break and a description of it: the scoring tables write a dimension
-- name above its question this way, and the description can run long.
local function is_bold_label_cell(para)
  local inlines = para.content
  local i = 1
  while inlines[i] and is_space(inlines[i]) do
    i = i + 1
  end
  if not inlines[i] or not is_bold_label(inlines[i]) then
    return false
  end
  i = i + 1
  while inlines[i] and is_space(inlines[i]) do
    i = i + 1
  end
  return inlines[i] == nil or is_break(inlines[i])
end

-- Text that is not empty and is short enough to be a name.
local function is_short_label_cell(para)
  local words = word_count(pandoc.utils.stringify(para))
  return words > 0 and words <= MAX_LABEL_WORDS
end

local function is_label_cell(cell)
  local para = single_paragraph(cell)
  return para ~= nil and (is_bold_label_cell(para) or is_short_label_cell(para))
end

local function head_names_first_column(head)
  local row = head.rows[1]
  return row ~= nil and row.cells[1] ~= nil
    and pandoc.utils.stringify(row.cells[1].contents) ~= ''
end

local function first_column_is_labels(body)
  if #body.body == 0 then
    return false
  end
  for _, row in ipairs(body.body) do
    if #row.cells < 2 or not is_label_cell(row.cells[1]) then
      return false
    end
  end
  return true
end

function Table(tbl)
  for _, row in ipairs(tbl.head.rows) do
    for _, cell in ipairs(row.cells) do
      if cell.col_span == 1 then
        cell.attributes['scope'] = 'col'
      end
    end
  end
  for _, body in ipairs(tbl.bodies) do
    if body.row_head_columns == 0 and head_names_first_column(tbl.head)
       and first_column_is_labels(body) then
      body.row_head_columns = 1
      for _, row in ipairs(body.body) do
        row.cells[1].attributes['scope'] = 'row'
      end
    end
  end
  return tbl
end

-- A caption that only says again what the heading above it says. The accessible name of a table is its
-- caption, and every table has one, but where the table comes straight after a heading, such as "Who does
-- what in this phase" over "What each role does in Phase 2, design", a sighted reader gets the same words
-- twice. NHSBSA asked for the main parts not to be text heavy, so on a screen the second one is kept for
-- screen readers and not drawn. A table introduced by a sentence keeps its visible caption, because there
-- the caption is the only title it has. See main table.caption-under-heading in styles.css.
function Blocks(blocks)
  for i = 2, #blocks do
    if blocks[i].t == 'Table' and blocks[i - 1].t == 'Header' then
      blocks[i].attr.classes:insert('caption-under-heading')
    end
  end
  return blocks
end
