from typing import TYPE_CHECKING, Iterable, List

from django.db import transaction

from .models import Embedding


if TYPE_CHECKING:
    from .index import VectorIndexed


class ModelEmbeddingService:
    """A service to generate embeddings and store them in the Embedding model
    for reuse in future index operations."""

    def __init__(self, ai_backend):
        self.ai_backend = ai_backend

    def _existing_embeddings_match(
        self, embeddings: Iterable[Embedding], splits: List[str]
    ) -> bool:
        if not embeddings:
            return False

        embedding_content = [embedding.content for embedding in embeddings]

        if set(splits) == set(embedding_content):
            return True

        return False

    def embeddings_for_strings(self, strings: List[str]) -> List[List[float]]:
        return self.ai_backend.get_embeddings(strings)

    @transaction.atomic
    def embeddings_for_instance(
        self,
        instance: "VectorIndexed",
    ) -> Iterable[Embedding]:
        splits = instance.get_split_content()
        embeddings = Embedding.get_for_instance(instance)

        # If the existing embeddings all match on content, we return them
        # without generating new ones
        if self._existing_embeddings_match(embeddings, splits):
            return embeddings

        # Otherwise we delete all the existing embeddings and get new ones
        embeddings.delete()

        embedding_vectors = self.embeddings_for_strings(splits)
        generated_embeddings = []
        for idx, split in enumerate(splits):
            embedding = Embedding.from_instance(instance)
            embedding.vector = embedding_vectors[idx]
            embedding.content = split
            embedding.save()
            generated_embeddings.append(embedding)

        return generated_embeddings
