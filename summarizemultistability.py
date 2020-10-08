import argparse
import collections
import copy
import json
import matplotlib.colors as mplcolors
import matplotlib.patches as mplpatch
import matplotlib.pyplot as plt
import numpy as np
import random
from sklearn import decomposition

def summarizeattractors(pset_report):
    '''Get a 2-tuple summarizing a set of attractors: attractor count, monotonic species count.'''
    attractors = pset_report['attractors']
    species = len(attractors[0])
    correlated_species = set()
    most_monotonic_species = 0
    for i in range(species):
        if i in correlated_species:
            continue
        sorted_attractors = sorted(attractors, key=lambda a: a[i])
        correlated_species.add(i)
        monotonic_species = 1
        for j in set(range(species)).difference(correlated_species):
            attractor_concs = [a[j] for a in sorted_attractors]
            if attractor_concs == sorted(attractor_concs) or attractor_concs == sorted(attractor_concs, reverse=True):
                monotonic_species += 1
                correlated_species.add(j)
        most_monotonic_species = max(most_monotonic_species, monotonic_species)
    return len(attractors), most_monotonic_species

def categorizeattractors(report):
    '''Get a dictionary of attractor summary tuples to lists of their occurrences.'''
    summary_occurrences = collections.defaultdict(list)
    for pset in report['psets']:
        summary_occurrences[summarizeattractors(pset)].append(pset)
    return summary_occurrences

def plotmultistability(report, label_counts=False, colorbar=True):
    '''Set up a multistability heatmap in the current pyplot.'''
    summary_occurrences = categorizeattractors(report)
    max_attractors = max(s[0] for s in summary_occurrences.keys())
    min_attractors = min(s[0] for s in summary_occurrences.keys())
    max_monotonic = len(report['species_names'])
    min_monotonic = 1
    width = max_attractors - min_attractors + 1
    x_range = range(min_attractors, max_attractors + 1)
    height = max_monotonic - min_monotonic + 1
    y_range = reversed(range(min_monotonic, max_monotonic + 1))
    heatmap_pixels = np.zeros((height, width), dtype=int)
    for summary, occurrences in summary_occurrences.items():
        heatmap_pixels[max_monotonic - summary[1]][summary[0] - min_attractors] = len(occurrences)
    fig, ax = plt.subplots()
    im = ax.imshow(heatmap_pixels, norm=mplcolors.LogNorm(vmax=heatmap_pixels.max()))
    if colorbar:
        fig.colorbar(im)
    ax.set_xticks(range(width))
    ax.set_yticks(range(height))
    ax.set_xticklabels([str(n) for n in x_range])
    ax.set_yticklabels([str(n) for n in y_range])
    ax.set_xlabel('Attractors')
    ax.set_ylabel('Monotonically correlated species')
    if label_counts:
        for y in range(height):
            for x in range(width):
                if heatmap_pixels[y][x] > 0:
                    ax.text(x, y, str(heatmap_pixels[y][x]), ha='center', va='center', color='gray')

def plotattractors(report, reduction, connect_psets='none', filter_attractors=None, filter_correlated_species=None, downsample=None):
    reduction.prepare(report)
    summary_occurrences = categorizeattractors(report)
    filtered_psets = []
    random.seed(1)
    for summary, occurrences in summary_occurrences.items():
        attractors, monotonic = summary
        if filter_attractors is not None and attractors != filter_attractors:
            continue
        if filter_correlated_species is not None and monotonic != filter_correlated_species:
            continue
        if downsample is not None and attractors in downsample:
            filtered_psets.extend(o for o in occurrences if random.uniform(0, 1) < downsample[attractors])
        else:
            filtered_psets.extend(occurrences)
    xlabel, ylabel = reduction.labels()
    if connect_psets == 'line':
        for pset in filtered_psets:
            pset_matrix = np.array(pset['attractors'])
            pset_xy = reduction.reduce(pset_matrix)
            sorted_attractors = pset_xy[pset_xy[:, 0].argsort()]
            plt.plot(sorted_attractors[:, 0], sorted_attractors[:, 1], 'o-')
    else:
        points = reduction.reduce(psets_matrix(filtered_psets))
        cmap = copy.copy(plt.get_cmap('viridis'))
        cmap.set_under('white', 1.0)
        hex_args = {'linewidths': 0.2, 'norm': mplcolors.LogNorm(vmin=2), 'cmap': cmap}
        if connect_psets == 'arc':
            fig = plt.figure()
            grid = fig.add_gridspec(nrows=1, ncols=2, width_ratios=(6, 1), wspace=0.05)
            ax_main = fig.add_subplot(grid[0, 0])
            ax_main.set_xlabel(xlabel)
            ax_main.set_ylabel(ylabel)
            ax_main.hexbin(points[:, 0], points[:, 1], **hex_args)
            ax_arcs = fig.add_subplot(grid[0, 1], sharey=ax_main)
            ax_arcs.tick_params(labelbottom=False, labelleft=False, bottom=False)
            color_cycle = ax_arcs._get_lines.prop_cycler
            for pset in filtered_psets:
                pset_matrix = np.array(pset['attractors'])
                pset_xy = reduction.reduce(pset_matrix)
                sorted_ys = sorted(pset_xy[:, 1])
                height = random.uniform(0.2, 1.8)
                color = next(color_cycle)['color']
                for i in range(len(sorted_ys) - 1):
                    a, b = sorted_ys[i:(i + 2)]
                    ax_arcs.add_patch(mplpatch.Arc((0, (a + b) / 2), height, b - a, 180.0, 90.0, 270.0, edgecolor=color, linewidth=0.5))
        else:
            plt.hexbin(points[:, 0], points[:, 1], **hex_args)
    if connect_psets != 'arc':
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

def psets_matrix(psets):
    full_matrix = None
    for pset in psets:
        if full_matrix is None:
            full_matrix = np.array(pset['attractors'])
        else:
            full_matrix = np.vstack((full_matrix, np.array(pset['attractors'])))
    return full_matrix

class PCA2D():
    def __init__(self):
        self.pca = decomposition.PCA(n_components=2)
    def prepare(self, report):
        self.pca.fit(psets_matrix(report['psets']))
    def reduce(self, matrix):
        return self.pca.transform(matrix)
    def labels(self):
        return 'PC1', 'PC2'

class AverageLog():
    def __init__(self, settings=None):
        self.settings = settings
    def prepare(self, report):
        self.names = report['species_names']
        if self.settings is None:
            raise NotImplementedError('You must specify genes for reduction axes')
        else:
            x, y = self.settings.split('/')
            self.x_components = [self._parsecomponent(report, c.strip()) for c in x.split(',')]
            self.y_components = [self._parsecomponent(report, c.strip()) for c in y.split(',')]
    def reduce(self, matrix):
        return np.stack((self._componentwisereduce(matrix, self.x_components), self._componentwisereduce(matrix, self.y_components)), 1)
    def labels(self):
        return ', '.join((self._componentname(c) for c in self.x_components)), ', '.join((self._componentname(c) for c in self.y_components))
    def _parsecomponent(self, report, text):
        if text.startswith('-'):
            text = text[1:]
            factor = -1
        else:
            factor = 1
        index = self.names.index(text) if text in self.names else self.names.index(f'X_{text}')
        return index, factor
    def _componentwisereduce(self, matrix, components):
        results = None
        for index, factor in components:
            component_log = np.log(matrix[:, index]) * factor
            if results is None:
                results = component_log
            else:
                results += component_log
        return np.exp(results / len(components))
    def _componentname(self, component):
        index, factor = component
        prefix = '-' if factor < 0 else ''
        name = self.names[index]
        return prefix + (name[2:] if name.startswith('X_') else name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=str, help='input JSON report filename')
    parser.add_argument('graph', type=str, help='output graph image filename')
    subcmds = parser.add_subparsers(dest='command', required=True, help='kind of graph to make')
    heatmap_parser = subcmds.add_parser('heatmap')
    heatmap_parser.add_argument('--counts', action='store_true', help='display counts in populated cells')
    heatmap_parser.add_argument('--colorbar', action='store_true', help='show colorbar even when counts are displayed')
    scatterplot_parser = subcmds.add_parser('scatterplot')
    scatterplot_parser.add_argument('--attractors', type=int, help='filter parameter sets by number of attractors')
    scatterplot_parser.add_argument('--correlated', type=int, help='filter parameter sets by number of monotonically correlated species')
    scatterplot_parser.add_argument('--connect', choices=['none', 'line', 'arc'], default='none', help='how to connect attractors from the same parameter set')
    scatterplot_parser.add_argument('--reduction', type=str, help='species for dimensions: X1,X2/Y1,Y2 or "pca" to run PCA')
    scatterplot_parser.add_argument('--downsample', type=str, help='chance of keeping a parameter set with specified attractor count, e.g. 2:0.1,3:0.5')
    args = parser.parse_args()
    with open(args.report) as f:
        report = json.loads(f.read())
    if args.command == 'heatmap':
        plotmultistability(report, label_counts=args.counts, colorbar=(args.colorbar or not args.counts))
    elif args.command == 'scatterplot':
        reduction = PCA2D() if args.reduction == 'pca' else AverageLog(args.reduction)
        downsample = {int(n): float(p) for n, p in [part.split(':') for part in args.downsample.split(',')]} if args.downsample else None
        plotattractors(report, reduction, connect_psets=args.connect, filter_attractors=args.attractors, filter_correlated_species=args.correlated, downsample=downsample)
    plt.savefig(args.graph, dpi=150)
    plt.close()
