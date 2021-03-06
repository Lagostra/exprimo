import json

from exprimo.graph import ComputationGraph
from exprimo.device import DeviceGraph
from exprimo.simulator import Simulator
from exprimo.plotting import plot_event_trace

from exprimo.optimizers.utils import prefix_heuristic, create_colocation_groups, apply_placement


if __name__ == '__main__':
    graph_file = '../nets/inception_v3.json'
    device_file = '../device_graphs/malvik.json'
    batches = 1
    pipeline_batches = 1

    with open(graph_file) as f:
        net_dict = json.load(f)

    net_string = json.dumps(net_dict)

    graph = ComputationGraph(force_device=None)
    graph.load_from_string(net_string)
    device_graph = DeviceGraph.load_from_file(device_file)
    simulator = Simulator(graph, device_graph)
    run_time, events = simulator.simulate(batch_size=128, batches=batches, pipeline_batches=pipeline_batches,
                                          return_event_trace=True, print_event_trace=True,
                                          comp_penalization=0.9, comm_penalization=0.25)

    plot_event_trace(events, simulator, show_transfer_lines=True, plot_op_time_distribution=True)

    print()
    print(f'Total batch run time: {run_time:,.2f}ms')
