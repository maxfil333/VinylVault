"""Smoke-тесты против локального Docker-стека."""

from __future__ import annotations

import io
import subprocess
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
TIMEOUT = 30.0

# Уборка идёт внутри контейнера app: у него есть доступ к Mongo по внутренней сети и ключи S3
CLEANUP_CODE = """
import asyncio, sys
from src.database import init_database, close_database, get_users_collection, get_session_cookies_collection
from src.cdn.s3_avatars import delete_user_avatar

async def main(username, user_id):
    await init_database()
    sessions = await get_session_cookies_collection()
    users = await get_users_collection()
    await sessions.delete_many({"username": username})
    await users.delete_many({"username": username})
    await close_database()
    if user_id:
        await delete_user_avatar(user_id)

asyncio.run(main(sys.argv[1], sys.argv[2]))
"""


def ok(name: str) -> None:
    print(f"[OK] {name}")


def warn(name: str, detail: str) -> None:
    print(f"[WARN] {name}: {detail}")


def fail(name: str, detail: str) -> None:
    print(f"[FAIL] {name}: {detail}")
    sys.exit(1)


def cleanup(username: str, user_id: str) -> None:
    """Удаляет созданного тестом пользователя, его сессии и аватар в S3."""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "app", "python", "-c", CLEANUP_CODE, username, user_id],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        warn(f"уборка не удалась для {username}", result.stderr.strip()[-300:])
        return
    ok(f"уборка тестовых данных ({username})")


def run_checks(username: str, state: dict) -> None:
    client = httpx.Client(base_url=BASE, follow_redirects=False, timeout=TIMEOUT)
    password = "TestPass123!"
    email = f"{username}@example.com"

    r = client.get("/health")
    if r.status_code != 200 or r.json().get("database") != "up":
        fail("health", f"status={r.status_code}, body={r.text[:200]}")
    ok("GET /health")

    r = client.get("/openapi.json")
    if r.status_code == 404:
        ok("схема API закрыта (ENABLE_DOCS=false)")
    else:
        warn("схема API открыта", f"/openapi.json -> {r.status_code}; на проде ENABLE_DOCS должен быть false")

    r = client.get("/welcome")
    if r.status_code != 200:
        fail("welcome", f"status={r.status_code}")
    ok("GET /welcome")

    r = client.get("/")
    if r.status_code not in (303, 307) or "/welcome" not in r.headers.get("location", ""):
        fail("root redirect guest", f"status={r.status_code}, location={r.headers.get('location')}")
    ok("GET / -> /welcome без сессии")

    r = client.get("/testuser")
    if r.status_code != 404:
        fail("testuser removed", f"status={r.status_code}")
    ok("GET /testuser удалён")

    r = client.get("/api/auth/check")
    if r.status_code != 200 or r.json().get("is_authenticated") is not False:
        fail("auth check guest", r.text)
    ok("GET /api/auth/check (guest)")

    r = client.get("/api/search/mixed/radiohead")
    if r.status_code != 200 or "albums" not in r.json():
        fail("search mixed guest", f"status={r.status_code}, body={r.text[:300]}")
    ok("GET /api/search/mixed (гостю доступен для welcome-страницы)")

    r = client.post(
        "/login",
        data={"username": "nobody", "password": ""},
    )
    if r.status_code not in (303, 307) or "error=invalid" not in r.headers.get("location", ""):
        fail("login empty password", f"status={r.status_code}, location={r.headers.get('location')}")
    ok("POST /login пустой пароль отклонён")

    r = client.post(
        "/register",
        data={"username": username, "password": password, "email": email},
    )
    if r.status_code not in (303, 307) or r.headers.get("location", "") != f"/user/{username}":
        fail("register", f"status={r.status_code}, location={r.headers.get('location')}, body={r.text[:200]}")
    ok("POST /register")

    session_cookie = r.cookies.get("vv_session_cookie")
    if not session_cookie:
        fail("register cookie", "vv_session_cookie не установлена")
    ok("cookie сессии после register")

    # Прокси прислал HTTPS -> cookie обязана уйти с флагом Secure (иначе сессию снимут с HTTP-трафика)
    r = client.post(
        "/login",
        data={"username": username, "password": password},
        headers={"X-Forwarded-Proto": "https"},
    )
    set_cookie = r.headers.get("set-cookie", "")
    if "Secure" not in set_cookie:
        fail(
            "secure cookie за прокси",
            f"нет флага Secure при X-Forwarded-Proto=https ({set_cookie}); проверь FORWARDED_ALLOW_IPS",
        )
    ok("Secure у cookie при X-Forwarded-Proto=https")

    auth = httpx.Client(
        base_url=BASE,
        follow_redirects=True,
        timeout=TIMEOUT,
        cookies={"vv_session_cookie": session_cookie},
    )

    r = auth.get("/me")
    if r.status_code != 200 or "page-type" not in r.text or username not in r.text or "/static/script.js" not in r.text:
        fail("/me", f"status={r.status_code}")
    ok("GET /me")

    r = client.get(f"/user/{username}")
    if r.status_code != 200 or username not in r.text:
        fail("public profile page", f"status={r.status_code}")
    ok(f"GET /user/{username}")

    r = auth.get("/api/me/userid")
    if r.status_code != 200 or not r.json().get("user_id"):
        fail("/api/me/userid", r.text)
    user_id = r.json()["user_id"]
    state["user_id"] = user_id
    ok("GET /api/me/userid")

    client.cookies.set("vv_session_cookie", session_cookie)
    r = client.get("/")
    if r.status_code not in (303, 307) or r.headers.get("location", "") != f"/user/{username}":
        fail("root redirect authed", f"status={r.status_code}, location={r.headers.get('location')}")
    ok("GET / -> /user/<username> с сессией")

    r = auth.post(
        f"/api/users/{user_id}/albums/add/",
        json={"album_name": "OK Computer", "artist_name": "Radiohead"},
    )
    if r.status_code != 200:
        fail("add album", f"status={r.status_code}, body={r.text[:300]}")
    ok("POST добавление альбома")

    r = auth.get(f"/api/users/{user_id}/albums/all/")
    albums = r.json() if r.status_code == 200 else []
    if len(albums) != 1:
        fail("albums after add", f"status={r.status_code}, albums={len(albums)}")
    album_id = albums[0]["album_id"]
    ok("GET альбомы пользователя")

    r = auth.put(
        f"/api/users/{user_id}/albums/layout/",
        json={"deleted_album_ids": [], "order": [album_id]},
    )
    if r.status_code != 200 or len(r.json()) != 1 or r.json()[0]["order"] != 0:
        fail("layout reorder", f"status={r.status_code}, body={r.text[:300]}")
    ok("PUT сохранение порядка")

    r = auth.put(
        f"/api/users/{user_id}/albums/layout/",
        json={"deleted_album_ids": [album_id], "order": []},
    )
    if r.status_code != 200 or r.json() != []:
        fail("layout delete", f"status={r.status_code}, body={r.text[:300]}")
    r = auth.get(f"/api/users/{user_id}/albums/all/")
    if r.status_code != 200 or r.json() != []:
        fail("albums after layout delete", f"status={r.status_code}, body={r.text[:300]}")
    ok("PUT удаление альбома одной операцией")

    r = auth.put(
        f"/api/users/{user_id}/albums/layout/",
        json={"deleted_album_ids": ["нет-такого"], "order": ["нет-такого"]},
    )
    if r.status_code != 200 or r.json() != []:
        fail("layout unknown ids", f"status={r.status_code}, body={r.text[:300]}")
    ok("PUT неизвестные album_id не ломают сохранение")

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = auth.post(
        f"/api/users/{user_id}/avatar",
        files={"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")},
    )
    if r.status_code != 200 or not r.json().get("avatar_url"):
        fail("avatar upload", f"status={r.status_code}, body={r.text[:300]}")
    ok("POST avatar upload (valid PNG)")

    r = auth.post(
        f"/api/users/{user_id}/avatar",
        files={"file": ("bad.txt", io.BytesIO(b"not-an-image"), "text/plain")},
    )
    if r.status_code != 400:
        fail("avatar reject invalid", f"status={r.status_code}")
    ok("POST avatar upload отклоняет не-изображение")


def main() -> None:
    username = f"smoke_{uuid.uuid4().hex[:8]}"
    state: dict = {"user_id": ""}
    try:
        run_checks(username, state)
    finally:
        cleanup(username, state["user_id"])

    print("\nВсе smoke-тесты прошли успешно.")


if __name__ == "__main__":
    main()
