import { TimeSeries } from './timeseries';

/**
 * Name of the JSON file containing the analysis report summary.
 */
export const kAnalysisFile: string = 'analysis.json';

/**
 * The character used to separate national and subnational region names in a
 * region identifier string.  E.g., strings of the format
 * "`country`:`province`".
 */
export const kRegionSeparator: string = ':';

/**
 * A report's data source.
 */
export class Source {
    private _name: string;
    private _url: string;

    /**
     * Create a new source instance.
     * @param name data source display name
     * @param url location of the source data
     */
    public constructor(name: string, url: string) {
        this._name = name;
        this._url = url;
    }

    /**
     * The data source name.
     */
    public get name(): string { return this._name; }

    /**
     * The URL where the source data can be found.
     */
    public get url(): string { return this._url; }
}

/**
 * High-level metadata about a generated case report.
 */
export class ReportEntry {
    private _base: string;
    private _country: string;
    private _region: string;
    private _source: Source;

    /**
     * Create a new report details instance.
     * @param base base folder where report data may be found
     * @param jsonObject JSON object containing the report details
     */
    public constructor(base: string, jsonObject: any)
    {
        this._base = base;
        this._source = new Source(jsonObject['description'], jsonObject['url'])

        var regionIdentifier = jsonObject['name'];
        var underscore = regionIdentifier.indexOf(kRegionSeparator);
        if (underscore < 0) {
            this._country = regionIdentifier;
            this._region = null;
        } else {
            this._country = regionIdentifier.substring(0, underscore);
            this._region = regionIdentifier.substring(underscore+1);
        }
    }

    /**
     * The country the report is for.
     */
    public get country(): string { return this._country; }

    /**
     * The optional subnational region (i.e. province or state) that the report
     * is for.  This will be `null` for a nation-level report.
     */
    public get region(): string { return this._region; }

    /**
     * Information about where the source data was obtained.
     */
    public get source(): Source { return this._source; }

    /**
     * Fetch the time series associated with this report entry.
     * @returns a promise with the entry's time series
     */
    public async FetchTimeSeriesAsync(): Promise<TimeSeries> {
        let regionFile: string
        if (this._region == null) {
            regionFile = `${this._country}.json`;
        } else {
            regionFile = `${this._country}_${this._region}.json`;
        }

        let fetchUrl = `${this._base}/${regionFile}`;
        return await TimeSeries.FetchUrlAsync(fetchUrl);
    }
}

/**
 * Contains the set of all available case rate analyses.
 */
export class CaseReport {
    private _generated: Date;
    private _regions: ReportEntry[];

    protected constructor(generated: Date, regions: ReportEntry[]) {
        this._generated = generated;
        this._regions = regions;
    }

    /**
     * Information about an entry within the case report.
     * @param i report entry index
     */
    public entryDetails(i: number): ReportEntry {
        return this._regions[i];
    }

    /**
     * The date when the analysis was generated.
     */
    public get generatedOn(): Date { return this._generated; }

    /**
     * The number of individual entries stored within the full report.
     */
    public get numberOfEntries(): number { return this._regions.length; }

    /**
     * Load details abotu a case report from the given URL.
     * @param url folder with analysis data
     * @returns a new case report instance
     */
    public static async LoadAsync(url: string): Promise<CaseReport> {
        const response = await fetch(`${url}/${kAnalysisFile}`);
        const jsonData = await response.json();
        return new CaseReport(
            new Date(jsonData['generated']),
            (<object[]>jsonData['regions']).map(item => new ReportEntry(url, item))
        );
    }
}
