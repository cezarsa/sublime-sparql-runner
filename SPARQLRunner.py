try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from json import loads
import threading
import re

import sublime
import sublime_plugin


PROGRESS = ['-', '\\', '|', '/']
PREFIX_REGEX = re.compile(r'^\s*prefix\s+(.*?)\s+<(.*?)>\s*$', re.MULTILINE | re.IGNORECASE)
SETTINGS_FILE = 'SPARQLRunner.sublime-settings'


class QueryRunner(threading.Thread):
    def __init__(self, server, query, prefixes):
        self.server = server
        self.query = query
        self.result = None
        self.prefixes = prefixes
        super(QueryRunner, self).__init__()

    def parse_prefixes(self):
        return self.prefixes + PREFIX_REGEX.findall(self.query)

    def replace_prefix(self, value, prefixes):
        for prefix, url in prefixes:
            if value.find(url) == 0:
                return value.replace(url, prefix)
        return value

    def format_result(self, result):
        prefixes = self.parse_prefixes()
        bindings = result['results']['bindings']
        variables = result['head']['vars']
        number_of_variables = len(variables)
        max_column_size = [len(varname) for varname in variables]
        column_padding = 2

        for line in bindings:
            for i, varname in enumerate(variables):
                variable_entry = line.get(varname, {})
                variable_value = variable_entry.get('value', '')
                variable_entry['value'] = variable_value = self.replace_prefix(variable_value, prefixes)
                line[varname] = variable_entry
                if len(variable_value) > max_column_size[i]:
                    max_column_size[i] = len(variable_value)

        output = []
        for i, varname in enumerate(variables):
            output.append(varname + " " * (max_column_size[i] - len(varname)))
            if i < number_of_variables - 1:
                output.append(" " * column_padding)
        output.append("\n")

        for i, varname in enumerate(variables):
            output.append("-" * max_column_size[i])
            if i < number_of_variables - 1:
                output.append(" " * column_padding)
        output.append("\n\n")

        for line in bindings:
            for i, varname in enumerate(variables):
                value = line[varname]['value']
                output.append(value + " " * (max_column_size[i] - len(value)))
                if i < number_of_variables - 1:
                    output.append(" " * column_padding)
            output.append("\n")

        return "".join(output)

    def run(self):
        try:
            params = {
                'query': self.query,
                'format': 'json'
            }

            url = self.server + '?' + urlencode(params)
            response = urlopen(url)
            result_dict = loads(response.read().decode("utf-8"))
            self.result = self.format_result(result_dict)
        except Exception as e:
            err = '%s: Error %s running query' % (__name__, str(e))
            sublime.error_message(err)


class RunSparqlCommand(sublime_plugin.TextCommand):
    def get_selection(self):
        sels = self.view.sel()
        if len(sels) == 0:
            return None
        first_selection = self.view.substr(sels[0])
        if len(first_selection) == 0:
            return None

        return first_selection

    def get_full_text(self):
        return self.view.substr(sublime.Region(0, self.view.size()))

    def handle_thread(self, thread, i=0):
        if thread.is_alive():
            self.view.set_status('sparql_query', 'Running your query on %s [%s]' % (thread.server, PROGRESS[i]))
            sublime.set_timeout(lambda: self.handle_thread(thread, (i + 1) % len(PROGRESS)), 100)
            return

        self.view.erase_status('sparql_query')

        if not thread.result:
            return

        sublime.status_message('Query successfully run on %s' % thread.server)
        new_view = self.view.window().new_file()
        new_view.settings().set('word_wrap', False)
        new_view.set_name("SPARQL Query Results")
        try:
            # Sublime Text 2 way
            edit = new_view.begin_edit()
            new_view.insert(edit, 0, thread.result)
            new_view.end_edit(edit)
        except:
            new_view.run_command('append', {
                'characters': thread.result
            })
        new_view.run_command("goto_line", {"line": 1})
        new_view.set_scratch(True)
        new_view.set_read_only(True)

    def run(self, edit):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        server = self.settings.get('current_endpoint', None)
        if not server:
            sublime.error_message("You should add/select an endpoint using 'SPARQL: Select endpoint' command.")
            return

        query = self.get_selection() or self.get_full_text()
        prefixes = self.settings.get('prefixes', [])
        query_thread = QueryRunner(server, query, prefixes)
        query_thread.start()
        self.handle_thread(query_thread)


class SelectSparqlEndpointCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        self.gather_endpoints()
        self.window.show_quick_panel(self.endpoints, self.on_panel_select_done)

    def gather_endpoints(self):
        self.current_endpoint = self.settings.get('current_endpoint', None)
        self.sparql_endpoints = self.settings.get('sparql_endpoints', [])

        self.endpoints = [
            ['Add new endpoint...', ''],
        ]

        for endpoint in self.sparql_endpoints:
            url = endpoint['url']
            name = endpoint['name']
            if url == self.current_endpoint:
                name = "*%s" % name
            self.endpoints.append([name, url])

    def add_endpoint(self, name, url):
        self.settings.set('sparql_endpoints', self.sparql_endpoints + [
            {
                'name': name,
                'url': url
            }
        ])
        self.set_as_current(url)

    def set_as_current(self, url):
        self.settings.set('current_endpoint', url)
        sublime.save_settings(SETTINGS_FILE)

    def on_panel_select_done(self, selected):
        if selected < 0:
            return

        if selected == 0:
            self.window.show_input_panel('Endpoint name', '', self.on_name_done, self.on_change, self.on_cancel)
            return
        self.set_as_current(self.endpoints[selected][1])

    def on_name_done(self, name):
        self.name = name
        self.window.show_input_panel('Endpoint url', '', self.on_url_done, self.on_change, self.on_cancel)

    def on_url_done(self, url):
        self.add_endpoint(self.name, url)

    def on_change(self, name):
        pass

    def on_cancel(self):
        pass
