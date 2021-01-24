import pathlib
import datetime

import click
import dateutil.tz
import jinja2


@click.command()
@click.option('--templates', help='Path to templates folder', metavar='DIR',
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              default='html')
@click.option('--timezone', help='Time zone string', metavar='TZ',
              type=str, default='America/Toronto')
@click.argument('src', type=str)
@click.argument('dst', type=click.Path(dir_okay=False))
def main(templates: str, timezone: str, src: str, dst: str):
    '''Quickly generate Jinja-based HTML templates.'''
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates),
        autoescape=jinja2.select_autoescape(['html'])
    )

    output_file = pathlib.Path(dst)

    tz = dateutil.tz.gettz(timezone)
    today = datetime.datetime.now(tz)

    jinja_template = env.get_template(src)
    html = jinja_template.render(date=today)
    with output_file.open('wt') as f:
        f.write(html)


if __name__ == '__main__':
    main()
