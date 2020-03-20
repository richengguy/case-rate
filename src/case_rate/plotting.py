import datetime
from typing import Dict

import bokeh.models
import bokeh.palettes
import bokeh.plotting
import bokeh.resources
import bokeh.embed

from case_rate import TimeSeries


class Plotter(object):
    '''High-level object for plotting time-series data.'''
    def __init__(self, timeseries: Dict[str, TimeSeries]):
        self._timeseries = timeseries
        self._num_series = len(timeseries)

        # Need to convert datetime.date into datetime.datetime so Bokeh knows
        # what do do with them.
        d: datetime.date
        self._dates = {
            name: [
                datetime.datetime(d.year, d.month, d.day) for d in ts.dates
            ] for name, ts in timeseries.items()
        }

        # Select the colour palettes to use.
        palette = max(self._num_series, 3)

        if self._num_series < 10:
            self._colours = bokeh.palettes.d3['Category10'][palette]
        elif self._num_series < 20:
            self._colours = bokeh.palettes.d3['Category20'][palette]
        else:
            self._colours = bokeh.palettes.d3['Category20'][20]

    def plot_confirmed(self):
        '''Plot all confirmed cases.
        '''
        p = bokeh.plotting.figure(title='Confirmed Cases',
                                  x_axis_label='Date',
                                  x_axis_type='datetime',
                                  y_axis_label='Cases',
                                  y_axis_type='log')

        for i, (region, timeseries) in enumerate(self._timeseries.items()):
            line_colour = self._colours[i % len(self._timeseries)]
            p.line(self._dates[region], timeseries.smoothed,
                   legend_label=region, line_color=line_colour,
                   line_width=1.5)
            p.line(self._dates[region], timeseries.confirmed,
                   line_color='lightgray')

            count = bokeh.models.Label(x=self._dates[region][-1],
                                       y=timeseries.confirmed[-1],
                                       text=f'{timeseries.confirmed[-1]}')
            p.add_layout(count)

        bokeh.plotting.show(p)
