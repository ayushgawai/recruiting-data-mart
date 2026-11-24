"""S3 URI parsing (no network / boto3 needed)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from recmart.ingest import parse_s3_uri
import pytest

def test_parse_s3():
    assert parse_s3_uri("s3://recruiting-raw/events/2025/") == ("recruiting-raw", "events/2025/")
    with pytest.raises(ValueError):
        parse_s3_uri("https://example.com/x")
