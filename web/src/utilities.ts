import { CaseReport } from './analysis';
import { TimeSeries } from './timeseries';

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
    if (intValue == NaN) {
        return null;
    }

    return intValue;
}
