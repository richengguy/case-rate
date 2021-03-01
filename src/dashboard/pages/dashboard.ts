import * as Chart from 'chart.js';

import * as Colours from '../colourTheme';
import { CaseReport, ReportEntry } from '../analysis';
import { TimeSeries, SeriesData, ConfidenceInterval } from '../timeseries';
import * as Utilities from '../utilities';

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

    public async RenderAsync(reportEntry: ReportEntry): Promise<HTMLElement> {
        let statistics = this._template.content.cloneNode(true) as HTMLElement;
        let countryName = statistics.querySelector('.country-name');
        countryName.textContent = reportEntry.country;

        let timeSeries = await reportEntry.FetchTimeSeriesAsync();
        setNumericalValue(statistics, 'new-cases', timeSeries.series['dailyChange'].raw);
        setNumericalValue(statistics, 'total-confirmed', timeSeries.series['cases'].raw);
        setGrowthFactor(statistics, 'relative-growth', timeSeries.series['growthFactor'].interpolated);

        return statistics;
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
            let jobs: Promise<HTMLElement>[] = [];
            for (let i = 0; i < cr.numberOfEntries; i++) {
                let entry = cr.entryDetails(i);
                if (entry.region !== null) {
                    continue;
                }

                jobs.push(factory.RenderAsync(entry));
            }

            return Promise.all(jobs);
        })
        .then(statistics => {
            for (const block of statistics) {
                dashboard.appendChild(block);
            }
        });
};
