from unittest.mock import MagicMock, patch

from services.storage.r2 import R2Client


@patch("services.storage.r2.boto3")
def test_upload_file(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    client = R2Client(
        account_id="test",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="test-bucket",
    )
    client.upload_file(
        b"file content",
        "decks/test.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Key"] == "decks/test.pptx"
    assert call_kwargs["Bucket"] == "test-bucket"


@patch("services.storage.r2.boto3")
def test_download_file(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    client = R2Client(
        account_id="test",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="test-bucket",
    )
    mock_s3.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"content"))}
    result = client.download_file("decks/test.pptx")
    assert result == b"content"


@patch("services.storage.r2.boto3")
def test_generate_signed_url(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    client = R2Client(
        account_id="test",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="test-bucket",
    )
    mock_s3.generate_presigned_url.return_value = "https://signed.url/test"
    url = client.get_signed_url("decks/test.pptx")
    assert "signed.url" in url


@patch("services.storage.r2.boto3")
def test_delete_file(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    client = R2Client(
        account_id="test",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="test-bucket",
    )
    client.delete_file("decks/test.pptx")
    mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="decks/test.pptx")


@patch("services.storage.r2.boto3")
def test_org_key_prefix(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    client = R2Client(
        account_id="test",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="test-bucket",
    )
    key = client.org_key("org-123", "decks/test.pptx")
    assert key == "org-123/decks/test.pptx"
