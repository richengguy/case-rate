import * as Chart from 'chart.js';

import { CaseReport, ReportEntry } from '../analysis';
import * as Plotting from '../plotting';
import { TimeSeries } from '../timeseries';
import * as Utilities from '../utilities';


function plotDailyChange(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let dailyChange = timeSeries.series['dailyChange'];
    let ciDataset = Plotting.confIntervalPlot(dailyChange, previousDays);

    let datasets: Chart.ChartDataSets[] = [
        Plotting.interpDataPlot(dailyChange, previousDays),
        ciDataset[0],
        ciDataset[1],
        Plotting.rawDataPlot(dailyChange, previousDays)
    ];

    let config = Plotting.createChartConfiguration(Utilities.getDates(timeSeries), datasets);
    new Chart(context, config);
}

function plotGrowthFactor(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let growthFactor = timeSeries.series['growthFactor'];

    let dataset = Plotting.interpDataPlot(growthFactor, previousDays);
    for (let i = 0; i < dataset.data.length; i++) {
        let gf = dataset.data[i] as number;
        dataset.data[i] = (gf - 1) * 100;
    }

    let config = Plotting.createChartConfiguration(Utilities.getDates(timeSeries), [dataset]);
    config.options.scales.yAxes[0].scaleLabel.labelString = 'Relative Growth';
    config.options.scales.yAxes[0].ticks = {
        suggestedMin: -25,
        suggestedMax: 25,
        callback: (value) => { return value + '%'; }
    };

    new Chart(context, config);
}

function plotCumulativeCases(timeSeries: TimeSeries, context: HTMLCanvasElement) {
    let previousDays = Utilities.getIntParameter('pastDays');
    let totalCases = timeSeries.series['cases'];

    let rawCounts = Plotting.rawDataPlot(totalCases, previousDays);
    let interpolated = Plotting.interpDataPlot(totalCases, previousDays);

    let config = Plotting.createChartConfiguration(Utilities.getDates(timeSeries), [interpolated, rawCounts]);
    config.options.scales.yAxes[0].scaleLabel.labelString = 'Cumulative Cases';
    new Chart(context, config);
}

function plotPredictedCases(timeSeries: TimeSeries, container: HTMLDivElement, context: HTMLCanvasElement) {
    let predictedCases = timeSeries.prediction;
    if (predictedCases == null) { return; }

    container.classList.remove('hidden');

    let datasets: Chart.ChartDataSets[] = [];
    datasets.push(...Plotting.predictionIntervalPlot(predictedCases));
    datasets.push(...Plotting.predictedCasesPlot(predictedCases));

    let pastDays = Utilities.numberOfDays(timeSeries.dates[timeSeries.length-1], predictedCases.dates[0]);
    if (pastDays > 0) {
        datasets.push(Plotting.interpDataPlot(timeSeries.series['dailyChange'], pastDays));
        datasets.push(Plotting.rawDataPlot(timeSeries.series['dailyChange'], pastDays));
    }

    var config = Plotting.createChartConfiguration(predictedCases.dates, datasets);
    new Chart(context, config);
}

function setupRegionSelection(infoRegion: HTMLElement, entry: ReportEntry, regionNames: string[]) {
    if (regionNames.length === 0) {
        infoRegion.innerText = entry.country;
        return;
    }

    infoRegion.innerText = `${entry.country} - `;
    let selection = document.createElement('select');

    let defaultOption = document.createElement('option');
    defaultOption.innerText = 'National';
    defaultOption.onclick = () => {
        let href = new URL(document.location.href);
        href.searchParams.delete('region');
        document.location.href = href.toString();
    }
    selection.appendChild(defaultOption);

    let currentRegion = Utilities.getStringParameter('region');
    for (const name of regionNames) {
        let option = document.createElement('option');

        option.innerText = name;
        option.onclick = () => {
            let href = new URL(document.location.href);
            href.searchParams.set('region', name);
            document.location.href = href.toString();
        }

        if (name === currentRegion) {
            option.selected = true;
        }

        selection.appendChild(option);
    }

    infoRegion.appendChild(selection);
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
    let country = Utilities.getStringParameter('country');
    let region = Utilities.getStringParameter('region');

    if (country == null) {
        throw new Error('No particular case report data was selected.');
    }

    setupDateSelection();

    CaseReport.LoadAsync('_analysis')
        .then(cr => {
            let infoDateGenerated = document.getElementById('info-date-generated');
            let infoRegion = document.getElementById('info-region');
            let infoSource = document.getElementById('info-source') as HTMLAnchorElement;

            let entry = cr.entryDetailsByName(country, region);
            infoDateGenerated.innerText = cr.generatedOn.toDateString();
            setupRegionSelection(infoRegion, entry, cr.listSubnationalRegions(entry.country));

            infoSource.href = entry.source.url;
            infoSource.innerText = entry.source.name;

            return entry.FetchTimeSeriesAsync()
        })
        .then(ts => {
            let dailyChange = document.getElementById('daily-change') as HTMLCanvasElement;
            let growthFactor = document.getElementById('growth-factor') as HTMLCanvasElement;
            let cumulativeCases = document.getElementById('cumulative-cases') as HTMLCanvasElement;
            let prediction = document.getElementById('prediction') as HTMLCanvasElement;
            let predictionContainer = document.getElementById('prediction-container') as HTMLDivElement;

            plotDailyChange(ts, dailyChange);
            plotGrowthFactor(ts, growthFactor);
            plotCumulativeCases(ts, cumulativeCases);
            plotPredictedCases(ts, predictionContainer, prediction);
        });
};
