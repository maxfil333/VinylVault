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
    const albumList = document.querySelector('.album-list'); // Ваш селектор

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
    } else {
        console.warn('Элемент albumList не найден в DOM');
    }
});


//-------------------------------------------------------------------------------------------------------------------API

// Функция отправки альбома на сервер ( @app.post("/api/users/{user_id}/albums/add/") )
async function sendAlbumToServer(album_search_item) {

    const user_id = '67cc043c067ff14f13e357ff'

    const albumData = {
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


const albumsUrl = serverAddress + 'albums/';

// Функция удаления альбома с сервера ( @app.delete("/albums/") )
async function deleteAlbumFromServer(albumName, artistName) {
    const albumData = {
        name: albumName,
        artist: artistName,
    };

    const requestOptions = {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(albumData),
    };

    logRequestDetails('DELETE', albumsUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        const response = await fetch(albumsUrl, requestOptions);
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
    const url = serverAddress + 'api/search/albums/';
    const request = `${url}${encodeURIComponent(albumName)}`;
    console.log(`GET: ${request}`);

    const response = await fetch(request);
    return await response.json();
}


//------------------------------------------------------------------------------------------------------------- ОСНОВНЫЕ

// Удаление альбома по клику (DOM + СЕРВЕР)
// Проверяем, существует ли albumList
if (albumList) {
    // Удаление альбома по клику (DOM + СЕРВЕР)
    albumList.addEventListener('click', (event) => {
        const target = event.target;
        // Проверяем, что клик был по элементу <li>
        if (target.tagName === 'LI') {
            // Получаем данные из атрибутов data-*
            const albumName = target.dataset.albumName;
            const artistName = target.dataset.artistName;

            // Проверяем, что данные присутствуют
            if (!albumName || !artistName) {
                console.error('Не удалось удалить альбом: отсутствует albumName или artistName');
                return;
            }

            // Удаляем элемент из DOM
            target.remove();

            // Удаляем альбом на сервере
            deleteAlbumFromServer(albumName, artistName)
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
        item.textContent = `${album_search_item.album_name} — ${album_search_item.artist_name}`;  // заполняем текст варианта;
        item.style.cursor = 'pointer';  // указываем стиль;

        // добавляем действие при клике:
        item.addEventListener('click', () => {

            // Создаем элемент списка
            const li = document.createElement('li');
            li.className = 'col-6 col-sm-6 col-md-4 col-lg-3';
            li.dataset.albumName = album_search_item.album_name; // Добавляем параметр albumName
            li.dataset.artistName = album_search_item.artist_name; // Добавляем параметр artistName

            // Создаем внутренние элементы
            const cardDiv = document.createElement('div');
            cardDiv.className = 'card h-100';

            // Контейнер изображения
            const imageContainer = document.createElement('div');
            imageContainer.className = 'image-container'; // Используем класс для фона-заполнителя

            const img = document.createElement('img');
            img.src = album_search_item.image.slice(-1)[0]['#text'] || '/static/data/other/unfound.jpg';
            img.className = 'album_list_square card-img-top';
            img.alt = album_search_item.album_name;

            // Обработчики событий
            img.onload = () => {
                img.style.opacity = '1'; // Показываем изображение после загрузки
            };
            img.onerror = () => {
                img.style.display = 'none'; // Скрываем изображение в случае ошибки
            };

            imageContainer.appendChild(img);

            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';

            const albumTitle = document.createElement('h5');
            albumTitle.className = 'album_list_album card-title';
            albumTitle.textContent = album_search_item.album_name;

            const artistText = document.createElement('p');
            artistText.className = 'album_list_artist card-text text-muted';
            artistText.textContent = album_search_item.artist_name;

            // Структурируем элементы
            cardBody.appendChild(albumTitle);
            cardBody.appendChild(artistText);
            cardDiv.appendChild(imageContainer);
            cardDiv.appendChild(cardBody);
            li.appendChild(cardDiv);

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

        // data = [{"album_name": name1, "artist_name": artist1, "image": ['#text': '..', 'size': '..']}, ...]
        addAlbumBySearch(data);
    } catch (error) {
        console.error('Ошибка при поиске альбомов:', error);
    }
});