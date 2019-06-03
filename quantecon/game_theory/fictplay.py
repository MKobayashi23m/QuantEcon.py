import numpy as np
from .normal_form_game import NormalFormGame
from ..util import check_random_state
from .random import _random_mixed_actions
from .utilities import _copy_action_profile_to


class FictitiousPlay:
    """
    Class representing the fictitious play model.

    Parameters
    ----------
    data : NormalFormGame or array-like
        The game played in fictitious play model

    gain : scalar(float), optional(default=None)
        The gain of fictitous play model. If gain is None, the model becomes
        decreasing gain model. If gain is scalar, the model becomes constant
        constant gain model.

    Attributes
    ----------
    g : NomalFormGame
        The game. See Parameters.

    N : scalar(int)
        The number of players in the model.

    players : Player
        Player instance in the model.

    nums_actions : tuple(int)
        Tuple of the number of actions, one for each player.
    """

    def __init__(self, data, gain=None):
        if isinstance(data, NormalFormGame):
            self.g = data
        else:  # data must be array_like
            payoffs = np.asarray(data)
            self.g = NormalFormGame(payoffs)

        self.N = self.g.N
        self.players = self.g.players
        self.nums_actions = self.g.nums_actions
        self.tie_breaking = 'smallest'

        if gain is None:
            self.step_size = lambda t: 1 / (t+2)  # decreasing gain
        else:
            self.step_size = lambda t: gain  # constant gain

    def _play(self, actions, t, brs, tie_breaking, tol, random_state):
        for i, player in enumerate(self.players):
            opponents_actions = tuple(actions[i+1:]) + tuple(actions[:i])
            brs[i] = player.best_response(
                opponents_actions if self.N > 2 else opponents_actions[0],
                tie_breaking=tie_breaking, tol=tol, random_state=random_state
            )

        for i in range(self.N):
            actions[i][:] *= 1 - self.step_size(t)
            actions[i][brs[i]] += self.step_size(t)

        return actions

    def play(self, actions=None, num_reps=1, t_init=0, out=None, **options):
        """
        Return a new action profile which is updated by playing the game
        `num_reps` times.

        Parameters
        ----------
        actions : tuple(array_like(float)), optional(default=None)
            The action profile in the first period. If None, selected randomly.

        num_reps : scalar(int), optional(default=1)
            The number of iterations.

        t_init : scalar(int), optional(default=0)
            The period the game starts.

        out : tuple(array-like(float)), optional(default=None)
            The tuple of actions which will be used in `_play` method.

        Returns
        -------
        tuple(ndarray(float))
            The mixed action profile after iteration.

        """
        tie_breaking = options.get('tie_breaking', self.tie_breaking)
        tol = options.get('tol', None)
        random_state = check_random_state(options.get('random_state', None))

        if out is None:
            out = tuple(np.empty(n) for n in self.nums_actions)

        if actions is None:
            _random_mixed_actions(out, random_state)
        else:
            _copy_action_profile_to(out, actions)

        brs = np.empty(self.N, dtype=int)
        for t in range(t_init, t_init+num_reps):
            out = self._play(out, t, brs, tie_breaking, tol, random_state)

        return out

    def time_series(self, ts_length, init_actions=None, t_init=0, **options):
        """
        Return the array representing time series of mixed action profile.

        Parameters
        ----------
        ts_length : scalar(int)
            The number of iterations.

        init_actions : tuple(int), optional(default=None)
            The action profile in the first period. If None, selected randomly.

        t_init : scalar(int), optional(default=0)
            The period the game starts.

        Returns
        -------
        tuple(ndarray(float, ndim=2))
            The array representing time series of mixed action profile.

        """
        tie_breaking = options.get('tie_breaking', self.tie_breaking)
        tol = options.get('tol', None)
        random_state = check_random_state(options.get('random_state', None))

        out = tuple(np.empty((ts_length, n)) for n in self.nums_actions)
        out_init = tuple(out[i][0, :] for i in range(self.N))

        if init_actions is None:
            _random_mixed_actions(out_init, random_state)
        else:
            _copy_action_profile_to(out_init, init_actions)

        actions = tuple(np.copy(action) for action in out_init)
        brs = np.empty(self.N, dtype=int)
        for j in range(1, ts_length):
            self._play(actions, t_init+j-1, brs,
                       tie_breaking, tol, random_state)
            for i in range(self.N):
                np.copyto(out[i][j, :], actions[i])

        return out


class StochasticFictitiousPlay(FictitiousPlay):
    """
    Class representing the stoochastic fictitous play model.
    Subclass of FictitiousPlay.

    Parameters
    ----------
    data : NormalFormGame or array-like
        The game played in the stochastic fictitious play model.

    distribution : scipy.stats object
        statistical distribution from scipy.stats

    gain : scalar(scalar), optional(default=None)
        The gain of fictitous play model. If gain is None, the model becomes
        decreasing gain model. If gain is scalar, the model becomes constant
        constant gain model.

    Attributes
    ----------
    See attributes of FictitousPlay.
    """

    def __init__(self, data, distribution, gain=None):
        FictitiousPlay.__init__(self, data, gain)

        self.payoff_perturbation_dist = \
            lambda size, random_state: distribution.rvs(
                                        size=size,
                                        random_state=random_state)

    def _play(self, actions, t, brs, tie_breaking, tol, random_state):
        for i, player in enumerate(self.players):
            opponents_actions = tuple(actions[i+1:]) + tuple(actions[:i])
            payoff_perturbation = \
                self.payoff_perturbation_dist(size=self.nums_actions[i],
                                              random_state=random_state)
            brs[i] = player.best_response(
                opponents_actions if self.N > 2 else opponents_actions[0],
                tie_breaking=tie_breaking,
                payoff_perturbation=payoff_perturbation,
                tol=tol, random_state=random_state
            )

        for i in range(self.N):
            actions[i][:] *= 1 - self.step_size(t)
            actions[i][brs[i]] += self.step_size(t)

        return actions
