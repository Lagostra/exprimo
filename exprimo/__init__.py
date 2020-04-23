import time

PLOT_STYLE = 'darkgrid'

LOG_CONFIG = {
    'clear_files': True,
    'streams': [
        print,
        'output.log'
    ]
}

if LOG_CONFIG['clear_files']:
    for stream in LOG_CONFIG['streams']:
        if isinstance(stream, str):
            with open(stream, 'w') as f:
                f.write('')


def log(*strings, end='\n', sep=''):
    for stream in LOG_CONFIG['streams']:
        if isinstance(stream, str):
            with open(stream, 'a') as f:
                timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
                string = sep.join(str(s) for s in strings)
                f.write(f'{timestamp}  {string}{end}')
        else:
            stream(*strings, end=end, sep=sep)

from exprimo.simulator import Simulator
from exprimo.plotting import plot_event_trace
from exprimo.device import DeviceGraph
from exprimo.graph import ComputationGraph
