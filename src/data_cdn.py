"""Статика website/data/{avatars,backgrounds,other} в S3 без префикса data/ (ключи other/..., avatars/..., backgrounds/...)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

import boto3

from src.config import cfg


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
    )


def data_asset_public_url(relative_under_data: str) -> str:
    """relative_under_data: 'other/logo.png' — относительно website/data/. URL = base/other/logo.png."""
    rel = relative_under_data.lstrip("/").replace("\\", "/")
    base = cfg.s3_base_domain.rstrip("/")
    return f"{base}/{rel}"


def s3_key_for_data_file(relative_under_data: str) -> str:
    rel = relative_under_data.lstrip("/").replace("\\", "/")
    return rel


def upload_data_file(local_file: Path, relative_under_data: str) -> str:
    key = s3_key_for_data_file(relative_under_data)
    content_type, _ = mimetypes.guess_type(local_file.name)
    if not content_type:
        content_type = "application/octet-stream"
    _s3_client().put_object(
        Bucket=cfg.s3_bucket,
        Key=key,
        Body=local_file.read_bytes(),
        ContentType=content_type,
        ACL="public-read",
    )
    return data_asset_public_url(relative_under_data)


def build_vv_theme_css() -> str:
    bg = data_asset_public_url("backgrounds/back1.jpg")
    loading = data_asset_public_url("other/loading.jpg")
    return f""":root {{
  --vv-page-bg: url('{bg}');
  --vv-loading-placeholder: url('{loading}');
}}
"""


def html_inject_cdn_head() -> str:
    unfound = data_asset_public_url("other/unfound.jpg")
    base = cfg.s3_base_domain.rstrip("/")
    return (
        f"<script>window.__VV_UNFOUND_IMG__={unfound!r};"
        f"window.__VV_DATA_CDN_BASE__={base!r};</script>\n"
        '<link href="/static/vv-data-theme.css" rel="stylesheet">\n'
    )


def patch_html_with_cdn_assets(html: str) -> str:
    logo = data_asset_public_url("other/VVlogo_solo_cr.png")
    sample_avatar = data_asset_public_url("avatars/avatar1.jpg")
    pairs = [
        ('src="static/data/other/VVlogo_solo_cr.png"', f'src="{logo}"'),
        ("src='static/data/other/VVlogo_solo_cr.png'", f"src='{logo}'"),
        ('src="/static/data/other/VVlogo_solo_cr.png"', f'src="{logo}"'),
        ('src="/static/data/avatars/avatar1.jpg"', f'src="{sample_avatar}"'),
        ('src="static/data/avatars/avatar1.jpg"', f'src="{sample_avatar}"'),
    ]
    for old, new in pairs:
        html = html.replace(old, new)
    needle = '<link href="/static/styles.css"'
    inject = html_inject_cdn_head()
    if needle in html:
        return html.replace(needle, inject + needle, 1)
    if "</head>" in html:
        return html.replace("</head>", inject + "</head>", 1)
    return html
