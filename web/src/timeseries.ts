/**
 * A simple container for time series data.
 */
export class TimeSeries {
    private _dates: Date[];
    private _values: Number[];

    /**
     * Create a new TimeSeries instance.
     * @param dates set of time series dates
     * @param values set of time series values
     */
    public constructor (dates: Date[], values: Number[]) {
        if (dates.length != values.length) {
            throw new Error('Dates and values don\'t have the same length.');
        }
        this._dates = dates;
        this._values = values;
    }

    /**
     * Number of items in the time series.
     */
    public get length(): Number { return this._dates.length; }

    /**
     * The dates in the time series.
     */
    public get dates(): Date[] { return this._dates; }

    /**
     * The values for each date in the time series.
     */
    public get values(): Number[] { return this._values; }
}
