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
    private _date: Date;
    private _region: string;
    private _source: Source;

    /**
     * Create a new report details instance.
     * @param base base folder where report data may be found
     * @param date date when the report entry was generated
     * @param jsonObject JSON object containing the report details
     */
    public constructor(base: string, date: Date, jsonObject: any)
    {
        this._base = base;
        this._date = date;
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

        let fetchUrl = `${this._base}/${regionFile}?t=${this._date.getTime()}`;
        return await TimeSeries.FetchUrlAsync(fetchUrl);
    }
}

export interface ReportConfig {
    filterWindow: number;
    minConfirmed: number;
}

/**
 * Contains the set of all available case rate analyses.
 */
export class CaseReport {
    private _config: ReportConfig;
    private _generated: Date;
    private _regions: ReportEntry[];

    protected constructor(generated: Date, regions: ReportEntry[], config: ReportConfig) {
        this._config = config;
        this._generated = generated;
        this._regions = regions;
    }

    /**
     * Information about an entry within the case report, by index.
     * @param i report entry index
     * @returns the case report entry
     */
    public entryDetails(i: number): ReportEntry {
        return this._regions[i];
    }

    /**
     * Information about an entry within the case report, by name.
     * @param country top-level country name
     * @param region subnational (province, state, etc.) name
     * @returns the case report entry; will be `null` if it cannot be found
     */
    public entryDetailsByName(country: string, region?: string): ReportEntry {
        for (const entry of this._regions) {
            let countryMatches = country === entry.country;
            let regionMatches = region === entry.region;
            if (countryMatches && regionMatches) {
                return entry;
            }
        }
        return null;
    }

    /**
     * Get all case reports for all subnational regions associated with a
     * country.
     * @param country top-level country name
     * @returns the names of all available regions (province, state, etc.)
     */
    public listSubnationalRegions(country: string): string[] {
        let regions: string[] = [];
        for (const entry of this._regions) {
            if (entry.region === null) {
                continue;
            }
            if (entry.country !== country) {
                continue;
            }
            regions.push(entry.region);
        }
        return regions;
    }

    /**
     * The filtering parameters used to generate the report.
     */
    public get configuration(): ReportConfig { return this._config; }

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
        const timestamp = new Date().getTime();
        const response = await fetch(`${url}/${kAnalysisFile}?t=${timestamp}`);
        const jsonData = await response.json();
        const dateGenerated = new Date(jsonData['generated']);
        return new CaseReport(
            dateGenerated,
            (<object[]>jsonData['regions']).map(item => new ReportEntry(url, dateGenerated, item)),
            jsonData['config']
        );
    }
}
