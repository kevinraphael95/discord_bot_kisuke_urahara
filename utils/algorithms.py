# ────────────────────────────────────────────────────────────────
# utils/algorithms.py — Tous les algorithmes de tri asynchrones
# Règle : UNIQUEMENT des swaps data[i], data[j] = data[j], data[i]
#         Jamais de copie intermédiaire, jamais de insert/pop
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# Tris classiques
# ────────────────────────────────────────────────────────────────
async def bubble_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
                yield data, [j, j + 1]
bubble_sort.desc = "Compare chaque élément avec le suivant et fait remonter les plus grands."


async def insertion_sort(data):
    for i in range(1, len(data)):
        j = i
        while j > 0 and data[j - 1] > data[j]:
            data[j], data[j - 1] = data[j - 1], data[j]
            yield data, [j, j - 1]
            j -= 1
insertion_sort.desc = "Insère chaque élément dans la partie déjà triée via des swaps successifs."


async def selection_sort(data):
    n = len(data)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if data[j] < data[min_idx]:
                min_idx = j
        if min_idx != i:
            data[i], data[min_idx] = data[min_idx], data[i]
            yield data, [i, min_idx]
selection_sort.desc = "Sélectionne le plus petit élément restant et le place au bon endroit."


async def quick_sort(data, low=0, high=None):
    if high is None:
        high = len(data) - 1
    if low < high:
        pivot = data[high]
        left = low
        for j in range(low, high):
            if data[j] < pivot:
                data[left], data[j] = data[j], data[left]
                yield data, [left, j]
                left += 1
        data[left], data[high] = data[high], data[left]
        yield data, [left, high]
        async for step, idx in quick_sort(data, low, left - 1):
            yield step, idx
        async for step, idx in quick_sort(data, left + 1, high):
            yield step, idx
quick_sort.desc = "Choisit un pivot et partitionne récursivement la liste."


async def merge_sort(data, start=0, end=None):
    if end is None:
        end = len(data)
    if end - start > 1:
        mid = (start + end) // 2
        async for step, idx in merge_sort(data, start, mid):
            yield step, idx
        async for step, idx in merge_sort(data, mid, end):
            yield step, idx
        # Fusion en place par rotations de swaps
        i, j = start, mid
        while i < j and j < end:
            if data[i] <= data[j]:
                i += 1
            else:
                # Rotation : amène data[j] en position i par swaps successifs
                k = j
                while k > i:
                    data[k], data[k - 1] = data[k - 1], data[k]
                    yield data, [k, k - 1]
                    k -= 1
                i += 1
                j += 1
merge_sort.desc = "Divise et fusionne récursivement les sous-listes pour trier (fusion par swaps)."


async def heap_sort(data):
    n = len(data)

    async def heapify(size, i):
        while True:
            largest = i
            l, r = 2 * i + 1, 2 * i + 2
            if l < size and data[l] > data[largest]:
                largest = l
            if r < size and data[r] > data[largest]:
                largest = r
            if largest == i:
                break
            data[i], data[largest] = data[largest], data[i]
            yield data, [i, largest]
            i = largest

    # Construction du tas
    for i in range(n // 2 - 1, -1, -1):
        async for step, idx in heapify(n, i):
            yield step, idx

    # Extraction
    for i in range(n - 1, 0, -1):
        data[i], data[0] = data[0], data[i]
        yield data, [0, i]
        async for step, idx in heapify(i, 0):
            yield step, idx
heap_sort.desc = "Tri utilisant un tas binaire (heapify entièrement async)."


async def shell_sort(data):
    n = len(data)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            j = i
            while j >= gap and data[j - gap] > data[j]:
                data[j], data[j - gap] = data[j - gap], data[j]
                yield data, [j, j - gap]
                j -= gap
        gap //= 2
shell_sort.desc = "Améliore Insertion Sort avec des gaps décroissants."


async def cocktail_sort(data):
    n = len(data)
    start, end = 0, n - 1
    while True:
        swapped = False
        for i in range(start, end):
            if data[i] > data[i + 1]:
                data[i], data[i + 1] = data[i + 1], data[i]
                swapped = True
                yield data, [i, i + 1]
        if not swapped:
            break
        swapped = False
        end -= 1
        for i in range(end - 1, start - 1, -1):
            if data[i] > data[i + 1]:
                data[i], data[i + 1] = data[i + 1], data[i]
                swapped = True
                yield data, [i, i + 1]
        if not swapped:
            break
        start += 1
cocktail_sort.desc = "Version bidirectionnelle de Bubble Sort."


async def comb_sort(data):
    n = len(data)
    gap = n
    shrink = 1.3
    sorted_ = False
    while not sorted_:
        gap = int(gap / shrink)
        if gap <= 1:
            gap = 1
            sorted_ = True
        for i in range(n - gap):
            if data[i] > data[i + gap]:
                data[i], data[i + gap] = data[i + gap], data[i]
                sorted_ = False
                yield data, [i, i + gap]
comb_sort.desc = "Amélioration de Bubble Sort avec un gap variable."


# ────────────────────────────────────────────────────────────────
# Expérimentaux — réécrits en swaps purs
# ────────────────────────────────────────────────────────────────
async def pair_sum_sort(data):
    """
    Odd-Even / Brick Sort : passe alternativement sur les paires (0,1),(2,3)...
    puis (1,2),(3,4)... et swap si nécessaire. Converge vers un tri complet.
    Remplace l'ancienne version qui utilisait des copies intermédiaires.
    """
    n = len(data)
    changed = True
    while changed:
        changed = False
        # Paires paires : (0,1), (2,3), ...
        for i in range(0, n - 1, 2):
            if data[i] > data[i + 1]:
                data[i], data[i + 1] = data[i + 1], data[i]
                changed = True
                yield data, [i, i + 1]
        # Paires impaires : (1,2), (3,4), ...
        for i in range(1, n - 1, 2):
            if data[i] > data[i + 1]:
                data[i], data[i + 1] = data[i + 1], data[i]
                changed = True
                yield data, [i, i + 1]
pair_sum_sort.desc = "Odd-Even Sort : alterne les paires paires et impaires jusqu'au tri complet."


async def pair_shift_sort(data):
    """
    Gnome Sort : si l'élément courant est mal placé, le swap vers la gauche
    jusqu'à sa bonne position, puis repart en avant.
    Remplace l'ancienne version avec insert/pop.
    """
    n = len(data)
    i = 1
    while i < n:
        if i == 0 or data[i] >= data[i - 1]:
            i += 1
        else:
            data[i], data[i - 1] = data[i - 1], data[i]
            yield data, [i, i - 1]
            i -= 1
pair_shift_sort.desc = "Gnome Sort : swap l'élément vers la gauche jusqu'à sa bonne position."


async def centrifugal_sort(data):
    """
    Tri par triplets via swaps directs (min au début, max à la fin du triplet).
    Chaque triplet est trié avec au plus 3 swaps comparatifs.
    """
    n = len(data)
    changed = True
    while changed:
        changed = False
        for offset in (0, 1):
            for i in range(offset, n - 2, 3):
                a, b, c = i, i + 1, i + 2
                # Tri réseau à 3 éléments : 3 comparaisons max, swaps directs
                if data[a] > data[b]:
                    data[a], data[b] = data[b], data[a]
                    changed = True
                    yield data, [a, b]
                if data[b] > data[c]:
                    data[b], data[c] = data[c], data[b]
                    changed = True
                    yield data, [b, c]
                if data[a] > data[b]:
                    data[a], data[b] = data[b], data[a]
                    changed = True
                    yield data, [a, b]
centrifugal_sort.desc = "Tri par triplets avec swaps directs (réseau de tri à 3 éléments)."


async def flashy_sort(data):
    """Heap Sort avec heapify async imbriquée — visuellement spectaculaire."""
    n = len(data)

    async def heapify(size, i):
        while True:
            largest = i
            l, r = 2 * i + 1, 2 * i + 2
            if l < size and data[l] > data[largest]:
                largest = l
            if r < size and data[r] > data[largest]:
                largest = r
            if largest == i:
                break
            data[i], data[largest] = data[largest], data[i]
            yield data, [i, largest]
            i = largest

    for i in range(n // 2 - 1, -1, -1):
        async for step, highlight in heapify(n, i):
            yield step, highlight

    for i in range(n - 1, 0, -1):
        data[i], data[0] = data[0], data[i]
        yield data, [0, i]
        async for step, highlight in heapify(i, 0):
            yield step, highlight
flashy_sort.desc = "Heap Sort visuellement spectaculaire avec heapify entièrement async."


# ────────────────────────────────────────────────────────────────
# Dictionnaire global pour import
# ────────────────────────────────────────────────────────────────
algorithms = {
    "Bubble Sort":      bubble_sort,
    "Cocktail Sort":    cocktail_sort,
    "Comb Sort":        comb_sort,
    "Heap Sort":        heap_sort,
    "Insertion Sort":   insertion_sort,
    "Merge Sort":       merge_sort,
    "Quick Sort":       quick_sort,
    "Selection Sort":   selection_sort,
    "Shell Sort":       shell_sort,
    "Odd-Even Sort":    pair_sum_sort,
    "Gnome Sort":       pair_shift_sort,
    "Centrifugal Sort": centrifugal_sort,
    "Flashy Sort":      flashy_sort,
}
