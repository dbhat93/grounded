"""Vector store abstraction.

A thin interface so the dense retriever does not care where vectors live. The
build target is LanceDB (embedded ANN, no server, persistent on disk); the
production target is pgvector behind the same interface. Nothing above this
layer changes when the store is swapped.
"""
import os


class VectorStore:
    """Interface. build() indexes normalized vectors under string ids; search()
    returns [(id, cosine_similarity)] for a normalized query vector."""

    def has(self):
        raise NotImplementedError

    def build(self, ids, vectors):
        raise NotImplementedError

    def open(self):
        raise NotImplementedError

    def search(self, qvector, k):
        raise NotImplementedError


class LanceDBStore(VectorStore):
    def __init__(self, path, name):
        import lancedb
        self.name = name
        os.makedirs(path, exist_ok=True)
        self.db = lancedb.connect(path)
        self.tbl = None

    def has(self):
        return self.name in self.db.table_names()

    def open(self):
        self.tbl = self.db.open_table(self.name)

    def build(self, ids, vectors):
        data = [{"id": i, "vector": v} for i, v in zip(ids, vectors.tolist())]
        self.tbl = self.db.create_table(self.name, data=data, mode="overwrite")

    def search(self, qvector, k):
        rows = (self.tbl.search(qvector).metric("cosine").limit(k).to_list())
        # cosine distance -> similarity
        return [(r["id"], 1.0 - float(r["_distance"])) for r in rows]
