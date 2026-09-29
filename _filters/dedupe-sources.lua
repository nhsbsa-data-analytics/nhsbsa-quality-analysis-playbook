--[[
Render citations as numbered sources, with the accessible names in the markup.

Two problems with letting Pandoc do it.

First, duplicates. Two references to the same clause produce two notes with the same text and
different numbers, so section 7 would list "GovS 010 section 6.5" three times out of three
entries. Sources here are merged on their rendered text, so a clause cited three times on a
page is one entry and carries the same number each time.

Second, the accessible name. Pandoc writes <a href="#fn3"><sup>3</sup></a>, whose accessible
name is "3", and a back-link whose name is an arrow glyph. Both read as nothing on their own,
which is WCAG 2.2 success criterion 2.4.9 Link Purpose (Link Only), and this site claims
2.4.9. Doing it in JavaScript after load would work in a browser but not in the built file,
and an accessibility affordance that depends on a script running is weaker than one in the
markup. So every reference is written here, with aria-label carrying the source itself: a
screen reader announces "Source 3, GovS 010 section 5.2" rather than "3".

The visible superscript is unchanged. aria-label sets the accessible name without altering
what is on the page.
]]

local order = {}       -- source text, in the order each was first cited
local number = {}      -- source text -> its number

local function esc(s)
  return s:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'):gsub('"', '&quot;')
end

local function ref(n, text)
  return pandoc.RawInline('html', string.format(
    '<a href="#src-%d" class="footnote-ref" role="doc-noteref" aria-label="Source %d, %s">'
    .. '<sup>%d</sup></a>', n, n, esc(text), n))
end

function Note(note)
  local text = pandoc.utils.stringify(note.content):gsub('%s+', ' '):gsub('^%s*(.-)%s*$', '%1')
  if not number[text] then
    order[#order + 1] = text
    number[text] = #order
  end
  return ref(number[text], text)
end

function Pandoc(doc)
  if #order == 0 then
    return doc
  end
  local items = {}
  for i, text in ipairs(order) do
    items[#items + 1] = string.format('<li id="src-%d">%s</li>', i, esc(text))
  end
  doc.blocks:insert(pandoc.RawBlock('html', table.concat({
    '<section id="footnotes" class="footnotes" role="doc-endnotes">',
    '<h2>Sources</h2>',
    '<ol>', table.concat(items, '\n'), '</ol>',
    '</section>',
  }, '\n')))
  return doc
end
