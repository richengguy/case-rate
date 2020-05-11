class ModellingError(Exception):
    pass


class NegativePopulationError(ModellingError):
    def __init__(self):
        super().__init__('Cannot have a negative population.')


class Compartment:
    '''A compartment within a compartmental epidemiological model.'''
    def __init__(self, population: int):
        '''
        Parameters
        ----------
        population : int
            the initial value of the compartment

        Raises
        ------
        ValueError
            if the population is negative
        '''
        if population < 0:
            raise NegativePopulationError()
        self._population = population

    @property
    def population(self) -> int:
        return self._population

    @population.setter
    def population(self, value: int):
        if value < 0:
            raise NegativePopulationError()
        self._population = value


class Transition:
    '''Defines a transition between two compartments.'''
    def __init__(self, weight: float):
        '''
        Parameters
        ----------
        weight : float
            a scale factor used to control how much "flow" there is between any
            two compartments
        '''
        self.weight = weight
