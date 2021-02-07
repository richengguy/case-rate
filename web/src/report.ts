import * as Chart from 'chart.js';

import * as Colours from './colourTheme';
import { CaseReport } from './analysis';
import { TimeSeries, SeriesData, ConfidenceInterval } from './timeseries';
import * as Utilities from './utilities';

function pruneArray(data: number[] | ConfidenceInterval[], previousDays?: number): number[] | ConfidenceInterval[] {
    return previousDays == null ? data : data.slice(-previousDays);
}

function rawDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
    let data = pruneArray(seriesData.raw, previousDays) as number[];
    return {
        type: 'bar',
        label: 'Daily New Cases',
        data: data,
        backgroundColor: Colours.kRawDataColour,
        barPercentage: 1.0,
        categoryPercentage: 1.0,
    }
}

function interpDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
    let data = pruneArray(seriesData.interpolated, previousDays) as number[];
    return {
        type: 'line',
        label: 'Daily New Cases (LOESS)',
        data: data,
        backgroundColor: Colours.kInterpolatedDataColour,
        borderColor: Colours.kInterpolatedDataColour,
        fill: false,
        pointRadius: 0,
        cubicInterpolationMode: 'monotone'
    }
}

function confIntervalPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets[] {
    let data = pruneArray(seriesData.confidenceIntervals, previousDays) as ConfidenceInterval[];
    let upperCi = data.map(ci => ci.upperInterval);
    let lowerCi = data.map(ci => ci.lowerInterval);

    return [{
        type: 'line',
        label: 'LOESS Confidence',
        data: upperCi,
        fill: '+1',
        pointRadius: 0,
        borderColor: Colours.kConfidenceIntervalColour,
        backgroundColor: Colours.kConfidenceIntervalColour,
    }, {
        type: 'line',
        label: 'LOESS Confidence - Lower',
        data: lowerCi,
        fill: false,
        pointRadius: 0,
        borderColor: Colours.kConfidenceIntervalColour,
        backgroundColor: Colours.kConfidenceIntervalColour,
    }]
}

function plotTimeSeries(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let dates = previousDays == null ? timeSeries.dates : timeSeries.dates.slice(-previousDays);

    let dailyChange = timeSeries.series['dailyChange'];
    let ciDataset = confIntervalPlot(dailyChange, previousDays);

    let datasets: Chart.ChartDataSets[] = [];
    datasets.push(interpDataPlot(dailyChange, previousDays));
    datasets.push(ciDataset[0], ciDataset[1]);
    datasets.push(rawDataPlot(dailyChange, previousDays));

    let legendConfig: Chart.ChartLegendOptions = {
        labels: {
            filter: (item, _) => {
                return item.text !== 'LOESS Confidence - Lower';
            }
        },
        onClick: function (event, item) {
            // NOTE: This is a slight modification of the Chart.js example on
            // how link legend items.  See
            // https://www.chartjs.org/docs/latest/configuration/legend.html#legend-label-configuration
            let index = item.datasetIndex;
            if (index === 0 || index === 3) {
                Chart.defaults.global.legend.onClick(event, item);
            } else {
                let ci = this.chart;
                [
                    ci.getDatasetMeta(1),
                    ci.getDatasetMeta(2)
                ].forEach((meta) => {
                    meta.hidden = meta.hidden === null ? !ci.data.datasets[index].hidden : null;
                });
                ci.update();
            }
        }
    }

    new Chart(context, {
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            legend: legendConfig
        }
    });
}

window.onload = () => {
    let canvas = document.getElementById('myChart') as HTMLCanvasElement;
    let selected = Utilities.getIntParameter('selected');
    if (selected == null) {
        throw new Error('No particular case report data was selected.');
    }

    CaseReport.LoadAsync('_analysis')
        .then(cr => cr.entryDetails(selected).FetchTimeSeriesAsync())
        .then(ts => plotTimeSeries(ts, canvas));
};
