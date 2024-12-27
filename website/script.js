//----------------------------------------------------------------------------------------------------------- ПЕРЕМЕННЫЕ

const albumInput = document.getElementById('album-input');
const albumList = document.getElementById('album-list');
const addAlbumBtn = document.getElementById('add-album-btn');


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

// Выделение альбома при наведении мыши
albumList.addEventListener('mouseover', (event) => {
    if (event.target.tagName === 'LI') {
        event.target.style.backgroundColor = '#f0f0f0';
    }
});

albumList.addEventListener('mouseout', (event) => {
    if (event.target.tagName === 'LI') {
        event.target.style.backgroundColor = ''; // Возвращаем оригинальный цвет
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

// Добавление альбома (DOM + СЕРВЕР)
function addAlbum() {
    const albumName = albumInput.value.trim(); // Получаем текст из поля ввода
    if (albumName === '') {
        return;
    }

    // Добавляем альбом локально
    const li = document.createElement('li');
    li.textContent = albumName;
    albumList.appendChild(li);

    // Очищаем поле ввода
    albumInput.value = '';

    // Отправляем альбом на сервер (с фиктивным исполнителем)
    const artistName = 'Неизвестный исполнитель';
    sendAlbumToServer(albumName, artistName);
}

// Обработчик нажатия на кнопку
addAlbumBtn.addEventListener('click', addAlbum);


// Удаление альбома по клику (DOM + СЕРВЕР)
albumList.addEventListener('click', (event) => {
    if (event.target.tagName === 'LI') {
        const albumName = event.target.textContent.trim(); // Получаем название альбома
        event.target.remove(); // Удаляем элемент из списка

        const artistName = 'Неизвестный исполнитель';
        deleteAlbumFromServer(albumName, artistName); // Удаляем альбом на сервере
    }
});


// Получаем элементы поиска
const albumSearchInput = document.getElementById('album-search');
const searchAlbumBtn = document.getElementById('search-album-btn');
const dropdownMenu = document.getElementById('dropdown-menu');
const albumSearchList = document.getElementById('album-search-list');


// --- Добавление альбома через поиск (DOM + СЕРВЕР) ---
function addAlbumBySearch(options) {
    dropdownMenu.innerHTML = ''; // Очищаем предыдущие варианты

    // для каждого элемента из выпадающего списка (найденные в результате поиска альбомы/исполнители):
    options.forEach((option) => {
        const item = document.createElement('div');  // создаём контейнер для варианта (внутри dropdown);
        item.textContent = option;  // заполняем текст варианта;
        item.style.cursor = 'pointer';  // указываем стиль;
        item.addEventListener('click', () => {  // добавляем действие при клике:

            const li = document.createElement('li');  // создаем элемент списка;
            li.textContent = option;  // заполняем его textContent значением варианта;
            albumList.appendChild(li); // добавляем элемент в список (список альбомов).

            // Очищаем поле ввода
            albumSearchInput.value = '';

            // Отправляем альбом на сервер (с фиктивным исполнителем)
            const albumName = option;
            const artistName = 'Неизвестный исполнитель';
            sendAlbumToServer(albumName, artistName);

            dropdownMenu.style.display = 'none'; // Скрываем меню после выбора
        });
        dropdownMenu.appendChild(item); // Добавляем элемент в меню
    });

    dropdownMenu.style.display = 'block'; // Показываем меню
    dropdownMenu.style.left = `${albumSearchInput.offsetLeft}px`; // Позиция по горизонтали
    dropdownMenu.style.top = `${albumSearchInput.offsetTop + albumSearchInput.offsetHeight}px`; // Позиция по вертикали
}

// --- Обработчик кнопки поиска ---
searchAlbumBtn.addEventListener('click', () => {
    const albumName = albumSearchInput.value.trim();
    if (albumName === '') {
        return;
    }

    // Отправляем запрос на сервер для поиска альбомов
    fetch(`${albumUrl}${albumName}`)
        .then(response => response.json())
        .then(data => {
            const options = data.map(album => `${album.name} - ${album.artist}`);
            addAlbumBySearch(options);
        })
        .catch(error => {
            console.error('Ошибка при поиске альбомов:', error);
        });
});
