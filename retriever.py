import csv
import math
import re
from collections import Counter

class SimpleTFIDFRetriever:
    def __init__(self, facets_csv_path="enriched_facets.csv"):
        self.facets_csv_path = facets_csv_path
        self.facets = []
        self.vocabulary = set()
        self.idf = {}
        self.facet_vectors = []
        self.stopwords = {
            'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent',
            'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
            'can', 'cant', 'cannot', 'could', 'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont',
            'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadnt', 'has', 'hasnt', 'have',
            'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here', 'heres', 'hers', 'herself', 'him',
            'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 'im', 'ive', 'if', 'in', 'into', 'is', 'isnt',
            'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 'my', 'myself', 'no', 'nor', 'not',
            'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over',
            'own', 'same', 'shant', 'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 'so', 'some', 'such',
            'than', 'that', 'thats', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'theres',
            'these', 'they', 'theyd', 'theyll', 'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too',
            'under', 'until', 'up', 'very', 'was', 'wasnt', 'we', 'wed', 'well', 'were', 'weve', 'werent',
            'what', 'whats', 'when', 'whens', 'where', 'wheres', 'which', 'while', 'who', 'whos', 'whom',
            'why', 'whys', 'with', 'wont', 'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve',
            'your', 'yours', 'yourself', 'yourselves'
        }
        self.load_and_index_facets()

    def tokenize(self, text):
        """Tokenize text into a list of lowercase alphanumeric words, filtering stopwords."""
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in self.stopwords]

    def load_and_index_facets(self):
        """Load enriched facets and build the TF-IDF index."""
        # Read from enriched facets CSV
        with open(self.facets_csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.facets.append(row)

        # Build vocabulary and term frequencies for each facet
        doc_counts = Counter()
        facet_token_lists = []
        
        for facet in self.facets:
            # We index both normalized name and category/scoring definition to enrich the search metadata
            text_to_index = f"{facet['normalized_facet']} {facet['category']} {facet['scoring_definition']}"
            tokens = self.tokenize(text_to_index)
            facet_token_lists.append(tokens)
            unique_tokens = set(tokens)
            self.vocabulary.update(unique_tokens)
            for token in unique_tokens:
                doc_counts[token] += 1

        # Calculate IDF
        num_docs = len(self.facets)
        for term in self.vocabulary:
            # IDF with smoothing
            self.idf[term] = math.log((1 + num_docs) / (1 + doc_counts[term])) + 1

        # Compute TF-IDF vectors for all facets
        for tokens in facet_token_lists:
            vector = self.compute_tfidf_vector(tokens)
            self.facet_vectors.append(vector)

    def compute_tfidf_vector(self, tokens):
        """Compute the TF-IDF vector for a list of tokens."""
        tf = Counter(tokens)
        vector = {}
        # Normalize tf vector
        for term, freq in tf.items():
            if term in self.idf:
                vector[term] = freq * self.idf[term]
        
        # Calculate L2 norm
        sq_sum = sum(val ** 2 for val in vector.values())
        norm = math.sqrt(sq_sum)
        if norm > 0:
            for term in vector:
                vector[term] /= norm
        return vector

    def cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two sparse TF-IDF vectors."""
        dot_product = 0.0
        # Iterate over the smaller vector for speed
        if len(vec1) > len(vec2):
            vec1, vec2 = vec2, vec1
        
        for term, val1 in vec1.items():
            if term in vec2:
                dot_product += val1 * vec2[term]
        return dot_product

    def retrieve(self, query, k=15):
        """Retrieve top k facets relevant to the query text."""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            # If query has no contentful words, return first k observable facets
            observable_facets = [f for f in self.facets if f["conversation_observable"] == "True"]
            return observable_facets[:k]

        query_vector = self.compute_tfidf_vector(query_tokens)

        # Compute similarity against all indexed facets
        scores = []
        for idx, facet_vec in enumerate(self.facet_vectors):
            sim = self.cosine_similarity(query_vector, facet_vec)
            scores.append((sim, self.facets[idx]))

        # Sort by similarity descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Take top k
        retrieved = [item[1] for item in scores[:k]]
        return retrieved

if __name__ == "__main__":
    # Self-test code
    retriever = SimpleTFIDFRetriever("enriched_facets.csv")
    print(f"Total facets indexed: {len(retriever.facets)}")
    
    # Test retrieval
    test_query = "I fell asleep very late and feel exhausted today. I can't concentrate."
    results = retriever.retrieve(test_query, k=5)
    print(f"\nTest retrieval for query: '{test_query}'")
    for i, res in enumerate(results):
        print(f"  {i+1}. {res['normalized_facet']} (Category: {res['category']}, Observable: {res['conversation_observable']})")
