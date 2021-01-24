const gulp = require('gulp');
const buildOutput = 'dist/'

exports.clean = () => {
    const del = require('del');
    return del(buildOutput)
}

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

exports.css = () => {
    const postcss = require('gulp-postcss');
    return gulp.src('css/*.css')
        .pipe(postcss())
        .pipe(gulp.dest(buildOutput + 'css'));
}

exports.html = gulp.series(_renderHtml('report'));
