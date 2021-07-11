import { TimeSeries, ConfidenceInterval } from './timeseries';

/**
 * Get a string query parameter.
 * @param name URL query parameter name
 * @returns the parameter's value or `null` if it doesn't exist
 */
export function getStringParameter(name: string): string {
    let url = new URL(document.location.href);
    return url.searchParams.get(name);
}

/**
 * Get an integer query parameter.
 * @param name URL query parameter name
 * @returns the parameter's integer value or `null` if it can't be parsed
 */
export function getIntParameter(name: string): number {
    let stringParam = getStringParameter(name);
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
 * Compute the number of days between two Date objects.
 * @param d1 first Date object
 * @param d2 second Date object
 * @returns the number of days between t1 and t2
 */
export function numberOfDays(d1: Date, d2: Date): number {
    let deltaT = d1.getTime() - d2.getTime();
    return deltaT / 86400000;  // number of milliseconds in a day
}

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
