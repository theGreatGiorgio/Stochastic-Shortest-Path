# -*- coding: utf-8 -*-
import functools
from typing import Tuple, List, Set, Iterable, Iterator
from functools import reduce


class MDP:
    def __init__(self, states: List[str], actions: List[str], w: List[int],
                 number_of_states: int = -1):
        self._states_name = states
        self._actions_name = actions
        number_of_states = max(number_of_states, len(self._states_name))
        self._w = w
        self._enabled_actions: List[Tuple[List[int], List[List[Tuple[int, float]]]]] = \
            [([], []) for _ in range(number_of_states)]
        self._pred: List[Set[int]] = \
            [set() for _ in range(number_of_states)]
        self._alpha_pred: List[List[Tuple[int, int]]] = \
            [[] for _ in range(number_of_states)]

    def enable_action(self, s: int, alpha: int,
                      delta_s_alpha: Iterable[Tuple[int, float]]) -> None:
        act_s, alpha_succ = self._enabled_actions[s]
        act_s.append(alpha)
        i = len(alpha_succ)
        alpha_succ.append([])
        for (succ, pr) in delta_s_alpha:
            alpha_succ[i].append((succ, pr))
            self._pred[succ].add(s)
            self._alpha_pred[succ].append((s, len(act_s) - 1))

    def act(self, s: int) -> List[int]:
        return self._enabled_actions[s][0]

    def pred(self, s: int) -> Set[int]:
        return self._pred[s]

    def w(self, alpha: int) -> int:
        return self._w[alpha]

    def alpha_predecessors(self, s: int) -> Iterator[Tuple[int, int]]:
        return map(lambda alpha_pred: (alpha_pred[0],
                                       self.act(alpha_pred[0])[alpha_pred[1]]),
                   self._alpha_pred[s])

    def alpha_successors_iterator(self, s: int) -> Iterable[Tuple[int, int, float]]:
        return MDPIterator(self._enabled_actions[s])

    def alpha_successors(self, s: int) -> Iterator[Tuple[int, List[Tuple[int, float]]]]:
        return map(lambda alpha_i: (self._enabled_actions[s][0][alpha_i],
                                    self._enabled_actions[s][1][alpha_i]),
                   range(len(self.act(s))))

    @property
    def number_of_states(self) -> int:
        return len(self._enabled_actions)

    def state_name(self, s: int) -> str:
        self.generate_names()
        return self._states_name[s]

    def act_name(self, alpha: int) -> str:
        self.generate_names()
        return self._actions_name[alpha]

    def generate_names(self):
        if len(self._states_name) < len(self._enabled_actions):
            self._states_name = ['s' + str(i) for i in range(len(self._enabled_actions))]
        if len(self._actions_name) == 0:
            self._actions_name = ['a' + str(i) for i in range(len(self._w))]

    def __str__(self):
        actions_successors_for = list(map(lambda actions_successors: str((
            list(map(lambda action: self.act_name(action) + "|" + str(self._w[action]), actions_successors[0])),
            list(map(lambda succ_pr_list:
                     list(map(lambda succ_pr: (self.state_name(succ_pr[0]), succ_pr[1]), succ_pr_list))
                     , actions_successors[1])))),
                                          self._enabled_actions))
        return reduce(lambda x, y: x + y, ([self.state_name(s) + " -> " + actions_successors_for[s] + "\n"
                                            for s in range(self.number_of_states)]))[:-1]


class UnfoldedMDP(MDP):
    def __init__(self, mdp: MDP, s0: int, T: List[int], l: int, v: int=0):
        mdp.generate_names()
        self._states_name = mdp._states_name + ['⊥']
        self._actions_name = mdp._actions_name + ['loop']
        self._w = mdp._w + [1]
        self._enabled_actions: List[Tuple[List[int], List[List[Tuple[int, float]]]]] = []
        self._pred: List[Set[int]] = []
        self._alpha_pred: List[List[Tuple[int, int]]] = []
        self._T = []

        bot_alpha_pred = []
        in_T = [False] * mdp.number_of_states
        for t in T:
            in_T[t] = True
        A = [{} for _ in range(mdp.number_of_states)]
        self._convert = []
        self._number_of_states = 0

        def fill(s: int):
            if s == len(self._enabled_actions):
                self._enabled_actions.append(([], []))
                self._pred.append(set())
                self._alpha_pred.append([])

        def unfold(s, v):
            i = A[s][v] = A[s].get(v, self._number_of_states)
            if i == self._number_of_states:
                self._convert.append((s, v))
                # self._states_name.append("(" + mdp.state_name(s) + ", " + str(v) + ")")
                self._number_of_states += 1
                fill(i)
                if in_T[s]:
                    self.enable_action(i, len(self._w) - 1, [(i, 1)])
                    self._T.append(i)
                else:
                    for (alpha, succ_list) in mdp.alpha_successors(s):
                        if v + mdp.w(alpha) > l:
                            bot_alpha_pred.append((i, alpha))
                        else:
                            v_new = v + mdp.w(alpha)
                            to_enable = []
                            for (succ, pr) in succ_list:
                                j = unfold(succ, v_new)
                                to_enable.append((j, pr))
                            self.enable_action(i, alpha, to_enable)
            return i

        import sys
        sys.setrecursionlimit(3000)
        unfold(s0, v)
        self._convert.append((-1, Bot()))
        self._enabled_actions.append(([len(self._w) - 1], [[(len(self._enabled_actions), 1)]]))
        self._pred.append(set())
        self._alpha_pred.append([])
        for (pred, alpha) in bot_alpha_pred:
            self.enable_action(pred, alpha, [(self._number_of_states, 1)])

    @property
    def target_states(self):
        return self._T

    def state_name(self, s: int) -> str:
        s, v = self._convert[s]
        if s != -1:
            return '(' + self._states_name[s] + ', ' + str(v) + ')'
        else:
            return '⊥'

    def convert(self, s: int) -> Tuple[int, int]:
        return self._convert[s]


class MDPIterator:
    def __init__(self, actions_enabled: Tuple[List[int], List[List[Tuple[int, float]]]]):
        self._actions_enabled = actions_enabled
        self._current_action = 0
        self._current_tuple = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._current_action == len(self._actions_enabled[1]):
            raise StopIteration
        elif self._current_tuple == len(self._actions_enabled[1][self._current_action]):
            self._current_action += 1
            self._current_tuple = 0
            return self.__next__()
        alpha = self._actions_enabled[0][self._current_action]
        succ, pr = self._actions_enabled[1][self._current_action][self._current_tuple]
        self._current_tuple += 1
        return alpha, succ, pr


@functools.total_ordering
class NeverSmaller(object):
    def __le__(self, other):
        return False


class Bot(NeverSmaller, int):
    def __repr__(self):
        return '⊥'

    def __str__(self):
        return self.__repr__()
