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
export class ReportDetails {
    private _country: string;
    private _region: string;
    private _source: Source;

    /**
     * Create a new report details instance.
     * @param regionIdent region identifier string of the form "`<country>`_`<region>`"
     */
    public constructor(source: Source, regionIdent: string)
    {
        this._source = source;

        var underscore = regionIdent.indexOf('_');
        if (underscore < 0) {
            this._country = regionIdent;
            this._region = null;
        } else {
            this._country = regionIdent.substring(0, underscore);
            this._region = regionIdent.substring(underscore+1);
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
}

/**
 * Contains the set of all available case rate analyses.
 */
export class CaseReport {
    private _generated: Date;
    private _regions: string[];

    public constructor(generated: Date, regions: string[]) {
        this._generated = generated;
        this._regions = regions;
    }

    /**
     * Information about an entry within the case report.
     * @param i report entry index
     */
    public entryDetails(i: number): ReportDetails {
        return new ReportDetails(null, this._regions[i]);
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
     * @param url JSON location
     * @returns a new case report instance
     */
    public static async LoadAsync(url: string): Promise<CaseReport> {
        const response = await fetch(url);
        const jsonData = await response.json();
        return new CaseReport(
            new Date(jsonData['generated']),
            jsonData['countries']
        );
    }
}
