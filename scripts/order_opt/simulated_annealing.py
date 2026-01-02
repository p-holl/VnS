import random
import numpy as np
from scipy.sparse import coo_matrix

from process_mp3.tracks import Track


LOSS_BY_TAG = {}


def similarity_loss(t1: Track, t2: Track | None):
    """Return number of shared tags (lower = better separation)."""
    if t2 is None:
        return 0
    weight = 0.
    for tag in set(t1.tags) & set(t2.tags):
        weight += LOSS_BY_TAG.get(tag, 1.)
    return weight


def greedy_fill(ordering: list[Track | None], remaining: list[Track]) -> list[Track]:
    """
    Create an ordering where items with similar tags end up far apart.
    Greedy: start with any item, repeatedly pick the least-similar next item.
    """
    remaining = list(remaining)
    random.shuffle(remaining)
    for i, t in enumerate(ordering):
        if t is None:
            last = ordering[i-1] if i > 0 else None
            next = ordering[i+1] if i < len(ordering)-1 else None
            best = min(remaining, key=lambda f: similarity_loss(f, last) + similarity_loss(f, next))
            ordering[i] = best
            remaining.remove(best)
    assert not remaining
    return ordering


def compute_weight_matrix(tracks: list[Track]):
    rows, cols, weights = [], [], []
    for i, t1 in enumerate(tracks):
        for j, t2 in enumerate(tracks):
            if i < j:
                weight = similarity_loss(t1, t2)
                if weight:
                    rows.append(i)
                    cols.append(j)
                    weights.append(weight)
    return coo_matrix((weights, (rows, cols)), shape=(len(tracks), len(tracks)))


def compute_total_loss(weights: coo_matrix, ordering: list[int]) -> float:
    pos = np.empty(len(ordering), dtype=int)
    pos[ordering] = np.arange(len(ordering))
    rows, cols, data = weights.row, weights.col, weights.data
    distance = np.abs(pos[rows] - pos[cols])
    losses = data * np.exp(-distance)
    return losses.sum()


def simulated_annealing(tracks: list[Track], initial_temp: float = 1000.0, cooling_rate: float = 0.995, iterations_per_temp: int = 100, min_temp: float = 1e-3):
    """ Use simulated annealing of non-fixed (number=None) tracks to find optimal ordering. """
    weights = compute_weight_matrix(tracks)
    current = list(range(len(tracks)))
    current_loss = compute_total_loss(weights, current)
    variable_indices = [i for i, t in enumerate(tracks) if t.number is None]
    if len(variable_indices) <= 1:
        return tracks, current_loss
    best = current.copy()
    best_loss = current_loss
    temp = initial_temp
    while temp > min_temp:
        print(best_loss / len(tracks))
        for _ in range(iterations_per_temp):
            # Generate neighbor by swapping two random elements
            new = current.copy()
            i, j = random.sample(variable_indices, 2)
            new[i], new[j] = new[j], new[i]
            new_loss = compute_total_loss(weights, new)
            delta_loss = new_loss - current_loss
            # Accept or reject move
            if delta_loss < 0 or random.random() < np.exp(-delta_loss / temp):
                current = new
                current_loss = new_loss
                if current_loss < best_loss:
                    best = current.copy()
                    best_loss = current_loss
        temp *= cooling_rate
    # Convert indices back to element names
    best_ordering = [tracks[i] for i in best]
    return best_ordering, best_loss
