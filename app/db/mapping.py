PREFIX = "embeddings_"
keys = ["skills", "markets", "industries", "specialisms"]

MAPPING = {key: f"{PREFIX}{key}" for key in keys}
