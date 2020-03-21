import datetime
from typing import Dict

import bokeh.resources
import bokeh.embed
import jinja2

from case_rate import Plotter, TimeSeries


class HTMLReport(object):
    '''Generate a report page for the current time series data.'''
    def __init__(self):
        self._env = jinja2.Environment(
            loader=jinja2.PackageLoader(__package__, 'templates'),
            autoescape=jinja2.select_autoescape(['html'])
        )

    def generate_report(self, data: Dict[str, TimeSeries]) -> str:
        '''Generate an HTML report for the provided time series.

        Parameters
        ----------
        data : Dict[str, TimeSeries]
            a dictionary containing the time series data for each region

        Returns
        -------
        str
            the rendered HTML output
        '''
        plotter = Plotter(data)
        plots = {
            'total_confirmed': plotter.plot_confirmed(),
            'new_daily_cases': plotter.plot_new_cases(),
            'growth_factor': plotter.plot_growth_factor()
        }

        for plot in plots.values():
            plot.sizing_mode = 'stretch_width'
            plot.legend.location = 'top_left'

        resources = bokeh.resources.INLINE.render()
        script, div = bokeh.embed.components(plots)

        template = self._env.get_template('report.html')
        return template.render(date=datetime.date.today(),
                               bokeh_resources=resources,
                               bokeh_scripts=script,
                               bokeh_plots=div)
