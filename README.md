Sublime SPARQL Runner
=====================

A Sublime Text 2/3 plugin to run SPARQL queries inside Sublime.


Installing
----------

* ~~Use Sublime Package Control to install it;~~
* Clone this repository inside your packages directory (`~/Library/Application Support/Sublime Text 3/Packages/` on OSX);
* Add the following config to your Preferences.sublime-settings file:

```
{
  ...
  "sparql_endpoint": "http://dbpedia.org/sparql"
  ...
}
```

Using
-----

Simply run it from the command palette. SPARQL Runner will consider either the **selected text** or the **entire file** as the SPARQL query.

If you want to add a key binding, open your "Default.sublime-keymap" and add:

    [
      { "keys": ["super+shift+k"], "command": "run_sparql" }
    ]

