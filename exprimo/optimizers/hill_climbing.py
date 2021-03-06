import json
import os
from random import randint

from tqdm import tqdm

from exprimo import log, get_log_dir
from exprimo.optimizers.base import BaseOptimizer
from exprimo.optimizers.utils import generate_random_placement, apply_placement
from exprimo.graph import get_flattened_layer_names


class HillClimbingOptimizer(BaseOptimizer):

    def optimize(self, net_string, device_graph):
        n_devices = len(device_graph.devices)

        def generate_neighbours(placement):
            if n_devices == 1:
                return

            i = 0
            while i < len(placement):
                p = placement[i]
                if p < n_devices - 1:
                    n = placement[:]
                    n[i] = p + 1
                    yield n
                if p > 0:
                    n = placement[:]
                    n[i] = p - 1
                    yield n
                i += 1

        net = json.loads(net_string)
        groups = self.create_colocation_groups(get_flattened_layer_names(net_string))

        placement = generate_random_placement(len(groups), n_devices)
        score = self.evaluate_placement(apply_placement(net_string, placement, groups), device_graph)

        i = 0
        while True:
            i += 1
            if self.verbose:
                log(f'Iteration {i}. Best running time: {score:.2f}ms')

            for n in generate_neighbours(placement):
                new_score = self.evaluate_placement(apply_placement(net_string, n, groups), device_graph)
                if (new_score < score or score == -1) and new_score != -1:
                    placement = n
                    score = new_score
                    break
            else:
                break

        return placement


class RandomHillClimbingOptimizer(BaseOptimizer):

    def __init__(self, *args, steps=5000, **kwargs):
        super().__init__(*args, **kwargs)
        self.steps = steps

    def optimize(self, net_string, device_graph):
        if self.score_save_period:
            with open(os.path.join(get_log_dir(), 'time_history.csv'), 'w') as f:
                f.write(f'step, time\n')

        n_devices = len(device_graph.devices)
        groups = self.create_colocation_groups(get_flattened_layer_names(net_string))

        placement = [0] * len(groups)  # generate_random_placement(len(groups), n_devices)
        score = self.evaluate_placement(apply_placement(net_string, placement, groups), device_graph)

        for i in tqdm(range(self.steps), disable=not self.verbose):
            new_placement = placement[:]
            new_placement[randint(0, len(new_placement) - 1)] = randint(0, n_devices - 1)
            new_score = self.evaluate_placement(apply_placement(net_string, new_placement, groups), device_graph)

            if (new_score < score or score == -1) and new_score != -1:
                score = new_score
                placement = new_placement

            if self.verbose and (i + 1) % self.verbose == 0:
                log(f'[{i+1}/{self.steps}] Current time: {score:.2f}ms')

            if self.score_save_period and i % self.score_save_period == 0:
                with open(os.path.join(get_log_dir(), 'time_history.csv'), 'a') as f:
                    f.write(f'{i + 1}, {score}\n')

        solution = json.dumps(apply_placement(net_string, placement, groups), indent=4)

        with open(os.path.join(get_log_dir(), 'hc_solution.json'), 'w') as f:
            f.write(solution)

        return solution
