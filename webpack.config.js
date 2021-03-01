const path = require('path');

module.exports = {
    mode: 'production',
    optimization: {
        usedExports: true,
    },
    externals: {
        'chart.js': 'Chart',
    },
    entry: {
        dashboard: './build/lib/dashboard/pages/dashboard.js',
        details: './build/lib/dashboard/pages/details.js'
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist')
    }
};
