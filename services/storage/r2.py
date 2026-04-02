import boto3
from pydantic_settings import BaseSettings


class R2Settings(BaseSettings):
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "burnish-files"
    r2_endpoint_url: str = ""


class R2Client:
    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
    ):
        settings = R2Settings()
        account_id = account_id or settings.r2_account_id
        access_key_id = access_key_id or settings.r2_access_key_id
        secret_access_key = secret_access_key or settings.r2_secret_access_key
        bucket_name = bucket_name or settings.r2_bucket_name
        endpoint = (
            settings.r2_endpoint_url
            or (f"https://{account_id}.r2.cloudflarestorage.com" if account_id else "")
        )
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key_id or None,
            aws_secret_access_key=secret_access_key or None,
            region_name="auto",
        )

    def upload_file(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def download_file(self, key: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        body = response["Body"]
        try:
            result: bytes = body.read()
            return result
        finally:
            body.close()

    def get_signed_url(self, key: str, expires_in: int = 900) -> str:
        url: str = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    def delete_file(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)

    def org_key(self, org_id: str, key: str) -> str:
        """Prefix key with org_id for per-org isolation."""
        return f"{org_id}/{key}"
