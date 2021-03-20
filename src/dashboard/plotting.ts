import * as Chart from 'chart.js';

import * as Colours from './colourTheme';
import { ConfidenceInterval, SeriesData } from './timeseries';
import * as Utilities from './utilities';

/**
 * Plot a set of raw (unprocessed) time series data.
 * @param seriesData series being plotting
 * @param previousDays number of days to plot
 * @returns the chart.js dataset object
 */
export function rawDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
    let data = Utilities.pruneArray(seriesData.raw, previousDays) as number[];
    return {
        type: 'bar',
        label: 'Reported',
        data: data,
        backgroundColor: Colours.kRawDataColour,
        barPercentage: 1.0,
        categoryPercentage: 1.0,
    }
}

/**
 * Plot a set of filtered, or interpolated, time series data.
 * @param seriesData series being plotted
 * @param previousDays number of days to plot
 * @returns the chart.js dataset object
 */
export function interpDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
    let data = Utilities.pruneArray(seriesData.interpolated, previousDays) as number[];
    return {
        type: 'line',
        label: 'LOESS Filtered',
        data: data,
        backgroundColor: Colours.kInterpolatedDataColour,
        borderColor: Colours.kInterpolatedDataColour,
        fill: false,
        pointRadius: 0,
        borderWidth: 1.5,
        cubicInterpolationMode: undefined
    }
}

/**
 * Plot the confidence interval for any sort of regression or filtering
 * operation applied to the time series.
 * @param seriesData series being plotted
 * @param previousDays number of days to plot
 * @returns the chart.js dataset object
 */
export function confIntervalPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets[] {
    let data = Utilities.pruneArray(seriesData.confidenceIntervals, previousDays) as ConfidenceInterval[];
    let upperCi = data.map(ci => ci.upperInterval);
    let lowerCi = data.map(ci => ci.lowerInterval);

    return [{
        type: 'line',
        label: 'LOESS Confidence',
        data: upperCi,
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
        borderDash: [5, 5],
        borderColor: Colours.kConfidenceIntervalColour,
    }, {
        type: 'line',
        label: 'LOESS Confidence - Lower',
        data: lowerCi,
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
        borderDash: [5, 5],
        borderColor: Colours.kConfidenceIntervalColour,
    }]
}
