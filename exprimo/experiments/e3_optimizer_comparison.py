import json
import multiprocessing
import os
from itertools import repeat, product

import pandas as pd
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

from exprimo import set_log_dir, log, PLOT_STYLE
from exprimo.optimize import optimize_with_config

sns.set(style=PLOT_STYLE)

LOG_DIR = os.path.expanduser('~/logs/e3_optimizer-comparison')
set_log_dir(LOG_DIR)

run_config = 'pipelined' # (1, 0, 0, 1)
NETWORK = ('resnet50', 'alexnet', 'inception')[run_config[0] if isinstance(run_config[0], int) else 0]
BATCHES = (1, 10)[run_config[1] if isinstance(run_config[1], int) else 0]
PIPELINE_BATCHES = (1, 2, 4)[run_config[2] if isinstance(run_config[2], int) else 0]
MEMORY_LIMITED = bool(run_config[3] if len(run_config) > 3 and isinstance(run_config[3], int) else 0)

REPEATS = 50

OPTIMIZERS = ('hc', 'sa', 'ga', 'me')
OPTIMIZER_NAMES = {
    'hc': 'Hill Climbing',
    'sa': 'Simulated Annealing',
    'ga': 'Genetic Algorithm',
    'me': 'MAP-elites',
}

NETWORK_NAMES = {
    'resnet50': 'ResNet-50',
    'alexnet': 'AlexNet',
    'inception': 'Inception V3'
}

cmap = sns.cubehelix_palette(5, start=.5, rot=-.75, reverse=True)


def test_optimizer(c, r, log_dir):
    c['log_dir'] = log_dir + f'/{r:03}'
    _, t = optimize_with_config(config=c, verbose=False, set_log_dir=True)
    return t


def run_optimizer_test(n_threads=-1):
    if n_threads == -1:
        n_threads = multiprocessing.cpu_count()

    for optimizer in tqdm(OPTIMIZERS):
        # log(f'Testing optimizer {optimizer}')
        run_name = f'e3_{optimizer}-{NETWORK}{"-pipeline" if PIPELINE_BATCHES > 1 else ""}' \
                   f'{"-limited" if MEMORY_LIMITED else ""}'
        config_path = f'configs/experiments/e3/{run_name}.json'
        score_path = os.path.join(LOG_DIR, f'{run_name}_scores.csv')

        with open(score_path, 'w') as f:
            f.write('run, time\n')

        with open(config_path) as f:
            config = json.load(f)

        config['optimizer_args']['verbose'] = False
        config['optimizer_args']['batches'] = BATCHES
        config['optimizer_args']['pipeline_batches'] = PIPELINE_BATCHES
        log_dir = config['log_dir']

        threaded_optimizer = config['optimizer'] in ('ga', 'genetic_algorithm', 'map-elites', 'map_elites')

        if n_threads == 1 or threaded_optimizer:
            for r in tqdm(range(REPEATS)):
                time = test_optimizer(config, r, log_dir)
                with open(score_path, 'a') as f:
                    f.write(f'{r},{time}\n')
        else:
            worker_pool = multiprocessing.Pool(n_threads)
            times = worker_pool.starmap(test_optimizer, zip(repeat(config), (r for r in range(REPEATS)),
                                                            repeat(log_dir)))
            worker_pool.close()
            with open(score_path, 'a') as f:
                for r, t in enumerate(times):
                    f.write(f'{r},{t}\n')

        set_log_dir(LOG_DIR)


def plot_results():
    all_results = pd.DataFrame()
    # CREATE PLOT OF RESULTS
    for optimizer in OPTIMIZERS:
        run_name = f'e3_{optimizer}-{NETWORK}{"-pipeline" if PIPELINE_BATCHES > 1 else ""}' \
                   f'{"-limited" if MEMORY_LIMITED else ""}'
        score_path = os.path.join(LOG_DIR, f'{run_name}_scores.csv')
        scores = pd.read_csv(score_path, index_col=0, squeeze=True)

        scores /= PIPELINE_BATCHES

        all_results[OPTIMIZER_NAMES[optimizer]] = scores

    plt.figure(figsize=(8, 8))
    chart = sns.barplot(data=all_results, palette=cmap)
    chart.set_xticklabels(
        chart.get_xticklabels(),
        rotation=45,
        horizontalalignment='right',
    )
    plt.ylabel('Batch execution time (ms)')
    plt.xlabel('Optimization algorithm')
    plt.tight_layout()
    plt.savefig(os.path.join(LOG_DIR, 'score_comparison.pdf'))
    plt.show()
    plt.close()


def plot_result_all_networks(test_type='normal'):
    all_results = pd.DataFrame()
    # CREATE PLOT OF RESULTS
    for network in ('alexnet', 'resnet50', 'inception'):
        for optimizer in OPTIMIZERS:
            run_name = f'e3_{optimizer}-{network}{"-pipeline" if test_type == "pipelined" else ""}' \
                       f'{"-limited" if test_type == "limited" else ""}'
            score_path = os.path.join(LOG_DIR, f'{run_name}_scores.csv')
            scores = pd.read_csv(score_path, index_col=0, squeeze=True)
            if test_type == 'pipelined':
                scores /= 10
            new_results = pd.DataFrame()
            new_results['score'] = scores
            new_results['optimizer'] = OPTIMIZER_NAMES[optimizer]
            new_results['network'] = network

            all_results = pd.concat([all_results, new_results])

    if test_type in ('normal', 'pipelined'):
        if os.path.exists(os.path.join(LOG_DIR, 'single-gpu.csv')):
            all_results = pd.concat([all_results, pd.read_csv(os.path.join(LOG_DIR, 'single-gpu.csv'))])

    fig, ax = plt.subplots(1, 3, figsize=(10, 6))

    for a, net in zip(ax, ('alexnet', 'resnet50', 'inception')):
        chart = sns.barplot(x='optimizer', y='score', data=all_results[all_results['network'] == net],
                            palette=cmap, ax=a)
        a.set_xlabel('')
        a.set_ylabel('')
        chart.set_xticklabels(
            chart.get_xticklabels(),
            rotation=45,
            horizontalalignment='right',
        )
        a.set_title(NETWORK_NAMES[net])
    fig.text(0.01, 0.5, 'Batch training time (ms)', va='center', rotation='vertical')
    plt.tight_layout()
    plt.savefig(os.path.join(LOG_DIR, f'score_comparison_{test_type}.pdf'), bb_inches='tight')
    plt.show()
    plt.close()


def plot_histories(test_type='normal', network='alexnet', ylim=None):
    all_data = pd.DataFrame()
    for optimizer in OPTIMIZERS:
        run_name = f'{optimizer}-{network}{"-pipeline" if test_type == "pipelined" else ""}' \
                   f'{"-limited" if test_type == "limited" else ""}'
        for run_dir in os.listdir(os.path.join(LOG_DIR, run_name)):
            with open(os.path.join(LOG_DIR, run_name, run_dir, 'time_history.csv')) as f:
                run_data = pd.read_csv(f, index_col=0)
                if test_type == 'pipelined':
                    run_data /= 10
                run_data['Optimizer'] = OPTIMIZER_NAMES[optimizer]

                run_data = run_data.rename(columns=lambda x: x.strip())

                if run_data.index.name == 'generation':
                    # Multiply by population size to get comparable plots
                    run_data.index *= 50
                    run_data.index.name = 'step'
            all_data = pd.concat([all_data, run_data])

    sns.lineplot(x=all_data.index, y='time', hue='Optimizer', style='Optimizer', data=all_data)
    if ylim:
        plt.ylim(0, ylim)
    plt.tight_layout()
    plt.xlabel('Step')
    plt.ylabel('Batch training time (ms)')
    plt.savefig(os.path.join(LOG_DIR, f'score_history_{test_type}_{network}.pdf'))
    plt.show()
    plt.close()


def run_variants(variants=('normal', 'limited', 'pipelined')):
    networks = 'resnet50', 'alexnet', 'inception'
    global BATCHES, PIPELINE_BATCHES, MEMORY_LIMITED, NETWORK, REPEATS
    for variation in tqdm(product(networks, variants)):
        log(f'Testing {variation[0]} network in {variation[1]} configuration')
        NETWORK = variation[0]
        if variation[1] == 'normal':
            BATCHES = 1
            PIPELINE_BATCHES = 1
            MEMORY_LIMITED = False
            REPEATS = 50
        elif variation[1] == 'limited':
            BATCHES = 1
            PIPELINE_BATCHES = 1
            MEMORY_LIMITED = True
            REPEATS = 50
        elif variation[1] == 'pipelined':
            BATCHES = 10
            PIPELINE_BATCHES = 4
            MEMORY_LIMITED = False
            REPEATS = 10

        run_optimizer_test()


if __name__ == '__main__':
    if run_config == 'all':
        run_variants()
        for test_type in ('normal', 'limited', 'pipeline'):
            plot_result_all_networks(test_type)
    elif isinstance(run_config, str):
        run_variants((run_config,))
        plot_result_all_networks(run_config)
    else:
        run_optimizer_test()
        plot_results()
