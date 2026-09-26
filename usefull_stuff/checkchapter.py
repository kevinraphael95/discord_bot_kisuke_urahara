import requests
import re

def get_wiki_chapter(name):
    url = "https://bleach.fandom.com/api.php"
    params = {
        "action": "query", "format": "json", "titles": name,
        "prop": "revisions", "rvprop": "content", "rvsection": "0",
        "redirects": 1
    }
    headers = {"User-Agent": "BleachComparisonBot/1.0"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        pages = data['query']['pages']
        page_id = list(pages.keys())[0]
        if page_id == "-1": return None
        
        content = pages[page_id]['revisions'][0]['*']

        # 1. Tenter la recherche classique "first_appearance = Chapter X"
        match = re.search(r"(?:first_appearance|manga debut|debut)\s*=\s*.*?(\d+)", content, re.IGNORECASE)
        if match: return match.group(1)
        
        # 2. Si échec, tenter la recherche du format [X. (souvent utilisé dans le texte de tête)
        match = re.search(r"\[(\d+)\.", content)
        if match: return match.group(1)

        # 3. Si échec, chercher n'importe quel nombre après le mot "Chapter"
        match = re.search(r"chapter\s*(\d+)", content, re.IGNORECASE)
        if match: return match.group(1)

        return None
    except:
        return None

def extraire_personnages_depuis_js(filepath):
    personnages = []
    with open(filepath, 'r', encoding='utf-8') as f:
        # On lit ligne par ligne pour éviter les erreurs de syntaxe des commentaires
        for line in f:
            # Cherche le motif {n:"Nom", ..., chapter:"Nombre"}
            match = re.search(r'n:"([^"]+)",.*?chapter:"(\d+)"', line)
            if match:
                personnages.append({'n': match.group(1), 'chapter': match.group(2)})
    return personnages

# --- Exécution ---
personnages = extraire_personnages_depuis_js('data.js')

print(f"{'Nom':<25} | {'Data JS':<10} | {'Wiki':<10}")
print("-" * 50)

for p in personnages:
    nom = p['n']
    chap_js = p['chapter']
    chap_wiki = get_wiki_chapter(nom)
    
    print(f"{nom:<25} | {chap_js:<10} | {chap_wiki if chap_wiki else 'Non trouvé'}")
