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

// Функция отправки альбома на сервер ( @app.post("/api/users/{user_id}/albums/add/") )
async function sendAlbumToServer(album_search_item) {

    const user_id = 'testid'

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

    const user_id = 'testid';

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


// Функция для поиска релевантных альбомов ( @app.get("/api/search/albums/{album_name}") )
async function searchAlbums(albumName) {
    const url = serverAddress + 'api/search/albums/' + encodeURIComponent(albumName);
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
document.addEventListener("DOMContentLoaded", () => {
    const pageType = document.querySelector("meta[name='page-type']")?.content;

    if (pageType === "user") {
        console.log("✅ Это страница пользователя. Загружаем альбомы...");
        const userId = "testid"; // Динамически получаем ID пользователя
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
function addAlbumBySearch(data) {
    dropdownMenu.innerHTML = ''; // Очищаем предыдущие варианты

    // data = [{'artist1': .., 'name1': ..}, {'artist2': .., 'name2': ..}]
    // для каждого элемента из выпадающего списка (найденные в результате поиска альбомы/исполнители):
    data.forEach((album_search_item) => {
        const item = document.createElement('div');  // создаём контейнер для варианта (внутри dropdown);
        item.textContent = `${album_search_item.album_name} — ${album_search_item.artist_name}`;  // текст варианта;
        item.style.cursor = 'pointer';  // указываем стиль;

        // добавляем действие при клике:
        item.addEventListener('click', () => {

            const li = createAlbumCard(album_search_item);

            albumList.appendChild(li); // Добавляем в список
            albumSearchInput.value = ''; // Очищаем поле ввода
            sendAlbumToServer(album_search_item); // Отправляем альбом на сервер !!!
            dropdownMenu.style.display = 'none'; // Скрываем меню после выбора
        });

        dropdownMenu.appendChild(item); // Добавляем элемент в меню
    });

    dropdownMenu.style.display = 'block'; // Показываем меню
    dropdownMenu.style.left = `${albumSearchInput.offsetLeft}px`; // Позиция по горизонтали
    dropdownMenu.style.top = `${albumSearchInput.offsetTop + albumSearchInput.offsetHeight}px`; // Позиция по вертикали
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
        // API call
        const data = await searchAlbums(albumName);

        if (data.length === 0) {
            console.log('No albums found.');
            return;
        }

        addAlbumBySearch(data);
    } catch (error) {
        console.error('Ошибка при поиске альбомов:', error);
    }
});