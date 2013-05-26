Sublime SPARQL Runner
=====================

A Sublime Text 2/3 plugin to run SPARQL queries inside Sublime.


Installing
----------

* Use Sublime Package Control to install it (or clone it inside your Packages dir);


Using
-----

* To add a new endpoint or select the current one open the command palette and choose `SPARQL: Select endpoint`
* To run a query choose `SPARQL: Run query`. SPARQL Runner will run the query against the current endpoint. It will consider either the **selected text** or the **entire file** as the SPARQL query.

If you want to add a key binding to run queries, open your "Default.sublime-keymap" and add:

    [
      { "keys": ["super+shift+k"], "command": "run_sparql" }
    ]


* Further config options can be found in Preferences -> Package Settings -> SPARQL Runner -> Settings
