from collections import OrderedDict
import datetime
from typing import Dict, Optional, NamedTuple

import bokeh.embed
import bokeh.plotting
import bokeh.resources
import jinja2
import numpy as np

from . import VERSION
from .plotting import Plotter
from .timeseries import TimeSeries


class SourceInfo(NamedTuple):
    '''Used to specify information about where the data came from.'''
    description: str
    url: str


class HTMLReport(object):
    '''Generate a report page for the current time series data.'''
    def __init__(self, sources: Optional[Dict[str, SourceInfo]] = None):
        '''
        Parameters
        ----------
        sources : dict of :class:`SourceInfo`
            dictionary of tuples with available data sources
        '''
        self._sources = sources.copy()
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
            'growth_factor': plotter.plot_growth_factor(),
            'log_slope': plotter.plot_log_slope()
        }

        for plot in plots.values():
            plot.sizing_mode = 'stretch_width'
            plot.legend.location = 'top_left'

        resources = bokeh.resources.CDN.render()
        script, div = bokeh.embed.components(plots)

        template = self._env.get_template('report.html')
        return template.render(date=datetime.date.today(),
                               sources=self._sources,
                               regions=list(data.keys()),
                               bokeh_resources=resources,
                               bokeh_scripts=script,
                               bokeh_plots=div)

    def generate_overview(self, data: Dict[str, TimeSeries]) -> str:
        '''Generates an HTML overview report for the provided time series.

        Parameters
        ----------
        data : Dict[str, TimeSeries]
            a dictionary containing the time series data for each region

        Returns
        -------
        overview : str
            the overview page
        details : Dict[str, str]
            the detail pages, keyed by the expected file name
        '''
        ordering = sorted(list(data.keys()))

        # Generate the top-level view.
        plots = OrderedDict()
        stats = {}
        for region in ordering:
            plotter = Plotter({region: data[region]})

            gf = np.squeeze(data[region].growth_factor()[-1, :])
            multiplier = np.power(10, data[region].log_slope()[-1, :])
            multiplier = np.squeeze(multiplier)

            info = {}
            info['link'] = f'details-{region}.html'
            info['total_confirmed'] = data[region].confirmed[-1]
            info['new_cases'] = data[region].daily_new_cases()[-1]
            info['multiplier'] = {
                'estimate': multiplier[0],
                'lower': multiplier[1],
                'upper': multiplier[2]
            }
            info['growth_factor'] = {
                'estimate': gf[0],
                'lower': gf[1],
                'upper': gf[2]
            }

            stats[region] = info

            plots[region] = plotter.plot_new_cases()
            plots[region].sizing_mode = 'scale_both'
            plots[region].aspect_ratio = 4 / 3
            plots[region].legend.visible = False

        resources = bokeh.resources.CDN.render()
        script, div = bokeh.embed.components(plots)

        unique_sources = set(info for info in self._sources.values())
        unique_sources = sorted(unique_sources, key=lambda x: x.description)

        template = self._env.get_template('overview.html')
        overview = template.render(date=datetime.date.today(),
                                   unique_sources=unique_sources,
                                   new_cases=div,
                                   stats=stats,
                                   bokeh_resources=resources,
                                   bokeh_scripts=script,
                                   VERSION=VERSION)

        details = {
            stats[region]['link']: self.generate_report({region: timeseries})
            for region, timeseries in data.items()
        }

        return overview, details
