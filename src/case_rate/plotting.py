import datetime
from typing import Dict, List, Tuple

import bokeh.models
import bokeh.palettes
import bokeh.plotting
import bokeh.resources
import bokeh.embed
import numpy as np

from case_rate import TimeSeries


class Plotter(object):
    '''High-level object for plotting time-series data.'''
    def __init__(self, timeseries: Dict[str, TimeSeries]):
        self._num_series = len(timeseries)

        # Select the colour palettes to use.
        num_palettes = min(max(self._num_series, 3), 20)
        if self._num_series < 10:
            palettes = bokeh.palettes.d3['Category10'][num_palettes]
        else:
            palettes = bokeh.palettes.d3['Category20'][num_palettes]

        # Need to convert datetime.date into datetime.datetime so Bokeh knows
        # what do do with them.
        d: datetime.date
        self._dates = {
            name: [
                datetime.datetime(d.year, d.month, d.day) for d in ts.dates
            ] for name, ts in timeseries.items()
        }

        def to_datetime(date: datetime.date) -> datetime.datetime:
            return datetime.datetime(date.year, date.month, date.day)

        # Rank regions based on counts to simplify some of the plotting.
        regions = sorted(timeseries.keys(),
                         key=lambda region: -timeseries[region].confirmed[-1])
        dates = list(
            [to_datetime(date) for date in timeseries[region].dates]
            for region in regions
        )
        timeseries = list(timeseries[region] for region in regions)
        colours = list(palettes[i % self._num_series] for i in range(self._num_series))  # noqa: E501

        self._data: List[Tuple[str, str, datetime.datetime, TimeSeries]]
        self._data = list(zip(colours, regions, dates, timeseries))

    def plot_confirmed(self):
        '''Plot all confirmed cases.'''
        p = bokeh.plotting.figure(title='Confirmed Cases',
                                  x_axis_label='Date',
                                  x_axis_type='datetime',
                                  y_axis_label='Cases',
                                  y_axis_type='log')

        for colour, region, dates, timeseries in self._data:
            p.line(dates, timeseries.smoothed, legend_label=region,
                   line_color=colour, line_width=1.5)
            p.line(dates, timeseries.confirmed, line_color='lightgray')

            count = bokeh.models.Label(x=dates[-1],
                                       y=timeseries.confirmed[-1],
                                       text=f'{timeseries.confirmed[-1]}')
            p.add_layout(count)

        bokeh.plotting.show(p)

    def plot_new_cases(self):
        '''Plot daily new cases over time.'''
        p = bokeh.plotting.figure(title='New Daily Cases',
                                  x_axis_label='Date',
                                  x_axis_type='datetime',
                                  y_axis_label='Cases')

        timeseries: TimeSeries
        for colour, region, dates, timeseries in self._data:
            new_cases = timeseries._processed.package()
            source = bokeh.models.ColumnDataSource(data={
                'date': dates,
                'new_cases': timeseries.daily_new_cases(),
                'estimated_slope': np.squeeze(new_cases[:, 0]),
                'upper_limit': np.squeeze(new_cases[:, 1]),
                'lower_limit': np.squeeze(new_cases[:, 2])
            })

            p.vbar(x='date', top='new_cases', source=source,
                   width=datetime.timedelta(days=1),
                   fill_color=colour,
                   alpha=0.5)
            p.line(x='date', y='estimated_slope', source=source,
                   line_color=colour,
                   line_width=2,
                   legend_label=region)

            uncertainty = bokeh.models.Band(base='date', upper='upper_limit',
                                            lower='lower_limit', source=source,
                                            line_color='grey',
                                            line_dash='dashed',
                                            line_alpha=1.0,
                                            fill_color=colour,
                                            fill_alpha=0.2)
            p.add_layout(uncertainty)

        bokeh.plotting.show(p)

    def plot_growth_factor(self):
        '''Plot the growth factor over time.'''
        p = bokeh.plotting.figure(title='Growth Factor',
                                  x_axis_label='Date',
                                  x_axis_type='datetime',
                                  y_axis_label='Growth Factor',
                                  y_range=(0, 4))

        timeseries: TimeSeries
        for colour, region, dates, timeseries in self._data:
            rates = timeseries.growth_factor()

            source = bokeh.models.ColumnDataSource(data={
                'date': dates,
                'growth_factor': np.squeeze(rates[:, 0]),
                'upper': np.squeeze(rates[:, 1]),
                'lower': np.squeeze(rates[:, 2])
            })

            uncertainty = bokeh.models.Band(base='date', upper='upper',
                                            lower='lower', source=source,
                                            level='underlay', fill_alpha=0.4,
                                            fill_color=colour,
                                            name=f'uncertainty')

            p.line(x='date', y='growth_factor', source=source,
                   legend_label=region, line_color=colour, line_width=2)
            p.add_layout(uncertainty)

        boundary = bokeh.models.Span(location=1, dimension='width',
                                     line_dash='dashed', line_color='gray')
        p.add_layout(boundary)

        bokeh.plotting.show(p)
