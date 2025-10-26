//----------------------------------------------------------------------------------------------------------- ПЕРЕМЕННЫЕ

const serverAddress = 'http://127.0.0.1:8000/'; // URL FastAPI сервера

const albumList = document.getElementById('album-list');
const albumSearchInput = document.getElementById('album-search');
const LfmSearchDropdownMenu = document.getElementById('lfm_search-dropdown-menu');
const searchAlbumBtn = document.getElementById('search-album-btn');

// Элементы для редактирования
const editBtn = document.getElementById('edit-btn');
const saveBtn = document.getElementById('save-btn');
const cancelBtn = document.getElementById('cancel-btn');
const saveCancelControls = document.getElementById('save-cancel-controls');

// Переменные для режима редактирования
let isEditMode = false;
let originalOrder = [];
let draggedElement = null;


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


// Закрытие выпадающего меню при клике вне него
function enableDropdownAutoClose(dropdown, input) {
    if (!dropdown || !input) return;
    let isMenuOpen = false;
    // Перехватываем открытие меню
    const observer = new MutationObserver(() => {
        const visible = dropdown.style.display !== 'none';
        if (visible && !isMenuOpen) {
            document.addEventListener('click', onClickOutside, true);
            isMenuOpen = true;
        } else if (!visible && isMenuOpen) {
            document.removeEventListener('click', onClickOutside, true);
            isMenuOpen = false;
        }
    });
    observer.observe(dropdown, { attributes: true, attributeFilter: ['style'] });
    function onClickOutside(event) {
        const clickedOnInput = input.contains(event.target);
        const clickedOnDropdown = dropdown.contains(event.target);

        // Если клик не по поисковому полю и не по меню — закрываем и очищаем
        if (!clickedOnInput && !clickedOnDropdown) {
            dropdown.style.display = 'none';
            input.value = ''; // очищаем поле поиска
        }
    }
}


// Закрытие выпадающего меню при клике вне него (инициализация после загрузки DOM)
document.addEventListener('DOMContentLoaded', () => {
    enableDropdownAutoClose(LfmSearchDropdownMenu, albumSearchInput);
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
    
    // Если мы в режиме редактирования, делаем элемент перетаскиваемым
    if (isEditMode) {
        li.draggable = true;
        li.addEventListener('dragstart', handleDragStart);
        li.addEventListener('dragend', handleDragEnd);
        li.addEventListener('dragover', handleDragOver);
        li.addEventListener('drop', handleDrop);
        li.addEventListener('dragenter', handleDragEnter);
        li.addEventListener('dragleave', handleDragLeave);
    }

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
    LfmSearchDropdownMenu.innerHTML = '';

    // helper для рендера группы
    const renderGroup = (titleText, items) => {
        const hasItems = Array.isArray(items) && items.length > 0;
        const header = document.createElement('div');
        header.textContent = titleText;
        header.className = 'dropdown-header text-muted';
        header.style.fontWeight = 'bold';
        header.style.padding = '6px 12px';
        LfmSearchDropdownMenu.appendChild(header);

        if (!hasItems) {
            const empty = document.createElement('div');
            empty.textContent = 'Нет результатов';
            empty.className = 'dropdown-item text-muted';
            LfmSearchDropdownMenu.appendChild(empty);
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
                LfmSearchDropdownMenu.style.display = 'none';
            });

            LfmSearchDropdownMenu.appendChild(item);
        });
    };

    renderGroup('Albums', result.albums);
    renderGroup('Artist\'s top-albums', result.artist_top_albums);

    LfmSearchDropdownMenu.style.display = 'block';
    LfmSearchDropdownMenu.style.left = `${albumSearchInput.offsetLeft}px`;
    LfmSearchDropdownMenu.style.top = `${albumSearchInput.offsetTop + albumSearchInput.offsetHeight}px`;
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

//----------------------------------------------------------------------------------------------------------- РЕЖИМ РЕДАКТИРОВАНИЯ

// Функция для включения режима редактирования
function enableEditMode() {
    isEditMode = true;
    editBtn.style.display = 'none';
    saveCancelControls.style.display = 'flex';
    
    // Сохраняем оригинальный порядок
    originalOrder = Array.from(albumList.children).map(li => ({
        albumId: li.dataset.albumId,
        element: li
    }));
    
    // Добавляем класс edit-mode к контейнеру альбомов
    albumList.classList.add('edit-mode');
    
    // Делаем альбомы перетаскиваемыми
    makeAlbumsDraggable();
}

// Функция для отключения режима редактирования
function disableEditMode() {
    isEditMode = false;
    editBtn.style.display = 'block';
    saveCancelControls.style.display = 'none';
    
    // Убираем класс edit-mode
    albumList.classList.remove('edit-mode');
    
    // Убираем drag-and-drop функциональность
    removeDragAndDrop();
}

// Функция для создания drag-and-drop функциональности
function makeAlbumsDraggable() {
    const albumItems = albumList.querySelectorAll('li');
    
    albumItems.forEach(item => {
        item.draggable = true;
        
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragenter', handleDragEnter);
        item.addEventListener('dragleave', handleDragLeave);
    });
}

// Функция для удаления drag-and-drop функциональности
function removeDragAndDrop() {
    const albumItems = albumList.querySelectorAll('li');
    
    albumItems.forEach(item => {
        item.draggable = false;
        item.removeEventListener('dragstart', handleDragStart);
        item.removeEventListener('dragend', handleDragEnd);
        item.removeEventListener('dragover', handleDragOver);
        item.removeEventListener('drop', handleDrop);
        item.removeEventListener('dragenter', handleDragEnter);
        item.removeEventListener('dragleave', handleDragLeave);
    });
}

// Обработчики drag-and-drop событий
function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.outerHTML);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    draggedElement = null;
    
    // Убираем все drag-over классы
    const albumItems = albumList.querySelectorAll('li');
    albumItems.forEach(item => item.classList.remove('drag-over'));
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(e) {
    e.preventDefault();
    if (this !== draggedElement) {
        this.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    
    if (this !== draggedElement) {
        // Вставляем перетаскиваемый элемент перед текущим
        albumList.insertBefore(draggedElement, this);
    }
}

// Функция для сохранения нового порядка
async function saveAlbumOrder() {
    const user_id = await getUserIdFromSession();
    if (!user_id) {
        console.error('user_id не найден в cookie!');
        return;
    }
    
    // Получаем новый порядок альбомов
    const newOrder = Array.from(albumList.children).map((li, index) => ({
        album_id: li.dataset.albumId,
        order: index
    }));
    
    const requestOptions = {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(newOrder),
    };
    
    const url = `${serverAddress}api/users/${user_id}/albums/reorder/`;
    
    try {
        const response = await fetch(url, requestOptions);
        if (!response.ok) {
            throw new Error(`Ошибка: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Порядок альбомов сохранен:', data);
        
        // Отключаем режим редактирования
        disableEditMode();
        
    } catch (error) {
        console.error('Ошибка при сохранении порядка альбомов:', error);
        alert('Не удалось сохранить порядок альбомов');
    }
}

// Функция для отмены изменений
function cancelEdit() {
    // Восстанавливаем оригинальный порядок
    albumList.innerHTML = '';
    originalOrder.forEach(item => {
        albumList.appendChild(item.element);
    });
    
    // Отключаем режим редактирования
    disableEditMode();
}

// Обработчики событий для кнопок редактирования
if (editBtn) {
    editBtn.addEventListener('click', enableEditMode);
}

if (saveBtn) {
    saveBtn.addEventListener('click', saveAlbumOrder);
}

if (cancelBtn) {
    cancelBtn.addEventListener('click', cancelEdit);
}