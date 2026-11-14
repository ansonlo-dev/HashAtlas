-- Pandoc Lua filter for the LaTeX technical report. It changes layout only, never wording:
--   * removes the manual "N. " prefix from level-1 headings (LaTeX numbers sections itself);
--   * renders inline code (file paths, field names) as breakable monospace text;
--   * sizes table columns from their content and sets header cells in bold;
--   * wraps tables in a small sans-serif environment.

local function latex_escape(s)
  local map = {
    ["\\"] = "\\textbackslash{}", ["{"] = "\\{", ["}"] = "\\}", ["$"] = "\\$", ["&"] = "\\&",
    ["#"] = "\\#", ["%"] = "\\%", ["~"] = "\\textasciitilde{}", ["^"] = "\\textasciicircum{}",
    ["_"] = "\\_", ["<"] = "\\textless{}", [">"] = "\\textgreater{}", ["|"] = "\\textbar{}",
  }
  return (s:gsub("[\\{}$&#%%~^_<>|]", map))
end

-- Allow line breaks after path separators and underscores in long identifiers.
local function breakable(s)
  local out = {}
  for ch in s:gmatch(".") do
    local e = latex_escape(ch)
    if ch == "/" or ch == "_" or ch == "." or ch == "," or ch == "=" then
      e = e .. "\\allowbreak{}"
    end
    table.insert(out, e)
  end
  return table.concat(out)
end

function Header(h)
  if h.level == 1 then
    local first = h.content[1]
    if first and first.t == "Str" and first.text:match("^%d+%.$") then
      -- drop the number token and the following space
      h.content:remove(1)
      if h.content[1] and h.content[1].t == "Space" then h.content:remove(1) end
    end
  end
  return h
end

function Code(c)
  return pandoc.RawInline("latex", "\\code{" .. breakable(c.text) .. "}")
end

local function cell_text(cell)
  return pandoc.utils.stringify(pandoc.Blocks(cell.contents))
end

local function longest_word(s)
  local m = 0
  for w in s:gmatch("%S+") do m = math.max(m, #w) end
  return m
end

function Table(tbl)
  local ncols = #tbl.colspecs
  -- Column sizing in "character" units for \small sans text across the text block (~100 characters).
  local LINE = 100
  local env = "reporttable"
  local minw, wt = {}, {}
  for i = 1, ncols do minw[i] = 0; wt[i] = 0 end
  local nrows = 0
  local function visit(rows)
    for _, row in ipairs(rows) do
      nrows = nrows + 1
      for i, cell in ipairs(row.cells) do
        local t = cell_text(cell)
        minw[i] = math.max(minw[i], longest_word(t) * 1.3 + 2)   -- never split a word; + padding
        wt[i] = math.max(wt[i], math.min(#t, 60))                  -- desirable width
      end
    end
  end
  visit(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do visit(body.body) end
  local total = 0
  for i = 1, ncols do total = total + math.max(wt[i], minw[i]) end
  if total > 0.7 * LINE then
    -- Wide table: guarantee each column its longest word, share the rest by desirable width.
    local summin = 0
    for i = 1, ncols do summin = summin + minw[i] end
    if summin > 0.92 * LINE then
      -- Very wide table: use a smaller size (more characters fit on a line) rather than split words.
      env, LINE = "reporttablesmall", 118
    end
    local frac = {}
    if summin >= LINE then
      for i = 1, ncols do frac[i] = minw[i] / summin end
    else
      local extra, sumextra = {}, 0
      for i = 1, ncols do extra[i] = math.max(wt[i] - minw[i], 0); sumextra = sumextra + extra[i] end
      for i = 1, ncols do
        local share = sumextra > 0 and extra[i] / sumextra or 1 / ncols
        frac[i] = (minw[i] + share * (LINE - summin)) / LINE
      end
    end
    for i = 1, ncols do tbl.colspecs[i] = { tbl.colspecs[i][1], frac[i] } end
  else
    for i = 1, ncols do tbl.colspecs[i] = { tbl.colspecs[i][1], pandoc.ColWidthDefault } end
  end
  -- Bold header cells.
  for _, row in ipairs(tbl.head.rows) do
    for _, cell in ipairs(row.cells) do
      cell.contents = cell.contents:walk({ Plain = function(p) return pandoc.Plain({ pandoc.Strong(p.content) }) end })
    end
  end
  -- Keep short tables on one page (long ones may still break, with repeated headers).
  local lines = math.min(nrows * 1.6 + 3, 30)
  return {
    pandoc.RawBlock("latex", string.format("\\Needspace{%.1f\\baselineskip}\\begin{%s}", lines, env)),
    tbl,
    pandoc.RawBlock("latex", "\\end{" .. env .. "}"),
  }
end
