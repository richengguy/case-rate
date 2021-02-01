class Sample {
    private _raw: number;
    private _interpolated: number;
    private _confUpper: number;
    private _confLower: number;

    /**
     * Create a new time series sample.
     * @param raw raw sample
     * @param interpolated interpolated value
     * @param upperConf upper confidence interval (optional)
     * @param lowerConf lower confidence value (optional)
     */
    public constructor(raw: number, interpolated: number, upperConf?: number, lowerConf?: number) { }

    /**
     * The sample's raw, unprocessed value.
     */
    public get value(): number { return this._raw; }

    /**
     * The sample's interpolated or filtered value.
     */
    public get interpolatedValue(): number { return this._interpolated; }

    /**
     * Indicates if the sample has an associated confidence interval.  Not all
     * time series will have this.
     */
    public get hasConfidenceInterval(): boolean { return this._confUpper != null && this._confLower != null; }

    /**
     * The sample's confidence interval.  The value will be `undefined` if
     * hasConfidenceInterval is `false`.
     */
    public get confidenceInterval(): [number, number] {
        return this.hasConfidenceInterval ? [this._confUpper, this._confLower] : undefined;
    }
}

interface SamplesDictionary {
    [key: string]: Sample[];
}

interface JsonSeries {
    readonly name: string
    readonly raw?: number[]
    readonly interpolated: number[]
    readonly confidenceInterval: number[]
}

/**
 * A simple container for time series data.
 */
export class TimeSeries {
    private _dates: Date[];
    private _samples: SamplesDictionary;

    /**
     * Create a new TimeSeries instance.
     * @param dates set of time series dates
     * @param values set of time series values
     */
    public constructor (dates: Date[], values: JsonSeries[]) {
        if (dates.length != values.length) {
            throw new Error('Dates and values don\'t have the same length.');
        }
        this._dates = dates;
        this._samples = {};
    }

    /**
     * Number of items in the time series.
     */
    public get length(): number { return this._dates.length; }

    /**
     * The dates in the time series.
     */
    public get dates(): Date[] { return this._dates; }

    /**
     * A dictionary containing the samples for all of the stored time series.
     * Each series is the same length, but may represent different types of
     * information.
     */
    public get series(): SamplesDictionary { return this._samples; }

    public static async FetchAsync(url: string): Promise<TimeSeries> {
        return null;
    }
}
