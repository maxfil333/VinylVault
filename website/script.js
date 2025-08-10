//----------------------------------------------------------------------------------------------------------- ПЕРЕМЕННЫЕ

const serverAddress = 'http://127.0.0.1:8000/'; // URL FastAPI сервера

const albumList = document.getElementById('album-list');
const albumSearchInput = document.getElementById('album-search');
const dropdownMenu = document.getElementById('dropdown-menu');
const searchAlbumBtn = document.getElementById('search-album-btn');


//---------------------------------------------------------------------------------------------------------------- UTILS

function logRequestDetails(method, url, headers, body) {
    console.log('>>> logging >>>')
    console.log(`${method}: Метод:`, method);
    console.log(`${method}: URL:`, url);
    console.log(`${method}: Заголовки:`, headers);
    if (body) {
        console.log(`${method}: Тело запроса:`, body);
    }
    console.log('<<< logging <<<')
}


//--------------------------------------------------------------------------------------------------- ВИЗУАЛЬНЫЕ ЭФФЕКТЫ

// Эффект увеличения альбома при наведении мыши
document.addEventListener('DOMContentLoaded', () => {
    if (albumList) {
        albumList.addEventListener('mouseover', (event) => {
            const card = event.target.closest('.card');
            if (card) {
                card.style.transform = 'scale(1.05)';
            }
        });

        albumList.addEventListener('mouseout', (event) => {
            const card = event.target.closest('.card');
            if (card) {
                card.style.transform = 'scale(1)';
            }
        });
    }
});


//-------------------------------------------------------------------------------------------------------------------API

// Функция для получения user_id из cookie: @app.get("api/me/userid")
async function getUserIdFromSession() {
    const response = await fetch(serverAddress + 'api/me/userid', { credentials: 'include' });
    if (!response.ok) return null;
    const data = await response.json();
    console.log(data.user_id)
    return data.user_id;
}

// Функция отправки альбома на сервер ( @app.post("/api/users/{user_id}/albums/add/") )
async function sendAlbumToServer(album_search_item) {

    const user_id = await getUserIdFromSession();
    if (!user_id) {
        console.error('user_id не найден в cookie!');
        return;
    }

    const albumData = {
        album_id: album_search_item.album_id,
        album_name: album_search_item.album_name,
        artist_name: album_search_item.artist_name
    };

    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(albumData),
    };

    const url = `${serverAddress}api/users/${user_id}/albums/add/`

    logRequestDetails('POST', url, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(url, requestOptions);

        if (!response.ok) {
            throw new Error(`Ошибка: ${response.status}`);
        }

        const data = await response.json();
        console.log('Ответ от сервера:', data);
    } catch (error) {
        console.error('Ошибка при добавлении альбома:', error);
        console.log('Не удалось добавить альбом на сервер!');
    }
}


// Функция удаления альбома с сервера ( @app.delete("/albums/") )
async function deleteAlbumFromServer(album_id) {

    const requestOptions = {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'}
    };

    const user_id = await getUserIdFromSession();
    if (!user_id) {
        console.error('user_id не найден в cookie!');
        return;
    }

    const url = `${serverAddress}api/users/${user_id}/albums/delete/${album_id}`;

    logRequestDetails('DELETE', url, requestOptions.headers);

    try {
        const response = await fetch(url, requestOptions);
        if (!response.ok) {
            throw new Error(`Ошибка: ${response.status}`);
        }
        const data = await response.json();
        console.log('Ответ от сервера:', data);
    } catch (error) {
        console.error('Ошибка при удалении альбома:', error);
        console.log('Не удалось удалить альбом с сервера!');
    }
}


// Функция для поиска релевантных альбомов и топ-альбомов артиста ( /api/search/mixed/{query} )
async function searchMixed(query) {
    const url = serverAddress + 'api/search/mixed/' + encodeURIComponent(query);
    console.log(`GET: ${url}`);
    const response = await fetch(url);
    return await response.json();
}


// Загрузка альбомов пользователя из базы ( app.get("/api/users/{user_id}/albums/all/", response_model=list[VV_Album]) )
async function loadUserAlbums(userId) {
    try {
        const response = await fetch(`${serverAddress}api/users/${userId}/albums/all/`);
        const albums = await response.json();

        albumList.innerHTML = ''; // Очищаем список перед добавлением новых альбомов

        albums.forEach(album => {
            const albumCard = createAlbumCard(album);
            albumList.appendChild(albumCard);
        });

    } catch (error) {
        console.error("Ошибка загрузки альбомов:", error);
    }
}

// ... вызов функции при загрузке страницы
document.addEventListener("DOMContentLoaded", async () => {
    const pageType = document.querySelector("meta[name='page-type']")?.content;

    if (pageType === "user") {
        console.log("✅ Это страница пользователя. Загружаем альбомы...");
        const userId = await getUserIdFromSession(); // Теперь await работает корректно
        if (!userId) {
            console.error('user_id не найден в cookie!');
            return;
        }
        loadUserAlbums(userId);
    }
});

//------------------------------------------------------------------------------------------------------------- ОСНОВНЫЕ

// Создание карточки альбома
function createAlbumCard(album) {
    // Создаем элемент списка
    const li = document.createElement('li');
    li.className = 'col-6 col-sm-6 col-md-4 col-lg-3';

    li.dataset.albumId = album.album_id;
    li.dataset.albumName = album.album_name;
    li.dataset.artistName = album.artist_name;

    // Создаем карточку
    const cardDiv = document.createElement('div');
    cardDiv.className = 'card h-100';

    // Контейнер изображения
    const imageContainer = document.createElement('div');
    imageContainer.className = 'image-container';

    const img = document.createElement('img');
    img.src = album.cover_url || '/static/data/other/unfound.jpg';
    img.className = 'album_list_square card-img-top';
    img.alt = album.album_name;

    // Обработчики событий загрузки изображения
    img.onload = () => {
        img.style.opacity = '1';
    };
    img.onerror = () => {
        img.style.display = 'none';
    };

    imageContainer.appendChild(img);

    // Тело карточки
    const cardBody = document.createElement('div');
    cardBody.className = 'card-body';

    const albumTitle = document.createElement('h5');
    albumTitle.className = 'album_list_album card-title';
    albumTitle.textContent = album.album_name;

    const artistText = document.createElement('p');
    artistText.className = 'album_list_artist card-text text-muted';
    artistText.textContent = album.artist_name;

    // Создаем кнопку удаления
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-album-button btn btn-sm position-absolute';
    deleteButton.style.top = '5px';
    deleteButton.style.left = '5px';
    deleteButton.textContent = '❌';
    deleteButton.onclick = (event) => {
        event.stopPropagation(); // Останавливаем всплытие события
        li.remove(); // Удаляем элемент из DOM
        deleteAlbumFromServer(album.album_id) // Удаляем альбом на сервере
            .then(() => {
                console.log(`Альбом ${album.album_name} от ${album.artist_name} успешно удалён с сервера`);
            });
    };

    // Собираем карточку
    cardBody.appendChild(albumTitle);
    cardBody.appendChild(artistText);
    cardDiv.appendChild(imageContainer);
    cardDiv.appendChild(cardBody);
    cardDiv.appendChild(deleteButton);
    li.appendChild(cardDiv);

    return li;
}


// Удаление альбома по клику (DOM + СЕРВЕР)
if (albumList) {
    albumList.addEventListener('click', (event) => {
        const target = event.target;
        // Проверяем, что клик был по элементу <li>
        if (target.tagName === 'LI') {
            // Получаем данные из атрибутов data-*
            const albumName = target.dataset.albumName;
            const artistName = target.dataset.artistName;
            const albumId = target.dataset.albumId

            // Проверяем, что данные присутствуют
            if (!albumName || !artistName) {
                console.error('Не удалось удалить альбом: отсутствует albumName или artistName');
                return;
            }

            // Удаляем элемент из DOM
            target.remove();

            // Удаляем альбом на сервере
            deleteAlbumFromServer(albumId)
                .then(() => {
                    console.log(`Альбом ${albumName} от ${artistName} успешно удалён с сервера`);
                })
                .catch((error) => {
                    console.error('Ошибка при удалении альбома на сервере:', error);
                    // Опционально: вернуть элемент в DOM при ошибке
                    // albumList.appendChild(target);
                });
        }
    });
} else {
    console.warn('Элемент albumList не найден в DOM');
}


// Добавление альбома на витрину при выборе варианта из выпадающего списка найденных альбомов
function addAlbumBySearchGrouped(result) {
    dropdownMenu.innerHTML = '';

    // helper для рендера группы
    const renderGroup = (titleText, items) => {
        const hasItems = Array.isArray(items) && items.length > 0;
        const header = document.createElement('div');
        header.textContent = titleText;
        header.className = 'dropdown-header text-muted';
        header.style.fontWeight = 'bold';
        header.style.padding = '6px 12px';
        dropdownMenu.appendChild(header);

        if (!hasItems) {
            const empty = document.createElement('div');
            empty.textContent = 'Нет результатов';
            empty.className = 'dropdown-item text-muted';
            dropdownMenu.appendChild(empty);
            return;
        }

        items.forEach((album) => {
            const item = document.createElement('div');
            item.className = 'dropdown-item d-flex align-items-center justify-content-between';
            item.style.cursor = 'pointer';

            const textSpan = document.createElement('span');
            textSpan.textContent = `${album.album_name} — ${album.artist_name}`;
            textSpan.style.whiteSpace = 'nowrap';
            textSpan.style.overflow = 'hidden';
            textSpan.style.textOverflow = 'ellipsis';
            textSpan.style.paddingRight = '8px';

            const img = document.createElement('img');
            const cover = album.cover_url || album.cover_url_reserve || '/static/data/other/unfound.jpg';
            img.src = cover;
            img.alt = album.album_name;
            img.style.width = '32px';
            img.style.height = '32px';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '4px';
            img.referrerPolicy = 'no-referrer';

            item.appendChild(textSpan);
            item.appendChild(img);

            item.addEventListener('click', () => {
                const li = createAlbumCard(album);
                albumList.appendChild(li);
                albumSearchInput.value = '';
                sendAlbumToServer(album);
                dropdownMenu.style.display = 'none';
            });

            dropdownMenu.appendChild(item);
        });
    };

    renderGroup('Albums', result.albums);
    renderGroup('Artist\'s top-albums', result.artist_top_albums);

    dropdownMenu.style.display = 'block';
    dropdownMenu.style.left = `${albumSearchInput.offsetLeft}px`;
    dropdownMenu.style.top = `${albumSearchInput.offsetTop + albumSearchInput.offsetHeight}px`;
}


// --- Обработчик кнопки поиска searchAlbumBtn (Найти альбом) ---

// PRESS ENTER
albumSearchInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        searchAlbumBtn.click();
    }
});

searchAlbumBtn.addEventListener('click', async () => {
    const albumName = albumSearchInput.value.trim();
    if (albumName === '') {
        return;
    }

    try {
        // API call (сгруппированный поиск)
        const data = await searchMixed(albumName);
        addAlbumBySearchGrouped(data);
    } catch (error) {
        console.error('Ошибка при поиске альбомов:', error);
    }
});