import jinja2


class Report(object):
    '''Generate a report page for the current time series data.'''
    def __init__(self):
        self._env = jinja2.Environment(
            loader=jinja2.PackageLoader(__package__, 'templates'),
            autoescape=jinja2.select_autoescape(['html'])
        )

    def generate_report(self) -> str:
        template = self._env.get_template('report.html')
        return template.render()
