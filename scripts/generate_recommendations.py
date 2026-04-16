#!/usr/bin/env python3
"""Pre-compute content-based recommendations using TF-IDF + cosine similarity.

For each movie, finds the 8 most similar movies based on title words,
category, and uploader. Outputs a lightweight JSON mapping.
"""
import json, os, re, math
from collections import defaultdict, Counter

MOVIES_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'movies.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'recommendations.json')

STOP_WORDS = {'the','a','an','in','of','for','and','or','is','to','full','movie','hd',
              'new','latest','free','watch','online','episode','episodes','hindi',
              'english','dubbed','official','video','videos','4k','1080p','720p'}

def tokenize(text):
    words = re.findall(r'[a-z0-9]+', (text or '').lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]

def build_tfidf(docs):
    """Build TF-IDF vectors for a list of (id, token_list) pairs."""
    df = Counter()
    for doc_id, tokens in docs:
        for t in set(tokens):
            df[t] += 1

    n = len(docs)
    idf = {t: math.log(n / (1 + freq)) for t, freq in df.items()}

    vectors = {}
    for doc_id, tokens in docs:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {}
        for t, count in tf.items():
            vec[t] = (count / total) * idf.get(t, 0)
        vectors[doc_id] = vec

    return vectors

def cosine_sim(v1, v2):
    """Cosine similarity between two sparse vectors (dicts)."""
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

def main():
    with open(MOVIES_PATH, encoding='utf-8') as f:
        data = json.load(f)
    movies = data.get('movies', [])
    print(f'Loaded {len(movies)} movies')

    docs = []
    for m in movies:
        tokens = tokenize(m.get('title', ''))
        cat_tokens = tokenize(m.get('category', '')) * 3
        up_tokens = tokenize(m.get('uploader', '')) * 2
        docs.append((m['id'], tokens + cat_tokens + up_tokens))

    vectors = build_tfidf(docs)
    print(f'Built TF-IDF vectors for {len(vectors)} documents')

    recommendations = {}
    movie_ids = list(vectors.keys())

    for i, mid in enumerate(movie_ids):
        if i % 500 == 0:
            print(f'  Processing {i}/{len(movie_ids)}...')

        v1 = vectors[mid]
        scores = []
        for other_id in movie_ids:
            if other_id == mid:
                continue
            sim = cosine_sim(v1, vectors[other_id])
            if sim > 0.05:
                scores.append((other_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        recommendations[mid] = [s[0] for s in scores[:8]]

    output = {
        'version': 1,
        'total_movies': len(recommendations),
        'recommendations': recommendations,
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f'Saved recommendations for {len(recommendations)} movies ({size_kb:.0f} KB)')

if __name__ == '__main__':
    main()
