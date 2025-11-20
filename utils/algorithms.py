# ────────────────────────────────────────────────────────────────
# utils/algorithms.py — Tous les algorithmes de tri asynchrones
# Chaque fonction yield les étapes pour la visualisation
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# Tris classiques
# ────────────────────────────────────────────────────────────────
async def bubble_sort(data):
    """Compare chaque élément avec le suivant et fait remonter les plus grands."""
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
                yield data, [j, j + 1]  # 🟥 surbrillance limitée aux éléments échangés
bubble_sort.desc = "Compare chaque élément avec le suivant et fait remonter les plus grands."

async def insertion_sort(data):
    for i in range(1, len(data)):
        key = data[i]
        j = i - 1
        moved = False
        moved_indices = []
        while j >= 0 and data[j] > key:
            data[j + 1] = data[j]
            moved_indices.append(j + 1)
            moved_indices.append(j)
            j -= 1
            moved = True
        data[j + 1] = key
        if moved:  # yield uniquement si qqch a bougé
            yield data, moved_indices + [j + 1, i]
insertion_sort.desc = "Insère chaque élément dans la partie déjà triée."


async def selection_sort(data):
    """Sélectionne le plus petit élément restant et le place au bon endroit."""
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
    """Choisit un pivot et partitionne récursivement la liste."""
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
        async for step, sorted_idx in quick_sort(data, low, left - 1):
            yield step, sorted_idx
        async for step, sorted_idx in quick_sort(data, left + 1, high):
            yield step, sorted_idx
quick_sort.desc = "Choisit un pivot et partitionne récursivement la liste."

async def merge_sort(data, start=0, end=None):
    """Divise et fusionne récursivement les sous-listes pour trier."""
    if end is None:
        end = len(data)
    if end - start > 1:
        mid = (start + end) // 2
        async for step, sorted_idx in merge_sort(data, start, mid):
            yield step, sorted_idx
        async for step, sorted_idx in merge_sort(data, mid, end):
            yield step, sorted_idx
        left, right = data[start:mid], data[mid:end]
        i = j = 0
        for k in range(start, end):
            if j >= len(right) or (i < len(left) and left[i] < right[j]):
                data[k] = left[i]
                i += 1
            else:
                data[k] = right[j]
                j += 1
            yield data, [k]
merge_sort.desc = "Divise et fusionne récursivement les sous-listes pour trier."

async def heap_sort(data):
    """Tri utilisant un tas binaire."""
    n = len(data)

    def heapify(n, i):
        largest = i
        l, r = 2 * i + 1, 2 * i + 2
        if l < n and data[l] > data[largest]:
            largest = l
        if r < n and data[r] > data[largest]:
            largest = r
        if largest != i:
            data[i], data[largest] = data[largest], data[i]
            heapify(n, largest)

    for i in range(n // 2 - 1, -1, -1):
        heapify(n, i)
        yield data, [i]

    for i in range(n - 1, 0, -1):
        data[i], data[0] = data[0], data[i]
        yield data, [0, i]
        heapify(i, 0)
heap_sort.desc = "Tri utilisant un tas binaire."

async def shell_sort(data):
    n = len(data)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = data[i]
            j = i
            moved = False
            moved_indices = []
            while j >= gap and data[j - gap] > temp:
                data[j] = data[j - gap]
                moved_indices.append(j)
                moved_indices.append(j - gap)
                j -= gap
                moved = True
            data[j] = temp
            if moved:  # yield uniquement si qqch a bougé
                yield data, moved_indices + [j, i]
        gap //= 2
shell_sort.desc = "Améliore Insertion Sort avec des gaps."

async def cocktail_sort(data):
    """Version bidirectionnelle de Bubble Sort."""
    n = len(data)
    swapped = True
    start = 0
    end = n - 1
    while swapped:
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
        start += 1
cocktail_sort.desc = "Version bidirectionnelle de Bubble Sort."

async def comb_sort(data):
    """Amélioration de Bubble Sort avec un gap variable."""
    n = len(data)
    gap = n
    shrink = 1.3
    sorted_ = False
    while not sorted_:
        gap = int(gap / shrink)
        if gap <= 1:
            gap = 1
            sorted_ = True
        i = 0
        while i + gap < n:
            if data[i] > data[i + gap]:
                data[i], data[i + gap] = data[i + gap], data[i]
                sorted_ = False
                yield data, [i, i + gap]
            i += 1
comb_sort.desc = "Amélioration de Bubble Sort avec un gap variable."

# ────────────────────────────────────────────────────────────────
# Nouveaux / expérimentaux
# ────────────────────────────────────────────────────────────────
async def pair_sum_sort(data):
    """Tri par paires basé sur la somme des éléments."""
    n = len(data)
    swapped = True
    while swapped:
        swapped = False
        pairs = [(i, i + 1) for i in range(0, n - 1, 2)]
        sums = [data[i] + data[j] for i, j in pairs]
        sorted_pairs = [pairs[i] for i in sorted(range(len(pairs)), key=lambda x: sums[x])]
        new_data = []
        for i, j in sorted_pairs:
            new_data.extend([data[i], data[j]])
        for k in range(len(new_data)):
            if data[k] != new_data[k]:
                data[k] = new_data[k]
                swapped = True
                yield data, [k]
        pairs = [(i, i + 1) for i in range(1, n - 1, 2)]
        sums = [data[i] + data[j] for i, j in pairs]
        sorted_pairs = [pairs[i] for i in sorted(range(len(pairs)), key=lambda x: sums[x])]
        new_data = data[:1]
        for i, j in sorted_pairs:
            new_data.extend([data[i], data[j]])
        if len(new_data) < n:
            new_data.append(data[-1])
        for k in range(len(new_data)):
            if data[k] != new_data[k]:
                data[k] = new_data[k]
                swapped = True
                yield data, [k]
pair_sum_sort.desc = "Tri par paires basé sur la somme des éléments."

async def pair_shift_sort(data):
    """Déplace le plus grand élément d'une paire vers la droite."""
    n = len(data)
    while True:
        changed = False
        i = 0
        while i < n - 1:
            a, b = data[i], data[i + 1]
            if a > b:
                gap = abs(a - b)
                new_pos = min(i + gap, n - 1)
                data.insert(new_pos, data.pop(i))
                changed = True
                yield data, [i, new_pos]
            i += 1
        if not changed:
            break
pair_shift_sort.desc = "Déplace le plus grand élément d'une paire vers la droite."

async def centrifugal_sort(data):
    """Tri par triplets, le nombre du milieu est replacé entre les deux autres."""
    n = len(data)
    changed = True
    while changed:
        changed = False
        for i in range(0, n - 2, 3):
            triplet = data[i:i + 3]
            sorted_triplet = sorted(triplet)
            if triplet != sorted_triplet:
                data[i:i + 3] = sorted_triplet
                changed = True
                yield data, list(range(i, i + 3))
        for i in range(1, n - 2, 3):
            triplet = data[i:i + 3]
            sorted_triplet = sorted(triplet)
            if triplet != sorted_triplet:
                data[i:i + 3] = sorted_triplet
                changed = True
                yield data, list(range(i, i + 3))
centrifugal_sort.desc = "Tri par triplets, le nombre du milieu est replacé entre les deux autres."

async def flashy_sort(data):
    """Tri rapide et visuellement spectaculaire."""
    n = len(data)
    # Étape 1 : Heapify
    def heapify(n, i):
        largest = i
        l, r = 2*i+1, 2*i+2
        if l < n and data[l] > data[largest]:
            largest = l
        if r < n and data[r] > data[largest]:
            largest = r
        if largest != i:
            data[i], data[largest] = data[largest], data[i]
            yield data, [i, largest]
            async for _ in heapify(n, largest):
                yield _, [i, largest]

    for i in range(n//2 -1, -1, -1):
        async for step, highlight in heapify(n, i):
            yield step, highlight

    # Étape 2 : Extraction du heap
    for i in range(n-1, 0, -1):
        data[i], data[0] = data[0], data[i]
        yield data, [0, i]
        async for step, highlight in heapify(i, 0):
            yield step, highlight



# ────────────────────────────────────────────────────────────────
# Dictionnaire global pour import
# ────────────────────────────────────────────────────────────────
algorithms = {
    "Bubble Sort": bubble_sort,
    "Cocktail Sort": cocktail_sort,
    "Comb Sort": comb_sort,
    "Heap Sort": heap_sort,
    "Insertion Sort": insertion_sort,
    "Merge Sort": merge_sort,
    "Quick Sort": quick_sort,
    "Selection Sort": selection_sort,
    "Shell Sort": shell_sort,
    "Pair Sum Sort": pair_sum_sort,
    "Pair Shift Sort": pair_shift_sort,
    "Centrifugal Sort": centrifugal_sort,
    "Tri test cool": flashy_sort
}
