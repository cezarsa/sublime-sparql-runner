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
DEFAULT_PREFIXES = [
    ('rdf:',  'http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    ('rdfs:', 'http://www.w3.org/2000/01/rdf-schema#'),
    ('xsd:',  'http://www.w3.org/2001/XMLSchema#'),
    ('fn:',   'http://www.w3.org/2005/xpath-functions#')
]

PREFIX_REGEX = re.compile(r'^\s*prefix\s+(.*?)\s+<(.*?)>\s*$', re.MULTILINE | re.IGNORECASE)


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

        prefixes = self.parse_prefixes(thread.query)
        sublime.status_message('Query successfully run on %s' % thread.server)
        self.view.erase_status('sparql_query')
        new_view = self.view.window().new_file()
        new_view.run_command('append', {
            'characters': self.format_result(thread.result, prefixes)
        })
        new_view.set_scratch(True)
        new_view.set_read_only(True)
        new_view.set_name("SPARQL Query Results")

    def parse_prefixes(self, query):
        return PREFIX_REGEX.findall(query)

    def format_result(self, result, prefixes):
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
                value = self.replace_prefix(line[varname]['value'], prefixes)
                output.append(value + " " * (max_column_size[i] - len(value) + column_padding))
            output.append("\n")

        return "".join(output)

    def replace_prefix(self, value, prefixes):
        for prefix, url in DEFAULT_PREFIXES + prefixes:
            if value.find(url) == 0:
                return value.replace(url, prefix)
        return value

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
