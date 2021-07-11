interface JsonTimeSeries {
    readonly country: string,
    readonly date: string[],
    readonly timeseries: JsonSeriesData[],
    readonly prediction: JsonSeriesPrediction
}

interface JsonSeriesData {
    readonly name: string
    readonly raw?: number[]
    readonly interpolated: number[]
    readonly confidenceInterval?: [number, number][]
}

interface JsonSeriesPrediction {
    readonly dates: string[]
    readonly cases: number[]
    readonly predictionInterval: [number, number][]
}

export class ConfidenceInterval {
    private _values: [number, number];

    public constructor(values: [number, number]) {
        this._values = values;
    }

    /**
     * The upper range of the confidence interval.
     */
    public get upperInterval(): number { return this._values[0]; }

    /**
     * The lower range of the confidence interval.
     */
    public get lowerInterval(): number { return this._values[1]; }
}

/**
 * Stores a time series prediction.
 */
export class PredictionData {
    private _dates: Date[];
    private _predictedCases: number[];
    private _confidence: ConfidenceInterval[];

    /**
     * Create a new PredictionData instance.
     * @param data the original JSON representation
     */
    constructor(data: JsonSeriesPrediction) {
        this._dates = data.dates.map(d => new Date(d));
        this._predictedCases = data.cases;
        this._confidence = data.predictionInterval.map(pi => {
            return new ConfidenceInterval(pi)
        });
    }

    /**
     * The dates of each of the predicted values.
     */
    public get dates(): Date[] { return this._dates; }

    /**
     * The number of predicted cases at each date.
     */
    public get predictedCases(): number[] { return this._predictedCases; }

    /**
     * The prediction interval for this specific prediction.  The interval will
     * start very small and widen over the course of the time series.
     */
    public get predictionInterval(): ConfidenceInterval[] { return this._confidence; }
}

export class SeriesData {
    private _raw: number[];
    private _interpolated: number[];
    private _confidence: ConfidenceInterval[]

    /**
     * Create a new SeriesData instance.
     * @param data the original JSON representation
     */
    constructor(data: JsonSeriesData) {
        this._interpolated = data.interpolated;
        this._raw = data.raw ?? [];
        this._confidence = [];
        if (data.confidenceInterval != null) {
            this._confidence = data.confidenceInterval.map((interval) => {
                return new ConfidenceInterval(interval);
            });
        }
    }

    public get interpolated(): number[] { return this._interpolated; }

    public get raw(): number[] { return this._raw; }

    public get confidenceIntervals(): ConfidenceInterval[] { return this._confidence; }

    public get hasRaw(): boolean { return this._raw.length != 0; }

    public get hasConfidenceIntervals(): boolean { return this._confidence.length != 0; }
}

interface SeriesDictionary {
    [key: string]: SeriesData;
}

/**
 * A simple container for time series data.
 */
export class TimeSeries {
    private _dates: Date[];
    private _length: number;
    private _prediction: JsonSeriesPrediction;
    private _samples: SeriesDictionary;

    /**
     * Create a new TimeSeries instance.
     * @param dates set of time series dates
     * @param jsonData set of time series values
     */
    public constructor (jsonTimeSeries: JsonTimeSeries) {
        this._dates = jsonTimeSeries.date.map(d => new Date(d));
        this._length = jsonTimeSeries.date.length;
        this._prediction = jsonTimeSeries.prediction;
        this._samples = {};
        for (const item of jsonTimeSeries.timeseries) {
            this._samples[item.name] = new SeriesData(item);
        }
    }

    /**
     * Number of items in the time series.
     */
    public get length(): number { return this._length; }

    /**
     * The dates in the time series.
     */
    public get dates(): Date[] { return this._dates; }

    /**
     * A dictionary containing the samples for all of the stored time series.
     * Each series is the same length, but may represent different types of
     * information.
     */
    public get series(): SeriesDictionary { return this._samples; }

    /**
     * The predicted number of cases for the given time series.  This will be
     * `null` if no predictions are available.
     */
    public get prediction(): PredictionData {
        if (this._prediction.dates.length > 0) {
            return new PredictionData(this._prediction);
        } else {
            return null;
        }
    }

    /**
     * Fetch a time series from a JSON file.
     * @param url location of timeseries json file
     * @returns a promise for a new TimeSeries instance
     */
    public static async FetchUrlAsync(url: string): Promise<TimeSeries> {
        var request = await fetch(url);
        var jsonData = await request.json() as JsonTimeSeries;
        return new TimeSeries(jsonData);
    }
}
