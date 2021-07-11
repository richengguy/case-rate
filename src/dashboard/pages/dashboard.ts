import * as Chart from 'chart.js';

import { CaseReport, ReportEntry } from '../analysis';
import * as Plotting from '../plotting';
import { SeriesData, TimeSeries } from '../timeseries';
import * as Utilities from '../utilities';

function plotDailyChanges(context: HTMLCanvasElement, dailyChange: SeriesData, totalDays: Date[], previousDays: number) {
    let datasets: Chart.ChartDataSets[] = [
        Plotting.interpDataPlot(dailyChange, previousDays),
        Plotting.rawDataPlot(dailyChange, previousDays)
    ];

    totalDays = Utilities.pruneArray(totalDays, previousDays) as Date[];
    let config = Plotting.createChartConfiguration(totalDays, datasets);
    new Chart(context, config);
}

function setDetailsPage(stats: HTMLElement, entry: ReportEntry) {
    let element = stats.querySelector('.details-link') as HTMLAnchorElement;
    if (entry.region === null) {
        element.href = `details.html?country=${entry.country}&pastDays=90`;
    } else {
        element.href = `details.html?country=${entry.country}&region=${entry.region}&pastDays=90`;
    }
}

function setGrowthFactor(stats: HTMLElement, field: string, data: number[]) {
    let element = stats.querySelector(`.${field}`);
    const length = data.length;
    const percentage = (data[length-1] - 1.0) * 100.0;

    element.textContent = `${percentage.toLocaleString()} %`;
}

function setNumericalValue(stats: HTMLElement, field: string, data: number[]) {
    let element = stats.querySelector(`.${field}`);
    const length = data.length;
    element.textContent = data[length-1].toLocaleString();
}

class RenderJob {
    private _container: HTMLElement;
    private _dailyChange: SeriesData;
    private _dates: Date[];
    private _index: number;

    public constructor(index: number, timeSeries: TimeSeries, container: HTMLElement) {
        this._index = index;
        this._container = container;
        this._dailyChange = timeSeries.series['dailyChange'];
        this._dates = Utilities.getDates(timeSeries);
    }

    public get container(): HTMLElement { return this._container; }
    public get dailyChange(): SeriesData { return this._dailyChange; }
    public get dates(): Date[] { return this._dates; }
    public get index(): number { return this._index; }
}

/**
 * Configures the region statistics template that's stored inside of the main
 * dashboard page.
 */
class RegionStatisticsFactory {
    private _template: HTMLTemplateElement;

    /**
     * Create a new RegionStatistics instance.
     * @param template
     *      a `<template>` containing the template for the statistics block
     */
    constructor(template: HTMLTemplateElement) {
        this._template = template;
    }

    public async RenderAsync(index: number, reportEntry: ReportEntry): Promise<RenderJob> {
        let statistics = this._template.content.cloneNode(true) as HTMLElement;
        let countryName = statistics.querySelector('.country-name');
        countryName.textContent = reportEntry.country;

        let timeSeries = await reportEntry.FetchTimeSeriesAsync();
        setNumericalValue(statistics, 'new-cases', timeSeries.series['dailyChange'].raw);
        setNumericalValue(statistics, 'total-confirmed', timeSeries.series['cases'].raw);
        setGrowthFactor(statistics, 'relative-growth', timeSeries.series['growthFactor'].interpolated);
        setDetailsPage(statistics, reportEntry);

        let chart = statistics.querySelector('.daily-cases-chart') as HTMLCanvasElement;
        chart.id = `cases-${index}`;

        return new RenderJob(index, timeSeries, statistics);
    }
}

window.onload = () => {
    let dashboard = document.getElementById('dashboard');
    let dateGenerated = document.getElementById('date-generated');
    let template = document.getElementById('__template') as HTMLTemplateElement;

    // Disable legend selection.
    Chart.defaults.global.legend.onClick = () => {};

    let factory = new RegionStatisticsFactory(template);
    CaseReport.LoadAsync('_analysis')
        .then(cr => {
            dateGenerated.innerText = cr.generatedOn.toDateString();
            let jobs: Promise<RenderJob>[] = [];
            for (let i = 0; i < cr.numberOfEntries; i++) {
                let entry = cr.entryDetails(i);
                if (entry.region !== null) {
                    continue;
                }

                jobs.push(factory.RenderAsync(i, entry));
            }

            return Promise.all(jobs);
        })
        .then(renderJobs => {
            for (const job of renderJobs) {
                dashboard.appendChild(job.container);
            }
            return renderJobs;
        })
        .then(renderJobs => {
            for (const job of renderJobs) {
                let chart = document.getElementById(`cases-${job.index}`) as HTMLCanvasElement;
                plotDailyChanges(chart, job.dailyChange, job.dates, 90);
            }
        });
};
