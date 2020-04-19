from collections import OrderedDict
import datetime
from typing import Dict, List, Optional, NamedTuple

import bokeh.embed
import bokeh.plotting
import bokeh.resources
import jinja2

from . import VERSION, analysis
from ._types import Datum
from .plotting import Plotter
from .analysis import TimeSeries


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

    def generate_report(self, data: Dict[str, List[Datum]],
                        min_confirmed: int = 0) -> str:
        '''Generate an HTML report for the provided time series.

        Parameters
        ----------
        data : dictionary of :class:`Cases` or :class:`CaseTesting` lists
            a dictionary of case reports, keyed by the region names
        min_confirmed : int, optional
            ignore any data where the number of confirmed cases is less than
            this value; default is '0' or disabled

        Returns
        -------
        str
            the rendered HTML output
        '''
        sources = {region: self._sources[region] for region in data.keys()}

        series = []
        for region, reports in data.items():
            ts = TimeSeries(reports, 'confirmed', min_confirmed)
            ts.label = region
            series.append(ts)

        plotter = Plotter(series)
        plots = {
            'total_confirmed': plotter.plot_series('Confirmed Cases', 'Cases'),
            'new_daily_cases': plotter.plot_derivative('Daily Cases', 'Cases'),
            'growth_factor': plotter.plot_growth_factor('Estimated Growth Factor'),  # noqa: E501
            'log_slope': plotter.plot_percent_change('Day-over-day Change')
        }

        for plot in plots.values():
            plot.sizing_mode = 'stretch_width'
            plot.legend.location = 'top_left'

        resources = bokeh.resources.CDN.render()
        script, div = bokeh.embed.components(plots)

        template = self._env.get_template('report.html')
        return template.render(date=datetime.date.today(),
                               sources=sources,
                               regions=list(data.keys()),
                               bokeh_resources=resources,
                               bokeh_scripts=script,
                               bokeh_plots=div)

    def generate_overview(self, data: Dict[str, List[Datum]],
                          min_confirmed: int = 0) -> str:
        '''Generates an HTML overview report for the provided time series.

        Parameters
        ----------
        data : Dict[str, TimeSeries]
            a dictionary containing the time series data for each region
        min_confirmed : int, optional
            ignore any data where the number of confirmed cases is less than
            this value; default is '0' or disabled

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
            ts = TimeSeries(data[region], 'confirmed', min_confirmed)
            ts.label = region

            gf = analysis.growth_factor(ts, 11)[-1, :]
            percent_change = analysis.percent_change(ts, 11)[-1, :]
            percent_change *= 100

            info = {}
            info['link'] = f'details-{region}.html'
            info['total_confirmed'] = int(ts[-1])
            info['new_cases'] = int(ts.daily_change[-1])
            info['multiplier'] = {
                'estimate': percent_change[0],
                'upper': percent_change[1],
                'lower': percent_change[2]
            }
            info['growth_factor'] = {
                'estimate': gf[0],
                'upper': gf[1],
                'lower': gf[2]
            }

            stats[region] = info

            plotter = Plotter([ts])
            plots[region] = plotter.plot_derivative('Daily Cases', 'Cases')
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
            stats[region]['link']: self.generate_report({region: timeseries},
                                                        min_confirmed)
            for region, timeseries in data.items()
        }

        return overview, details
