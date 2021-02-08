import * as Chart from 'chart.js';

import * as Colours from '../colourTheme';
import { CaseReport } from '../analysis';
import { TimeSeries, SeriesData, ConfidenceInterval } from '../timeseries';
import * as Utilities from '../utilities';


function rawDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
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

function interpDataPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets {
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

function confIntervalPlot(seriesData: SeriesData, previousDays?: number): Chart.ChartDataSets[] {
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

function plotDailyChange(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let dailyChange = timeSeries.series['dailyChange'];
    let ciDataset = confIntervalPlot(dailyChange, previousDays);

    let datasets: Chart.ChartDataSets[] = [
        interpDataPlot(dailyChange, previousDays),
        ciDataset[0],
        ciDataset[1],
        rawDataPlot(dailyChange, previousDays)
    ];

    let legendConfig: Chart.ChartLegendOptions = {
        labels: {
            filter: (item, _) => {
                return item.text !== 'LOESS Confidence - Lower';
            }
        }
    };

    new Chart(context, {
        type: 'line',
        data: {
            labels: Utilities.getDates(timeSeries),
            datasets: datasets
        },
        options: {
            legend: legendConfig,
            scales: {
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
    });
}

function plotGrowthFactor(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let growthFactor = timeSeries.series['growthFactor'];

    let dataset = interpDataPlot(growthFactor, previousDays);
    for (let i = 0; i < dataset.data.length; i++) {
        let gf = dataset.data[i] as number;
        dataset.data[i] = (gf - 1) * 100;
    }

    new Chart(context, {
        type: 'line',
        data: {
            labels: Utilities.getDates(timeSeries),
            datasets: [dataset]
        },
        options: {
            legend: {
                display: false
            },
            scales: {
                yAxes: [{
                    ticks: {
                        suggestedMin: -25,
                        suggestedMax: 25,
                        callback: (value) => {
                            return value + '%';
                        }
                    },
                    scaleLabel: {
                        display: true,
                        labelString: 'Relative Growth'
                    },
                }]
            }
        }
    });
}

function plotCumulativeCases(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let totalCases = timeSeries.series['cases'];

    let rawCounts = rawDataPlot(totalCases, previousDays);
    let interpolated = interpDataPlot(totalCases, previousDays);

    new Chart(context, {
        type: 'line',
        data: {
            labels: Utilities.getDates(timeSeries),
            datasets: [
                interpolated,
                rawCounts
            ]
        },
        options: {
            scales: {
                yAxes: [{
                    scaleLabel: {
                        display: true,
                        labelString: 'Cumulative Cases'
                    },
                }]
            }
        }
    });
}

function setupDateSelection() {
    const previousDays = Utilities.getIntParameter('pastDays') ?? 'all';
    const availableDays = [60, 90, 180, 'all'];

    availableDays.map(numDays => {
        let a = document.getElementById(`days-${numDays}`) as HTMLAnchorElement;

        a.onclick = () => {
            let href = new URL(document.location.href);
            href.searchParams.set('pastDays', numDays.toString());
            document.location.href = href.toString();
        };

        if (numDays === previousDays) {
            a.classList.add('font-bold');
        }

        return a;
    });
}

window.onload = () => {
    let selected = Utilities.getIntParameter('selected');
    if (selected == null) {
        throw new Error('No particular case report data was selected.');
    }

    setupDateSelection();

    // Disable legend selection.
    Chart.defaults.global.legend.onClick = () => {};

    CaseReport.LoadAsync('_analysis')
        .then(cr => {
            let infoDateGenerated = document.getElementById('info-date-generated');
            let infoRegion = document.getElementById('info-region');
            let infoSource = document.getElementById('info-source') as HTMLAnchorElement;

            let entry = cr.entryDetails(selected);
            infoDateGenerated.innerText = cr.generatedOn.toDateString();

            if (entry.region) {
                infoRegion.innerText = `${entry.country} - ${entry.region}`;
            } else {
                infoRegion.innerText = entry.country;
            }

            infoSource.href = entry.source.url;
            infoSource.innerText = entry.source.name;

            return entry.FetchTimeSeriesAsync()
        })
        .then(ts => {
            let dailyChange = document.getElementById('daily-change') as HTMLCanvasElement;
            let growthFactor = document.getElementById('growth-factor') as HTMLCanvasElement;
            let cumulativeCases = document.getElementById('cumulative-cases') as HTMLCanvasElement;

            plotDailyChange(ts, dailyChange);
            plotGrowthFactor(ts, growthFactor);
            plotCumulativeCases(ts, cumulativeCases);
        });
};
