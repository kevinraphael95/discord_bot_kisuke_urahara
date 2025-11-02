# ────────────────────────────────────────────────────────────────
# utils/algorithms.py — Tous les algorithmes de tri asynchrones
# Chaque fonction yield les étapes pour la visualisation
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# Tri classiques
# ────────────────────────────────────────────────────────────────
async def bubble_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
            yield data, list(range(n - i, n))

async def insertion_sort(data):
    for i in range(1, len(data)):
        key = data[i]
        j = i - 1
        while j >= 0 and data[j] > key:
            data[j + 1] = data[j]
            j -= 1
            yield data, list(range(i + 1))
        data[j + 1] = key
        yield data, list(range(i + 1))

async def selection_sort(data):
    n = len(data)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if data[j] < data[min_idx]:
                min_idx = j
        data[i], data[min_idx] = data[min_idx], data[i]
        yield data, list(range(i + 1))

async def quick_sort(data, low=0, high=None):
    if high is None:
        high = len(data) - 1
    if low < high:
        pivot, left, right = data[high], low, high - 1
        while left <= right:
            while left <= right and data[left] < pivot:
                left += 1
            while left <= right and data[right] >= pivot:
                right -= 1
            if left < right:
                data[left], data[right] = data[right], data[left]
            yield data, list(range(low))
        data[left], data[high] = data[high], data[left]
        yield data, list(range(low, left + 1))
        async for step, sorted_idx in quick_sort(data, low, left - 1):
            yield step, sorted_idx
        async for step, sorted_idx in quick_sort(data, left + 1, high):
            yield step, sorted_idx

async def merge_sort(data, start=0, end=None):
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
            yield data, list(range(start, k + 1))

async def heap_sort(data):
    n = len(data)
    def heapify(n, i):
        largest = i
        l, r = 2*i + 1, 2*i + 2
        if l < n and data[l] > data[largest]:
            largest = l
        if r < n and data[r] > data[largest]:
            largest = r
        if largest != i:
            data[i], data[largest] = data[largest], data[i]
            heapify(n, largest)
    for i in range(n//2 - 1, -1, -1):
        heapify(n, i)
        yield data, []
    for i in range(n - 1, 0, -1):
        data[i], data[0] = data[0], data[i]
        heapify(i, 0)
        yield data, list(range(i, n))

async def shell_sort(data):
    n = len(data)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = data[i]
            j = i
            while j >= gap and data[j - gap] > temp:
                data[j] = data[j - gap]
                j -= gap
                yield data, list(range(i + 1))
            data[j] = temp
            yield data, list(range(i + 1))
        gap //= 2

async def cocktail_sort(data):
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
            yield data, list(range(i + 1))
        if not swapped:
            break
        swapped = False
        end -= 1
        for i in range(end - 1, start - 1, -1):
            if data[i] > data[i + 1]:
                data[i], data[i + 1] = data[i + 1], data[i]
                swapped = True
            yield data, list(range(i + 1))
        start += 1

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
        i = 0
        while i + gap < n:
            if data[i] > data[i + gap]:
                data[i], data[i + gap] = data[i + gap], data[i]
                sorted_ = False
            yield data, list(range(i + 1))
            i += 1

# ────────────────────────────────────────────────────────────────
# Nouveaux / expérimentaux
# ────────────────────────────────────────────────────────────────
async def pair_sum_sort(data):
    n = len(data)
    swapped = True
    while swapped:
        swapped = False
        pairs = [(i, i+1) for i in range(0, n-1, 2)]
        sums = [data[i]+data[j] for i,j in pairs]
        sorted_pairs = [pairs[i] for i in sorted(range(len(pairs)), key=lambda x: sums[x])]
        new_data = []
        for i,j in sorted_pairs:
            new_data.extend([data[i], data[j]])
        for k in range(len(new_data)):
            if data[k] != new_data[k]:
                data[k] = new_data[k]
                swapped = True
            yield data, list(range(len(data)))
        pairs = [(i, i+1) for i in range(1, n-1, 2)]
        sums = [data[i]+data[j] for i,j in pairs]
        sorted_pairs = [pairs[i] for i in sorted(range(len(pairs)), key=lambda x: sums[x])]
        new_data = data[:1]
        for i,j in sorted_pairs:
            new_data.extend([data[i], data[j]])
        if len(new_data) < n:
            new_data.append(data[-1])
        for k in range(len(new_data)):
            if data[k] != new_data[k]:
                data[k] = new_data[k]
                swapped = True
            yield data, list(range(len(data)))

async def pair_shift_sort(data):
    n = len(data)
    while True:
        changed = False
        i = 0
        while i < n-1:
            a,b = data[i], data[i+1]
            if a != b:
                gap = abs(a-b)
                if a > b:
                    new_pos = min(i+gap, n-1)
                    data.insert(new_pos, data.pop(i))
                    changed = True
            i += 1
            yield data, [i]
        if not changed:
            break

async def centrifugal_sort(data):
    n = len(data)
    changed = True
    while changed:
        changed = False
        for i in range(0, n-2, 3):
            triplet = data[i:i+3]
            sorted_triplet = sorted(triplet)
            if triplet != sorted_triplet:
                data[i:i+3] = sorted_triplet
                changed = True
            yield data, list(range(i,i+3))
        for i in range(1, n-2, 3):
            triplet = data[i:i+3]
            sorted_triplet = sorted(triplet)
            if triplet != sorted_triplet:
                data[i:i+3] = sorted_triplet
                changed = True
            yield data, list(range(i,i+3))

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
}
