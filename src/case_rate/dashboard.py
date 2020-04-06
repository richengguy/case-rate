import enum
import pathlib
from typing import Dict, List, Optional

from case_rate import filters
from case_rate._types import PathLike, Cases
from case_rate.report import HTMLReport
from case_rate.timeseries import TimeSeries


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
                 source: Optional[str] = None,
                 confidence: float = 0.95,
                 filter_window: int = 7,
                 min_confirmed: int = 1):
        '''
        Parameters
        ----------
        mode : OutputType, optional
            the generated report type, by default OutputType.DEFAULT
        output : Path-like
            name of the dashboard HTML file, by default 'dashboard.html'
        source : str, optional
            path to the data's source repository, by default `None`
        confidence : float, optional
            the confidence interval percentage, by default 0.95
        filter_window : int, optional
            the size of the sliding window for the least-squares filter; by
            default 7
        min_confirmed : int, optional
            the minimum number of minimum confirmed cases for the date to be
            included in the report
        '''
        self.output_mode = mode
        self._output_path = pathlib.Path(output)
        self._source = source
        self._analysis_config = {
            'confidence': confidence,
            'window': filter_window
        }
        self._min_confirmed = min_confirmed
        self._html = HTMLReport()

    def generate(self, cases: Dict[str, List[Cases]]):
        '''Generate the HTML dashboard for the given case reports.

        Parameters
        ----------
        cases : dictionary of :class:`Cases` lists
            a dictionary of case reports, keyed by the region names
        '''
        def min_confirmed(case: Cases) -> bool:
            return case.confirmed >= self._min_confirmed

        for region in cases:
            cases[region] = filters.sum_by_date(cases[region])

        timeseries = {
            name: TimeSeries(filters.select(region, min_confirmed),
                             **self._analysis_config)
            for name, region in cases.items()
        }

        if self.output_mode == OutputType.DEFAULT:
            self._detail_page(timeseries)
        elif self.output_mode == OutputType.DASHBOARD:
            self._dashboard_page(timeseries)

    def _detail_page(self, timeseries: Dict[str, TimeSeries]):
        '''Generates the single HTML report (aka detail view).

        Parameters
        ----------
        timeseries : Dict[str, TimeSeries]
            dictionary containing the timeseries for each region
        '''
        with self._output_path.open('w') as f:
            f.write(self._html.generate_report(timeseries, self._source))

    def _dashboard_page(self, timeseries: Dict[str, TimeSeries]):
        '''Generates the dashboard view with regional detail views.

        Parameters
        ----------
        timeseries : Dict[str, TimeSeries]
            dictionary containing the timeseries for each region
        '''
        overview, details = self._html.generate_overview(timeseries, self._source)  # noqa: E501
        with self._output_path.open('w') as f:
            f.write(overview)

        for filename, html in details.items():
            path = pathlib.Path(filename)
            with path.open('w') as f:
                f.write(html)
