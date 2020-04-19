import enum
import pathlib
from typing import Dict, List, Optional

from . import filters
from ._types import PathLike, Datum
from .report import HTMLReport, SourceInfo
from .timeseries import TimeSeries


class OutputType(enum.Enum):
    '''Specifies the dashboard output types.'''
    DEFAULT = enum.auto()
    DASHBOARD = enum.auto()


class Dashboard(object):
    '''Generate a dashboard view when comparing multiple countries/regions.

    The dashboard takes care of generating the underlying reports and then
    saving the HTML files.  The default mode is render a single report with
    each country/region overlaid onto the same graph.  The "dashboard" mode
    will generate a set of HTML pages, with a single landing page and multiple
    detail pages.
    '''
    def __init__(self, mode: OutputType = OutputType.DEFAULT,
                 output: PathLike = 'dashboard.html',
                 sources: Optional[Dict[str, SourceInfo]] = None,
                 confidence: float = 0.95,
                 filter_window: int = 11,
                 min_confirmed: int = 1):
        '''
        Parameters
        ----------
        mode : OutputType, optional
            the generated report type, by default OutputType.DEFAULT
        output : Path-like
            name of the dashboard HTML file, by default 'dashboard.html'
        sources : dict of :class:`SourceInfo` objects
            contains optional data source information, by default `None`
        confidence : float, optional
            the confidence interval percentage, by default 0.95
        filter_window : int, optional
            the size of the sliding window for the least-squares filter, set to
            '11' by default
        min_confirmed : int, optional
            the minimum number of minimum confirmed cases for the date to be
            included in the report
        '''
        self.output_mode = mode
        self._output_path = pathlib.Path(output)
        self._analysis_config = {
            'confidence': confidence,
            'window': filter_window
        }
        self._min_confirmed = min_confirmed
        self._html = HTMLReport(sources)

    def generate(self, data: Dict[str, List[Datum]]):
        '''Generate the HTML dashboard for the given case reports.

        Parameters
        ----------
        data : dictionary of :class:`Cases` or :class:`CaseTesting` lists
            a dictionary of case reports, keyed by the region names
        '''
        for region in data:
            data[region] = filters.sum_by_date(data[region])

        if self.output_mode == OutputType.DEFAULT:
            self._detail_page(data)
        elif self.output_mode == OutputType.DASHBOARD:
            self._dashboard_page(data)

    def _detail_page(self, data: Dict[str, List[Datum]]):
        '''Generates the single HTML report (aka detail view).

        Parameters
        ----------
        data : dictionary of :class:`Cases` or :class:`CaseTesting` lists
            a dictionary of case reports, keyed by the region names
        '''
        with self._output_path.open('w') as f:
            f.write(self._html.generate_report(data))

    def _dashboard_page(self, data: Dict[str, List[Datum]]):
        '''Generates the dashboard view with regional detail views.

        Parameters
        ----------
        data : dictionary of :class:`Cases` or :class:`CaseTesting` lists
            a dictionary of case reports, keyed by the region names
        '''
        overview, details = self._html.generate_overview(data)
        with self._output_path.open('w') as f:
            f.write(overview)

        for filename, html in details.items():
            path = pathlib.Path(filename)
            with path.open('w') as f:
                f.write(html)
