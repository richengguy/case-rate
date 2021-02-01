import { CaseReport } from './analysis';
import { TimeSeries } from './timeseries';

window.onload = () => {
    CaseReport.LoadAsync('analysis.json')
        .then(report => {
            console.log('Generated on: ' + report.generatedOn);
        });
};
