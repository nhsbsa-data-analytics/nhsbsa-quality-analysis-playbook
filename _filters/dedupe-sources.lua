--[[
Render citations as numbered sources: grouped by the standard they come from, each clause
a link to the clause itself, and the accessible names in the markup.

Three problems with letting Pandoc do it.

First, duplicates. Two references to the same clause produce two notes with the same text and
different numbers, so the uncertainty page would list "GovS 010 section 6.5" three times out
of three entries. Sources here are merged on their rendered text, so a clause cited three
times on a page is one entry and carries the same number each time.

Second, the standard's name, over and over. A page resting on five clauses of GovS 010 listed
five lines each beginning "GovS 010", and the name was the first thing read every time while
the clause, which is the part that differs, sat at the end. Entries that share the opening
words are gathered under those words, written once, and each entry carries what is left: the
clause. Grouping is on the text itself rather than on a list of standards kept here, so a
standard cited for the first time groups without this file knowing anything about it. An entry
sharing its opening with nothing else keeps its full text and stands on its own.

The numbers are still the order of first citation, so the superscript a reader follows in the
prose is the number they land on, and `value` on each item holds it through the grouping.

Third, the accessible name. Pandoc writes <a href="#fn3"><sup>3</sup></a>, whose accessible
name is "3", and a back-link whose name is an arrow glyph. Both read as nothing on their own,
which is WCAG 2.2 success criterion 2.4.9 Link Purpose (Link Only), and this site claims
2.4.9. Doing it in JavaScript after load would work in a browser but not in the built file,
and an accessibility affordance that depends on a script running is weaker than one in the
markup. So every reference is written here, with aria-label carrying the source itself: a
screen reader announces "Source 3, GovS 010 section 5.2" rather than "3". The label carries
the whole citation, standard and clause together, because the grouping that saves a sighted
reader the repetition is not something a reader hearing one entry at a time can see.

The visible superscript is unchanged. aria-label sets the accessible name without altering
what is on the page.

There is deliberately no heading here. Quarto moves a section with id "footnotes" into the
page appendix and titles it from `language: section-title-footnotes` in _quarto.yml, which is
"Sources". A heading written here as well gave every citing page the word twice, once in
Quarto's appendix heading and once underneath it, and the same twice over in the PDF built
from these pages.
]]

local order = {}       -- plain text of each source, in the order each was first cited
local number = {}      -- plain text -> its number
local link = {}        -- plain text -> the URL it cites, where the source is a bare link
local markup = {}      -- plain text -> its rendered HTML, for anything that is not

local function esc(s)
  return s:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'):gsub('"', '&quot;')
end

local function trim(s)
  return (s:gsub('^%s*(.-)%s*$', '%1'))
end

--- The inlines of a note, flattened out of whatever blocks hold them.
local function inlines_of(note)
  local out = {}
  for _, blk in ipairs(note.content) do
    if blk.content then
      for _, inl in ipairs(blk.content) do out[#out + 1] = inl end
    end
  end
  return out
end

--- A source written as nothing but a link, which is what lets the clause be split off the
--- standard below. Returns the URL, or nil for anything else.
local function bare_link(inls)
  local found = nil
  for _, inl in ipairs(inls) do
    if inl.t == 'Link' then
      if found then return nil end
      found = inl.target
    elseif inl.t ~= 'Space' and inl.t ~= 'SoftBreak' then
      return nil
    end
  end
  return found
end

local function ref(n, text)
  return pandoc.RawInline('html', string.format(
    '<a href="#src-%d" class="footnote-ref" role="doc-noteref" aria-label="Source %d, %s">'
    .. '<sup>%d</sup></a>', n, n, esc(text), n))
end

function Note(note)
  local inls = inlines_of(note)
  local text = trim(pandoc.utils.stringify(note.content):gsub('%s+', ' '))
  if not number[text] then
    order[#order + 1] = text
    number[text] = #order
    local url = bare_link(inls)
    if url then
      link[text] = url
    else
      markup[text] = trim(pandoc.write(pandoc.Pandoc({pandoc.Plain(inls)}), 'html'))
    end
  end
  return ref(number[text], text)
end

local function words(s)
  local out = {}
  for w in s:gmatch('%S+') do out[#out + 1] = w end
  return out
end

--- How many opening words two sources share.
local function shared(a, b)
  local n = 0
  while a[n + 1] and b[n + 1] and a[n + 1] == b[n + 1] do n = n + 1 end
  return n
end

-- Words that name a part of a document rather than the document. Two sources citing
-- sections 2 and 6 of the same guidance share the word "section" as well as the title, and
-- a group taking every shared word left the standard labelled "..., section" above a list
-- reading "2" and "6". The clause word belongs with its number, so the label stops short of
-- it.
local CLAUSE = {section = true, sections = true, chapter = true, chapters = true,
                principle = true, principles = true, part = true, paragraph = true,
                clause = true, annex = true, appendix = true, table = true, figure = true,
                step = true, edition = true, page = true}

--- Pull the label back off any trailing word that names a part rather than a document.
local function label_end(parts, n)
  while n > 1 do
    local w = parts[n]:lower():gsub('[^%a]', '')
    if CLAUSE[w] then n = n - 1 else break end
  end
  return n
end

--- Gather the sources that open with the same words. Each group is the longest opening every
--- member of it shares, and a source sharing fewer than two opening words with anything else
--- is a group of one holding its whole text. Order of first citation is kept, both between
--- groups and inside one.
local function group(texts)
  local parts, taken, groups = {}, {}, {}
  for i, t in ipairs(texts) do parts[i] = words(t) end
  for i = 1, #texts do
    if not taken[i] then
      local members, common = {i}, nil
      for j = i + 1, #texts do
        if not taken[j] then
          local n = shared(parts[i], parts[j])
          -- Only against what the group already shares, so a third member cannot pull the
          -- opening longer than the first two have in common.
          if common then n = math.min(n, common) end
          n = label_end(parts[i], n)
          if n >= 2 then
            members[#members + 1] = j
            common = n
          end
        end
      end
      for _, m in ipairs(members) do taken[m] = true end
      if #members > 1 then
        local label = table.concat(parts[i], ' ', 1, common):gsub('[,;:]$', '')
        local items = {}
        for _, m in ipairs(members) do
          items[#items + 1] = {n = m, text = table.concat(parts[m], ' ', common + 1)}
        end
        groups[#groups + 1] = {label = label, items = items}
      else
        groups[#groups + 1] = {label = nil, items = {{n = i, text = texts[i]}}}
      end
    end
  end
  return groups
end

function Pandoc(doc)
  if #order == 0 then
    return doc
  end
  local out = {'<section id="footnotes" class="footnotes" role="doc-endnotes">',
               '<ul class="pb-sources">'}
  for _, g in ipairs(group(order)) do
    out[#out + 1] = '<li>'
    if g.label then
      out[#out + 1] = string.format('<span class="pb-source-standard">%s</span>', esc(g.label))
    end
    out[#out + 1] = '<ol class="pb-source-clauses">'
    for _, item in ipairs(g.items) do
      local whole = order[item.n]
      local body
      if link[whole] then
        -- The visible text is the clause alone, because the standard is written once above
        -- it. Read on its own, out of the list, "section 6.1" says nothing about where it
        -- goes, which is WCAG 2.4.9 Link Purpose (Link Only) at AAA. The accessible name
        -- carries the whole citation, and the visible words are inside it, which is what
        -- 2.5.3 Label in Name asks for.
        body = string.format('<a href="%s" aria-label="%s">%s</a>',
                             esc(link[whole]), esc(whole), esc(item.text))
      else
        body = markup[whole]
      end
      out[#out + 1] = string.format('<li id="src-%d" value="%d">%s</li>', item.n, item.n, body)
    end
    out[#out + 1] = '</ol>'
    out[#out + 1] = '</li>'
  end
  out[#out + 1] = '</ul>'
  out[#out + 1] = '</section>'
  doc.blocks:insert(pandoc.RawBlock('html', table.concat(out, '\n')))
  return doc
end
