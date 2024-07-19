import asyncio

import numpy as np
from typing import List
from torch import Tensor
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    model_name_or_path='Alibaba-NLP/gte-large-en-v1.5', trust_remote_code=True,
    revision='a0d6174973604c8ef416d9f6ed0f4c17ab32d78d')


async def get_embedding(texts: List[str]) -> List[List[float]]:
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_tensor=True)

    if isinstance(embeddings, Tensor) or isinstance(embeddings, np.ndarray):
        return embeddings.tolist()
    else:
        raise ValueError("Unexpected return type from model.encode")
