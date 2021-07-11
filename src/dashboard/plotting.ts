import * as Chart from 'chart.js';

import * as Colours from './colourTheme';
import { ConfidenceInterval, PredictionData, SeriesData } from './timeseries';
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

/**
 * Plot the predicted number of cases given some prediction data.
 * @param prediction prediction time series data
 * @returns the chart.js dataset object
 */
export function predictedCasesPlot(prediction: PredictionData): Chart.ChartDataSets[] {
    let roundedPrediction = prediction.predictedCases.map(p => Math.round(p));
    return [{
        type: 'line',
        label: 'Predicted Cases',
        fill: false,
        data: roundedPrediction,
        borderColor: Colours.kPredictionColour,
    }]
}

/**
 * Plot a prediction interval diven prediction data.
 * @param prediction prediction time series data
 * @returns the chart.js dataset object
 */
export function predictionIntervalPlot(prediction: PredictionData) : Chart.ChartDataSets[] {
    let upperPi = prediction.predictionInterval.map(pi => pi.upperInterval);
    let lowerPi = prediction.predictionInterval.map(pi => pi.lowerInterval);

    return [{
        type: 'line',
        label: 'Prediction Interval',
        data: upperPi,
        fill: '+1',
        pointRadius: 0,
        borderWidth: 0,
        backgroundColor: Colours.kPredictionIntervalColour
    }, {
        type: 'line',
        data: lowerPi,
        fill: false,
        pointRadius: 0,
        borderWidth: 0,
        backgroundColor: Colours.kClearColour
    }]
}

/**
 * Generate a configuration to render some data on a chart.
 * @param dates the dates used for the chart's horizontal axis
 * @param charts the data sets to show on the main chart
 * @returns the customizeable chart configuration
 */
export function createChartConfiguration(dates: Date[], charts: Chart.ChartDataSets[]): Chart.ChartConfiguration {
    let defaultLegendConfig: Chart.ChartLegendOptions = {
        labels: {
            filter: (item, _) => {
                return item.text !== undefined;
            }
        }
    };

    return {
        type: 'line',
        data: {
            labels: dates,
            datasets: charts
        },
        options: {
            maintainAspectRatio: false,
            legend: defaultLegendConfig,
            scales: {
                xAxes: [{
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'D MMM YYYY'
                        }
                    }
                }],
                yAxes: [{
                    ticks: {
                        min: 0
                    },
                    scaleLabel: {
                        display: true,
                        labelString: 'Cases'
                    }
                }]
            }
        }
    }
}
