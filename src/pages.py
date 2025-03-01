import aiofiles

from src.config import WEBSITE_DIR

async  def generate_user_page(user_id: str, username: str):
    html_content = f"""
    
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VinylVault</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="/static/styles.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400&display=swap" rel="stylesheet">
    </head>
    
    <body>
    
    <!-- Шапка страницы -->
    <div class="container" style="height: 54px">
    <nav class="navbar navbar-expand-sm navbar-dark bg-dark fixed-top">
        <div class="container-fluid">
            <a class="navbar-brand" href="/welcome" style="padding-top: 0">
                <img src="/static/data/other/VVlogo_solo_cr.png" alt="VivylVault Logo" style="width:200px; height:30px;" class="rounded-3">
            </a>
            <div class="collapse navbar-collapse justify-content-end" id="mynavbar">
                <form class="d-flex">
                    <a class="btn btn-danger me-2" type="button">My profile</a>
                </form>
            </div>
        </div>
    </nav>
    </div>
    
    <!-- Блок профиля пользователя -->
    <div class="container-fluid position-relative d-flex justify-content-center" style="background-color: black; height: 100px;">
        <img src="/static/data/avatars/avatar1.jpg" alt="User Avatar"
             class="rounded-circle position-absolute"
             style="width: 150px; height: 150px; bottom: 0; transform: translateY(50%);">
        <span class="font-family: Barlow text-white position-absolute" style="bottom: 5px; margin-left: 250px; z-index: 1;">{username}</span>
    </div>
    
    <!-- Блок с альбомами -->
    <div class="container my-4 pt-5">
        <h2 class="text-center text-danger" style="font-family: Barlow;">Top Albums</h2>
    
        <div class="mb-3 position-relative">
            <div class="d-flex align-items-center">
                <div class="position-relative flex-grow-1">
                    <input type="text" id="album-search" class="form-control" placeholder="Название альбома" />
                    <div id="dropdown-menu" class="dropdown-menu w-100" style="display: none; position: absolute; top: 100%; left: 0;">
                        <!-- Варианты для поиска появятся здесь -->
                    </div>
                </div>
                <button id="search-album-btn" class="btn ms-2 text-bg-danger" style="white-space: nowrap;">Найти</button>
            </div>
        </div>
    
        <div>
            <ul id="album-list" class="row list-unstyled g-3">
                <!-- Здесь будут храниться альбомы -->
                <!-- ... -->
                <!-- Здесь будут храниться альбомы -->
            </ul>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/script.js"></script>
    
    </body>
    </html>

    
    """
    page_path = f"{WEBSITE_DIR}/data/users/{user_id}.html"
    async with aiofiles.open(page_path, "w", encoding="utf-8") as f:
        await  f.write(html_content)
