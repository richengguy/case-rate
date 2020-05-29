import click

from ._helpers import _parse_region_selector
from .. import sources
from .. import filters
from ..storage import Storage


@click.command('modelling')
@click.argument('country', nargs=1)
@click.pass_obj
def command(config: dict, country: str):
    '''Generate an SIR model for the given country/region.'''
    input_source = sources.init_source(config['storage'], False, country,
                                       config['sources'])

    with Storage() as storage:
        country, province = _parse_region_selector(country)
        storage.populate(input_source)
        cases = storage.cases(input_source, country=country,
                              province=province)
        cases = filters.sum_by_date(cases)

    import matplotlib.pyplot as plt
    import numpy as np
    confirmed = np.array([case.confirmed for case in cases])
    recovered = np.array([case.resolved for case in cases])
    deceased = np.array([case.deceased for case in cases])

    plt.figure()
    plt.plot(confirmed, label='Confirmed')
    plt.plot(recovered, label='Recovered')
    plt.plot(deceased, label='Deceased')
    plt.legend()

    plt.figure()
    plt.plot(confirmed - (recovered + deceased))

    plt.show()
