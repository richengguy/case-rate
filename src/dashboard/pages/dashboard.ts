import * as Chart from 'chart.js';

import * as Colours from '../colourTheme';
import { CaseReport } from '../analysis';
import { TimeSeries, SeriesData, ConfidenceInterval } from '../timeseries';
import * as Utilities from '../utilities';

/**
 * Configures the region statistics template that's stored inside of the main
 * dashboard page.
 */
class RegionStatistics {
    private _template: HTMLTemplateElement;

    /**
     * Create a new RegionStatistics instance.
     * @param template
     *      a `<template>` containing the template for the statistics block
     */
    constructor(template: HTMLTemplateElement) {
        this._template = template;
    }

    public Render(): HTMLElement {
        var statistics = this._template.content.cloneNode(true) as HTMLElement;
        var countryName = statistics.querySelector('.countryName');
        countryName.textContent = 'Canada';
        return statistics;
    }
}

window.onload = () => {
    let template = document.getElementById('__template') as HTMLTemplateElement;
    let dashboard = document.getElementById('dashboard');

    let stats = (new RegionStatistics(template)).Render();
    dashboard.appendChild(stats);
};
