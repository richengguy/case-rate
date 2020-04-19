import datetime
from typing import List, Tuple, Optional

import bokeh.models
import bokeh.palettes
import bokeh.plotting
import numpy as np

from . import analysis
from .analysis import TimeSeries


def _generate_palettes(num_series: int) -> list:
    '''Generates the palettes to choose the colours of the time series.

    Parameters
    ----------
    num_series : int
        number of time series being displayed

    Returns
    -------
    list
        the D3 palettes for each time series
    '''
    num_palettes = min(max(num_series, 3), 20)
    if num_series < 10:
        palettes = bokeh.palettes.d3['Category10'][num_palettes]
    else:
        palettes = bokeh.palettes.d3['Category20'][num_palettes]

    return list(palettes[i % num_palettes] for i in range(num_palettes))


def _to_datetime(dates: List[datetime.date]) -> List[datetime.datetime]:
    '''Converts :class:`datetime.date` objects into :class:`datetime.datetime`.

    Bokeh doesn't recognize date objects and so they have to be converted into
    datetime prior to rendering.

    Parameters
    ----------
    dates : list of :class:`datetime.date`
        input dates

    Returns
    -------
    list of :class:`datetime.datetime`
        converted dates
    '''
    d: datetime.date
    return list(datetime.datetime(d.year, d.month, d.day) for d in dates)


def _make_plot(**kwargs) -> bokeh.plotting.Figure:
    '''Initializes the bokeh plot.

    Parameters
    ----------
    title : str, optional
        plot title
    ylabel : str, optional
        label for the y-axis
    yrange : ``(min, max)``
        values that the y-axis should span
    log_plot : bool, optional
        y-axis is represented using a logarithmic scale

    Returns
    -------
    bokeh.plotting.Figure
        bokeh figure
    '''
    plot_args = {
        'x_axis_label': 'Date',
        'x_axis_type': 'datetime',
    }

    if 'title' in kwargs:
        plot_args['title'] = kwargs['title']
    if 'ylabel' in kwargs:
        plot_args['y_axis_label'] = kwargs['ylabel']
    if 'log_plot' in kwargs and kwargs['log_plot']:
        plot_args['y_axis_type'] = 'log'
    if 'yrange' in kwargs:
        plot_args['y_range'] = kwargs['yrange']

    return bokeh.plotting.Figure(**plot_args)


class Plotter:
    '''Plotting interface for time series data.

    The :class:`Plotter` class provides a single interface for plotting a
    :class:`TimeSeries` using Bokeh.
    '''
    def __init__(self, series: List[TimeSeries],
                 filter_window: int = 11,
                 confidence_interval: Optional[float] = None):
        '''
        Parameters
        ----------
        series : list of :class:`TimeSeries`
            the time series that the plotter is going to plot
        filter_window : int, optional
            specify the size of the filter window used when generating some of
            the plots; default is 11
        confidence_interval : float, optional
            specify the confidence interval for any plots that might visualize
            it
        '''
        ts: TimeSeries

        palettes = _generate_palettes(len(series))
        dates = [_to_datetime(ts.dates) for ts in series]

        self._data: List[Tuple[str, datetime.datetime, TimeSeries]]
        self._data = list(zip(palettes, dates, series))

        self._filter_args = {}
        self._filter_args['window'] = filter_window
        if confidence_interval is not None:
            self._filter_args['confidence'] = confidence_interval

    def plot_series(self,
                    title: Optional[str] = None,
                    ylabel: Optional[str] = None,
                    log_plot: bool = True,
                    show_count: bool = True) -> bokeh.plotting.Figure:
        '''Plots the provided series on a Bokeh plot.

        Parameters
        ----------
        title : str, optional
            plot title
        y_label : str, optional
            the y-axis label
        log_plot : bool, optional
            if ``True`` then the plot has a logarithmic y-axis; defaults to
            ``True``
        show_count : bool, optional
            if ``True`` then the very last value is shown on the plot, treating
            it as a cumulative sum

        Returns
        -------
        bokeh ``Figure``
        '''
        p = _make_plot(title=title, ylabel=ylabel, log_plot=log_plot)
        filter_args = self._filter_args.copy()
        filter_args['log_domain'] = log_plot

        for colour, dates, series in self._data:
            smoothed = analysis.smooth(series, **filter_args)
            p.line(dates, smoothed, legend_label=series.label,
                   line_color=colour, line_width=1.5)
            p.line(dates, np.array(series), line_color='lightgray')

            if show_count:
                p.add_layout(
                    bokeh.models.Label(
                        x=dates[-1], y=series[-1], text=f'{int(series[-1])}'
                    )
                )

        return p

    def plot_derivative(self,
                        title: Optional[str] = None,
                        ylabel: Optional[str] = None) -> bokeh.plotting.Figure:
        '''Plot the derivative of the time series.

        Parameters
        ----------
        title : str, optional
            plot title
        ylabel : str, optional
            y-axis label
        '''
        p = _make_plot(title=title, ylabel=ylabel)
        for colour, dates, series in self._data:
            derivative = analysis.estimate_slope(series, **self._filter_args)

            data = {
                'date': dates,
                'difference': series.daily_change,
                'derivative': np.squeeze(derivative[:, 0]),
                'upper_ci': np.squeeze(derivative[:, 1]),
                'lower_ci': np.squeeze(derivative[:, 2])
            }

            source = bokeh.models.ColumnDataSource(data)
            width = datetime.timedelta(days=1)

            # Displays the finite difference and slope estimate.
            p.vbar(x='date', top='difference', source=source, width=width,
                   fill_color=colour, alpha=0.5)
            p.line(x='date', y='derivative', source=source, line_color=colour,
                   line_width=2, legend_label=series.label)

            # Displays the confidence interval band.
            p.add_layout(bokeh.models.Band(
                base='date', upper='upper_ci', lower='lower_ci', source=source,
                line_color='grey', line_dash='dashed', line_alpha=1.0,
                fill_color=colour, fill_alpha=0.2))

        return p

    def plot_percent_change(self, title: Optional[str] = None) -> bokeh.plotting.Figure:  # noqa: E501
        '''Plot the sample-over-sample percent change.

        Parameters
        ----------
        title : str, optional
            plot title

        Returns
        -------
        bokeh ``Figure``
        '''
        p = _make_plot(title=title, ylabel='Percent Change (%)')
        for colour, dates, series in self._data:
            prcnt_change = analysis.percent_change(series, **self._filter_args)
            prcnt_change *= 100.0

            data = {
                'date': dates,
                'percent_change': np.squeeze(prcnt_change[:, 0]),
                'upper_ci': np.squeeze(prcnt_change[:, 1]),
                'lower_ci': np.squeeze(prcnt_change[:, 2])
            }

            source = bokeh.models.ColumnDataSource(data)

            # Displays the finite difference and slope estimate.
            p.line(x='date', y='percent_change', source=source,
                   line_color=colour, line_width=2, legend_label=series.label)

            # Displays the confidence interval band.
            p.add_layout(bokeh.models.Band(
                base='date', upper='upper_ci', lower='lower_ci', source=source,
                line_color='grey', line_dash='dashed', line_alpha=1.0,
                fill_color=colour, fill_alpha=0.2))

        return p

    def plot_growth_factor(self, title: Optional[str] = None) -> bokeh.plotting.Figure:  # noqa: E501
        '''Plot the growth factor for the time series.

        Parameters
        ----------
        title : str, optional
            plot title

        Returns
        -------
        bokeh ``Figure``
        '''
        p = _make_plot(title=title, ylabel='Growth Factor', yrange=(0, 2.5))

        for colour, dates, series in self._data:
            growth = analysis.growth_factor(series, **self._filter_args)

            data = {
                'date': dates,
                'growth_factor': np.squeeze(growth[:, 0]),
                'upper_ci': np.squeeze(growth[:, 1]),
                'lower_ci': np.squeeze(growth[:, 2])
            }

            source = bokeh.models.ColumnDataSource(data)

            # Displays the finite difference and slope estimate.
            p.line(x='date', y='growth_factor', source=source,
                   line_color=colour, line_width=2, legend_label=series.label)

            # Displays the confidence interval band.
            p.add_layout(bokeh.models.Band(
                base='date', upper='upper_ci', lower='lower_ci', source=source,
                line_color='grey', line_dash='dashed', line_alpha=1.0,
                fill_color=colour, fill_alpha=0.2))

        # Displays line where growth is slowing.
        p.add_layout(bokeh.models.Span(location=1, dimension='width',
                                       line_dash='dashed', line_color='gray'))

        return p
