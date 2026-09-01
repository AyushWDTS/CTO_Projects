import hashlib
import re
import string
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "msclkid"}
TITLE_SIMILARITY_THRESHOLD = 0.920
TEXT_SIMILARITY_THRESHOLD = 0.880
MINIMUM_CLUSTER_CONFIDENCE = 0.850


@dataclass(frozen=True)
class SimilarityScores:
    title_sequence_score: float
    title_token_score: float
    text_token_score: float

    @property
    def best_title_score(self) -> float:
        return max(self.title_sequence_score, self.title_token_score)


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None

    stripped = url.strip()
    if not stripped:
        return None

    parts = urlsplit(stripped)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or ""
    if path != "/":
        path = path.rstrip("/")

    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        normalized_key = key.lower()
        if normalized_key.startswith("utm_") or normalized_key in TRACKING_PARAMS:
            continue
        query_pairs.append((key, value))

    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    translated = value.lower().translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", translated).strip()


def text_tokens(value: str | None, *, max_tokens: int | None = None) -> set[str]:
    tokens = [token for token in normalize_text(value).split() if len(token) >= 3]
    if max_tokens is not None:
        tokens = tokens[:max_tokens]
    return set(tokens)


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def sequence_similarity(left: str | None, right: str | None) -> float:
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def compare_article_text(
    title: str | None,
    clean_text: str | None,
    candidate_title: str | None,
    candidate_clean_text: str | None,
) -> SimilarityScores:
    return SimilarityScores(
        title_sequence_score=sequence_similarity(title, candidate_title),
        title_token_score=jaccard_similarity(text_tokens(title), text_tokens(candidate_title)),
        text_token_score=jaccard_similarity(
            text_tokens(clean_text, max_tokens=1000),
            text_tokens(candidate_clean_text, max_tokens=1000),
        ),
    )


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
