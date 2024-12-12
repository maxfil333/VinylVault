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

const apiUrl = 'http://127.0.0.1:8000/albums/'; // URL FastAPI сервера

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

    logRequestDetails('POST', apiUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(apiUrl, requestOptions);

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

    logRequestDetails('DELETE', apiUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(apiUrl, requestOptions);

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