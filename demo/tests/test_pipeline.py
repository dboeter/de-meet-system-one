import pytest

from jevdemo.pipeline import bucket, bucket_counts


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (0.95, "accept"),
        (0.90, "accept"),
        (0.5, "review"),
        (0.10, "reject"),
        (0.02, "reject"),
    ],
)
def test_probability_lands_in_bucket(p, expected):
    assert bucket(p, lo=0.10, hi=0.90) == expected


def test_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        bucket(0.5, lo=0.9, hi=0.1)


def test_bucket_counts_include_empty_buckets():
    assert bucket_counts([0.99, 0.95, 0.4]) == {"accept": 2, "review": 1, "reject": 0}
