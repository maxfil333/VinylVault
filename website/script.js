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

const serverAddress = 'http://127.0.0.1:8000/'; // URL FastAPI сервера
const albumsUrl = serverAddress + 'albums/';

// Функция отправки альбома на сервер ( @app.post("/albums/") )
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

    logRequestDetails('POST', albumsUrl, requestOptions.headers, JSON.parse(requestOptions.body));

    try {
        // fetch используется для отправки HTTP-запроса
        const response = await fetch(albumsUrl, requestOptions);

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


// Добавление альбома на витрину при выборе варианта из выпадающего списка найденных альбомов  (DOM + СЕРВЕР)
function addAlbumBySearch(data) {
    dropdownMenu.innerHTML = ''; // Очищаем предыдущие варианты

    // data = [{'artist1': .., 'name1': ..}, {'artist2': .., 'name2': ..}]
    // для каждого элемента из выпадающего списка (найденные в результате поиска альбомы/исполнители):
    data.forEach((option) => {
        const item = document.createElement('div');  // создаём контейнер для варианта (внутри dropdown);
        item.textContent = `${option.name} — ${option.artist}`;  // заполняем текст варианта;
        item.style.cursor = 'pointer';  // указываем стиль;

        // добавляем действие при клике:
        item.addEventListener('click', () => {

            // Создаем элемент списка
            const li = document.createElement('li');
            li.className = 'col-6 col-sm-6 col-md-4 col-lg-3';
            li.dataset.albumName = option.name; // Добавляем параметр albumName
            li.dataset.artistName = option.artist; // Добавляем параметр artistName

            // Создаем внутренние элементы
            const cardDiv = document.createElement('div');
            cardDiv.className = 'card h-100';

            // Контейнер изображения
            const imageContainer = document.createElement('div');
            imageContainer.className = 'image-container'; // Используем класс для фона-заполнителя

            const img = document.createElement('img');
            img.src = option.image.slice(-1)[0]['#text'] || 'data/other/unfound.jpg';
            img.className = 'album_list_square card-img-top';
            img.alt = option.name;

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
            albumTitle.textContent = option.name;

            const artistText = document.createElement('p');
            artistText.className = 'album_list_artist card-text text-muted';
            artistText.textContent = option.artist;

            // Структурируем элементы
            cardBody.appendChild(albumTitle);
            cardBody.appendChild(artistText);
            cardDiv.appendChild(imageContainer);
            cardDiv.appendChild(cardBody);
            li.appendChild(cardDiv);

            albumList.appendChild(li); // Добавляем в список
            albumSearchInput.value = ''; // Очищаем поле ввода
            sendAlbumToServer(option.name, option.artist); // Отправляем альбом на сервер !!!
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
    fetch(`${albumsUrl}${encodeURIComponent(albumName)}`)
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                console.log('No albums found.');
                return;
            }
            addAlbumBySearch(data);  // data = [{'artist1': .., 'name1': ..}, {'artist2': .., 'name2': ..}]
        })
        .catch(error => {
            console.error('Ошибка при поиске альбомов:', error);
        });
});
