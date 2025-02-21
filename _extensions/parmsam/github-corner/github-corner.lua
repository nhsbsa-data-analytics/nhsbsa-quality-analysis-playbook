local function ensure_html_deps()
    quarto.doc.add_html_dependency({
        name = 'quarto-corner',
        version = '1.0.0',
        scripts = {
            "github-corner.js",
        }
    })
end

local function html_corner(options)
    local script = string.format(
        [[<script>
            document.addEventListener("DOMContentLoaded", function () {
                const githubCorner = document.querySelector('#github-corner-wrapper .github-corner');
                githubCorner.setAttribute('href', '%s');
                githubCorner.querySelector('svg').style.fill = '%s';
                githubCorner.querySelector('svg').style.color = '%s';
                githubCorner.querySelector('svg').setAttribute('width', '%d');
                githubCorner.querySelector('svg').setAttribute('height', '%d');
                githubCorner.style.position = 'absolute';
                githubCorner.style.top = '0';
                if ('%s' === 'right') {
                    githubCorner.style.right = '0';
                } else {
                    githubCorner.style.left = '0';
                    githubCorner.style.transform = 'scaleX(-1)';
                }
            });
        </script>]],
        options.url,
        options.backgroundColor,
        options.logoColor,
        options.size,
        options.size,
        options.position
    )
    quarto.doc.include_text("after-body", script)
end

function Pandoc(doc)
  if quarto.doc.is_format("html:js") then
      ensure_html_deps()

    options = {
        url = "https://github.com",
        backgroundColor = "#151513",
        logoColor = "#fff",
        position = "right",
        size = 80
        }
    if doc.meta["github-corner"] then
      meta_options = doc.meta["github-corner"]
    end
    
    if meta_options["url"] then 
        options["url"] = pandoc.utils.stringify(meta_options["url"])
    end
    if meta_options["background-color"] then
        options["backgroundColor"] = pandoc.utils.stringify(meta_options["background-color"])
    end
    if meta_options["logo-color"] then
        options["logoColor"] = pandoc.utils.stringify(meta_options["logo-color"])
    end
    if meta_options["position"] then
        options["position"] = pandoc.utils.stringify(meta_options["position"])
    end
    if meta_options["size"] then
        options["size"] = tonumber(pandoc.utils.stringify(meta_options["size"]))
    end

    html_corner(options)
  end
end
