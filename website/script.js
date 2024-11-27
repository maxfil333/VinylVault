//----------------------------------------------------------------------------------------------------------------------
// ПЕРЕМЕННЫЕ
const albumInput = document.getElementById('album-input');
const albumList = document.getElementById('album-list');
const addAlbumBtn = document.getElementById('add-album-btn');


//----------------------------------------------------------------------------------------------------------------------
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


//----------------------------------------------------------------------------------------------------------------------
// Удаление альбома по клику

albumList.addEventListener('click', (event) => {
    if (event.target.tagName === 'LI') {
        event.target.remove();
    }
});


//----------------------------------------------------------------------------------------------------------------------
const apiUrl = 'http://127.0.0.1:8000/albums/'; // URL FastAPI сервера

// Функция отправки альбома на сервер ----------------------------------------------------------------------------------
async function sendAlbumToServer(albumName, artistName) {
    const albumData = {
        name: albumName,
        artist: artistName,
    };

    try {
        // fetch используется для отправки HTTP-запроса.
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(albumData),
        });

        if (!response.ok) {
            throw new Error(`Ошибка: ${response.status}`);
        }

        const data = await response.json();
        console.log('Ответ от сервера:', data);
    } catch (error) {
        console.error('Ошибка при добавлении альбома:', error);
        alert('Не удалось добавить альбом!');
    }
}

// Функция добавления альбома ------------------------------------------------------------------------------------------
function addAlbum() {
    const albumName = albumInput.value.trim(); // Получаем текст из поля ввода
    if (albumName === '') {
        alert('Введите название альбома!');
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




