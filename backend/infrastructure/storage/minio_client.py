"""MinIO 对象存储客户端 —— 封装文件上传和下载操作。"""

import io
from functools import lru_cache

from minio import Minio

from backend.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    """获取全局 MinIO 客户端单例。"""
    settings = get_settings()
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )


def upload_file(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str,
) -> str:
    """上传文件到 MinIO，返回对象路径。"""
    client = get_minio_client()
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_name


def download_file(bucket: str, object_name: str) -> bytes:
    """从 MinIO 下载文件，返回文件内容字节。"""
    client = get_minio_client()
    response = client.get_object(bucket_name=bucket, object_name=object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
