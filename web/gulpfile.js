const gulp = require('gulp');

exports.clean = () => {
    const del = require('del');
    return del('build')
}

exports.css = () => {
    const postcss = require('gulp-postcss');
    return gulp.src('css/*.css')
        .pipe(postcss())
        .pipe(gulp.dest('build/css'));
}
