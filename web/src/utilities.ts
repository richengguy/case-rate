import { TimeSeries, ConfidenceInterval } from './timeseries';

/**
 * Get an integer query parameter.
 * @param name URL query parameter name
 * @returns the parameter's integer value or `null` if it can't be parsed
 */
export function getIntParameter(name: string): number {
    let url = new URL(document.location.href);
    let stringParam = url.searchParams.get(name);

    if (stringParam == null) {
        return null;
    }

    let intValue = parseInt(stringParam);
    if (isNaN(intValue)) {
        return null;
    }

    return intValue;
}

/**
 * Get the correct date range for the given time series.
 * @param timeSeries a case report time series
 * @returns the correct data range
 */
export function getDates(timeSeries: TimeSeries): Date[] {
    let previousDays = getIntParameter('pastDays');
    return pruneArray(timeSeries.dates, previousDays) as Date[];
}

type SeriesArray = number[] | ConfidenceInterval[] | Date[];

/**
 * Prune the input time series array so that it retains only the last 'N' days
 * of data.
 * @param data
 *      input array
 * @param previousDays
 *      number of days to retain; setting to `null` will retain all array values
 * @returns the truncated/pruned array
 */
export function pruneArray(data: SeriesArray, previousDays?: number): SeriesArray {
    return previousDays == null ? data : data.slice(-previousDays);
}
