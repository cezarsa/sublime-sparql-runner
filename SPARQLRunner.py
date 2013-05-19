from urllib.parse import urlencode
from urllib.request import urlopen
from json import loads
import threading

import sublime
import sublime_plugin


PROGRESS = ['-', '\\', '|', '/']


class QueryRunner(threading.Thread):
    def __init__(self, server, query):
        self.server = server
        self.query = query
        super(QueryRunner, self).__init__(self)

    def run(self):
        try:
            params = {
                'query': self.query,
                'format': 'json'
            }

            url = self.server + '?' + urlencode(params)
            response = urlopen(url)
            self.result = loads(response.read().decode("utf-8"))
        except Exception as e:
            err = '%s: Error %s running query' % (__name__, str(e))
            sublime.error_message(err)
            self.result = None


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

        if not thread.result:
            return

        sublime.status_message('Query successfully run on %s' % thread.server)
        self.view.erase_status('sparql_query')
        new_view = self.view.window().new_file()
        new_view.run_command('append', {
            'characters': self.format_result(thread.result)
        })
        new_view.set_scratch(True)
        new_view.set_read_only(True)
        new_view.set_name("SPARQL Query Results")

    def format_result(self, result):
        bindings = result['results']['bindings']
        variables = result['head']['vars']
        max_column_size = [len(varname) for varname in variables]
        column_padding = 2

        for line in bindings:
            for i, varname in enumerate(variables):
                value = line[varname]['value']
                if len(value) > max_column_size[i]:
                    max_column_size[i] = len(value)

        output = []
        for i, varname in enumerate(variables):
            output.append(varname + " " * (max_column_size[i] - len(varname) + column_padding))
        output.append("\n")

        for i, varname in enumerate(variables):
            output.append("-" * max_column_size[i] + " " * column_padding)
        output.append("\n\n")

        for line in bindings:
            for i, varname in enumerate(variables):
                value = line[varname]['value']
                output.append(value + " " * (max_column_size[i] - len(value) + column_padding))
            output.append("\n")

        return "".join(output)

    def run(self, edit):
        settings = self.view.settings()
        server = settings.get('sparql_endpoint')
        if (not server) or len(server) == 0:
            sublime.error_message("You should add 'sparql_endpoint' setting to your preferences file.")
            return

        query = self.get_selection() or self.get_full_text()
        query_thread = QueryRunner(server, query)
        query_thread.start()
        self.handle_thread(query_thread)
