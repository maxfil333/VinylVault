//----------------------------------------------------------------------------------------------------------- ПЕРЕМЕННЫЕ

const albumList = document.getElementById('album-list');
const albumSearchInput = document.getElementById('album-search');
const dropdownMenu = document.getElementById('dropdown-menu');
const searchAlbumBtn = document.getElementById('search-album-btn');


//---------------------------------------------------------------------------------------------------------------- UTILS

function logRequestDetails(method, url, headers, body) {
    console.log(`${method}: Метод:`, method);
    console.log(`${method}: URL:`, url);
    console.log(`${method}: Заголовки:`, headers);
    if (body) {
        console.log(`${method}: Тело запроса:`, body);
    }
}


//--------------------------------------------------------------------------------------------------- ВИЗУАЛЬНЫЕ ЭФФЕКТЫ

// Эффект увеличения альбома при наведении мыши
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


//--------------------------------------------------------------------------------------------------------------- СЕРВЕР

const albumUrl = 'http://127.0.0.1:8000/albums/'; // URL FastAPI сервера

// Функция отправки альбома на сервер
async function sendAlbumToServer(albumName, artistName) {
    const albumData = {
        name: albumName,
        artist: artistName,
    };

    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(albumData),
    };

    logRequestDetails('POST', albumUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(albumUrl, requestOptions);

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


// Функция удаления альбома с сервера
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

    logRequestDetails('DELETE', albumUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(albumUrl, requestOptions);

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


//------------------------------------------------------------------------------------------------------------- ОСНОВНЫЕ

// Удаление альбома по клику (DOM + СЕРВЕР)
albumList.addEventListener('click', (event) => {
    if (event.target.tagName === 'LI') {
        event.target.remove();  // Удаляем элемент из списка
        const albumName = event.target.dataset.albumName;  // получаем название альбома
        const artistName = event.target.dataset.artistName;  // получаем название артиста
        deleteAlbumFromServer(albumName, artistName);  // Удаляем альбом на сервере
    }
});


// --- Добавление альбома при выборе варианта из выпадающего списка найденных альбомов  (DOM + СЕРВЕР) ---
function addAlbumBySearch(options) {
    dropdownMenu.innerHTML = ''; // Очищаем предыдущие варианты

    // для каждого элемента из выпадающего списка (найденные в результате поиска альбомы/исполнители):
    options.forEach((option) => {
        const item = document.createElement('div');  // создаём контейнер для варианта (внутри dropdown);
        const string_option = `${option.name} — ${option.artist}`;
        item.textContent = string_option;  // заполняем текст варианта;
        item.style.cursor = 'pointer';  // указываем стиль;
        item.addEventListener('click', () => {  // добавляем действие при клике:

            // Создаем элемент списка
            const li = document.createElement('li');
            li.dataset.albumName = option.name; // Добавляем параметр albumName
            li.dataset.artistName = option.artist; // Добавляем параметр artistName

            // Создаем внутренние элементы
            const squareDiv = document.createElement('div');
            squareDiv.className = 'album_list_square';

            const albumDiv = document.createElement('div');
            albumDiv.className = 'album_list_album';
            albumDiv.textContent = option.name; // Название альбома

            const artistDiv = document.createElement('div');
            artistDiv.className = 'album_list_artist';
            artistDiv.textContent = option.artist; // Имя исполнителя

            // Добавляем внутренние элементы в li
            li.appendChild(squareDiv);
            li.appendChild(albumDiv);
            li.appendChild(artistDiv);

            // Находим ul и добавляем элемент списка
            const albumList = document.getElementById('album-list');
            albumList.appendChild(li);

            albumSearchInput.value = ''; // Очищаем поле ввода

            sendAlbumToServer(option.name, option.artist); // Отправляем альбом на сервер

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
albumSearchInput.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        searchAlbumBtn.click();
    }
});

searchAlbumBtn.addEventListener('click', () => {
    const albumName = albumSearchInput.value.trim();
    if (albumName === '') {
        return;
    }

    // Отправляем запрос на сервер для поиска альбомов
    fetch(`${albumUrl}${encodeURIComponent(albumName)}`)
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                console.log('No albums found.');
                return;
            }
            addAlbumBySearch(data);
        })
        .catch(error => {
            console.error('Ошибка при поиске альбомов:', error);
        });
});
