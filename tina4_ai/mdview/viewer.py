"""HTML template builder for the Markdown viewer."""


def build_html(initial_path: str = "") -> str:
    """Build the viewer HTML page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mdview</title>
<link rel="stylesheet" href="/assets/markdown.css">
<link rel="stylesheet" href="/assets/highlight.css">
</head>
<body>
<div class="app">
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>mdview</h2>
    </div>
    <div class="sidebar-search">
      <input type="text" id="filter" placeholder="Filter files..." oninput="filterTree(this.value)">
    </div>
    <div class="file-tree" id="tree"></div>
  </div>
  <div class="content">
    <div class="content-header">
      <div class="breadcrumb" id="breadcrumb"></div>
    </div>
    <div class="content-body" id="body">
      <div class="empty-state" id="empty">
        <div class="icon">&#x1F4D6;</div>
        <div>Select a Markdown file from the sidebar</div>
      </div>
      <div class="markdown-body" id="rendered" style="display:none"></div>
    </div>
  </div>
</div>
<div class="reload-indicator" id="reload-indicator">Reloaded</div>

<script src="/assets/marked.min.js"></script>
<script src="/assets/highlight.min.js"></script>
<script>
(function() {{
  var currentPath = null;
  var eventSource = null;

  // Configure marked with highlight.js renderer
  var renderer = new marked.Renderer();
  renderer.code = function(token) {{
    var lang = (token.lang || '').trim();
    var text = token.text || '';
    var highlighted;
    if (lang && hljs.getLanguage(lang)) {{
      try {{ highlighted = hljs.highlight(text, {{language: lang}}).value; }}
      catch(e) {{ highlighted = hljs.highlightAuto(text).value; }}
    }} else {{
      try {{ highlighted = hljs.highlightAuto(text).value; }}
      catch(e) {{ highlighted = text; }}
    }}
    var langClass = lang ? ' class="language-' + lang + '"' : '';
    return '<pre><code' + langClass + '>' + highlighted + '</code></pre>';
  }};

  marked.setOptions({{
    gfm: true,
    breaks: false,
    renderer: renderer
  }});

  // Fetch helper
  function api(url) {{
    return fetch(url).then(function(r) {{ return r.json(); }}).catch(function(err) {{
      console.error('API error:', url, err);
      return {{entries: [], error: err.message}};
    }});
  }}

  // Load file tree
  function loadTree(path, container) {{
    api('/api/files?path=' + encodeURIComponent(path)).then(function(data) {{
      container.innerHTML = '';
      if (!data.entries) return;
      data.entries.forEach(function(entry) {{
        var node = document.createElement('div');
        node.className = 'tree-node';
        node.dataset.name = entry.name.toLowerCase();

        var label = document.createElement('div');
        label.className = 'tree-label';

        var icon = document.createElement('span');
        icon.className = 'tree-icon';

        var nameSpan = document.createElement('span');
        nameSpan.className = 'tree-name';
        nameSpan.textContent = entry.name;

        if (entry.type === 'dir') {{
          icon.textContent = '\\u25B6';
          label.appendChild(icon);
          label.appendChild(nameSpan);

          var badge = document.createElement('span');
          badge.style.cssText = 'margin-left:auto;font-size:11px;color:var(--text-muted)';
          badge.textContent = entry.md_count;
          label.appendChild(badge);

          var children = document.createElement('div');
          children.className = 'tree-children collapsed';

          var loaded = false;
          (function(lbl, ico, ch, entryPath) {{
            lbl.addEventListener('click', function(e) {{
              e.stopPropagation();
              e.preventDefault();
              if (!loaded) {{
                loadTree(entryPath, ch);
                loaded = true;
              }}
              ch.classList.toggle('collapsed');
              ico.textContent = ch.classList.contains('collapsed') ? '\\u25B6' : '\\u25BC';
            }});
          }})(label, icon, children, entry.path);

          node.appendChild(label);
          node.appendChild(children);
        }} else {{
          icon.textContent = '#';
          icon.style.cssText = 'font-size:11px;font-weight:bold;color:var(--primary)';
          label.appendChild(icon);
          label.appendChild(nameSpan);

          (function(lbl, entryPath) {{
            lbl.addEventListener('click', function(e) {{
              e.stopPropagation();
              e.preventDefault();
              document.querySelectorAll('.tree-label.active').forEach(function(l) {{
                l.classList.remove('active');
              }});
              lbl.classList.add('active');
              loadFile(entryPath);
            }});
          }})(label, entry.path);

          node.appendChild(label);
        }}

        container.appendChild(node);
      }});
    }});
  }}

  // Load and render a markdown file
  function loadFile(path) {{
    currentPath = path;
    api('/api/content?path=' + encodeURIComponent(path)).then(function(data) {{
      if (data.error) {{
        document.getElementById('rendered').innerHTML = '<p style="color:var(--red)">' + data.error + '</p>';
        document.getElementById('rendered').style.display = 'block';
        document.getElementById('empty').style.display = 'none';
        return;
      }}
      document.getElementById('empty').style.display = 'none';
      var rendered = document.getElementById('rendered');
      rendered.style.display = 'block';
      rendered.innerHTML = marked.parse(data.content);

      // Fix checkbox rendering for task lists
      rendered.querySelectorAll('li').forEach(function(li) {{
        var checkbox = li.querySelector('input[type="checkbox"]');
        if (checkbox) li.classList.add('task-list-item');
      }});

      // Update breadcrumb
      var parts = path.split('/');
      var bc = document.getElementById('breadcrumb');
      bc.innerHTML = '';
      parts.forEach(function(part, i) {{
        if (i > 0) {{
          var sep = document.createElement('span');
          sep.textContent = ' / ';
          bc.appendChild(sep);
        }}
        var span = document.createElement('span');
        span.textContent = part;
        if (i === parts.length - 1) span.className = 'current';
        bc.appendChild(span);
      }});

      // Update page title
      document.title = parts[parts.length - 1] + ' \\u2014 mdview';

      // Start watching for changes
      watchFile(path);
    }});
  }}

  // SSE file watcher
  function watchFile(path) {{
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/api/watch?path=' + encodeURIComponent(path));
    eventSource.onmessage = function(e) {{
      if (e.data === 'changed') {{
        loadFile(currentPath);
        var indicator = document.getElementById('reload-indicator');
        indicator.classList.add('visible');
        setTimeout(function() {{ indicator.classList.remove('visible'); }}, 1500);
      }}
    }};
  }}

  // Filter tree
  window.filterTree = function(query) {{
    var q = query.toLowerCase();
    document.querySelectorAll('#tree .tree-node').forEach(function(node) {{
      if (!q) {{
        node.style.display = '';
        return;
      }}
      var name = node.dataset.name || '';
      node.style.display = name.indexOf(q) >= 0 ? '' : 'none';
    }});
  }};

  // Listen for remote navigate events (singleton reuse)
  var navSource = new EventSource('/api/navigate-events');
  navSource.onmessage = function(e) {{
    try {{
      var msg = JSON.parse(e.data);
      if (msg.path) loadFile(msg.path);
    }} catch(err) {{}}
  }};

  // Initialize
  loadTree('.', document.getElementById('tree'));

  // Auto-open initial file if specified
  var initialPath = '{initial_path}';
  if (initialPath) {{
    loadFile(initialPath);
  }}
}})();
</script>
</body>
</html>"""
