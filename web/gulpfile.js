const gulp = require('gulp');
const buildOutput = 'dist/'

// NOTE: Replace with NPM commands and use rollup.js for packing.

function _renderHtml(template) {
    var fn = (cb) => {
        const exec = require('child_process').exec;
        exec(`python render.py ${template}.jinja2 ${buildOutput}${template}.html`,
            (err, stdout, stderr) => {
                if (stdout.length > 0) { console.log(stdout); }
                if (stderr.length > 0) { console.log(stderr); }
                cb(err);
            }
        );
    };
    fn.displayName = template;
    return fn;
}

function compileTypescript() {
    const browserify = require('browserify');
    const buffer = require('vinyl-buffer');
    const source = require('vinyl-source-stream');
    const sourcemaps = require('gulp-sourcemaps');
    const terser = require('gulp-terser');
    const tsify = require('tsify');

    return browserify({
        'basedir': 'src',
        'debug': true
    })
        .add('report.ts')
        .plugin(tsify)
        .bundle()
        .pipe(source('report.js'))
        .pipe(buffer())
        .pipe(sourcemaps.init({ loadMaps: true}))
        .pipe(terser({
            keep_fnames: true,
            keep_classnames: true
        }))
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest(buildOutput));
}

exports.clean = () => {
    const del = require('del');
    return del(buildOutput)
}

exports.css = () => {
    const postcss = require('gulp-postcss');
    return gulp.src('css/*.css')
        .pipe(postcss())
        .pipe(gulp.dest(buildOutput + 'css'));
}

exports.html = gulp.series(
    compileTypescript,
    _renderHtml('report')
);
