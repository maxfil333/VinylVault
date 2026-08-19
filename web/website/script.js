//----------------------------------------------------------------------------------------------------------- ПЕРЕМЕННЫЕ

// Базовый URL API: тот же origin, что и страница (корректно и для localhost, и для деплоя)
const serverAddress = `${window.location.origin}/`;

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
let pendingDeletes = new Set();
let pendingAvatarFile = null;
let originalAvatarSrc = null;
let pendingAvatarObjectUrl = null;
let currentProfileUserId = null;
let currentProfileUsername = null;
let isOwnProfilePage = false;


//---------------------------------------------------------------------------------------------------------------- UTILS

// Флаг для отслеживания программных кликов кнопки поиска
let isSearchButtonClick = false;

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
        // Если был программный клик кнопки поиска, игнорируем это событие
        if (isSearchButtonClick) {
            return;
        }
        
        const clickedOnInput = input.contains(event.target);
        const clickedOnDropdown = dropdown.contains(event.target);
        const clickedOnSearchBtn = searchAlbumBtn && searchAlbumBtn.contains(event.target);

        // Если клик не по поисковому полю, не по кнопке поиска и не по меню — закрываем и очищаем
        if (!clickedOnInput && !clickedOnDropdown && !clickedOnSearchBtn) {
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

async function loadUserProfile() {
    const response = await fetch(serverAddress + 'api/me/profile', { credentials: 'include' });
    if (!response.ok) return null;
    return await response.json();
}

async function loadPublicProfile(username) {
    const response = await fetch(`${serverAddress}api/profiles/${encodeURIComponent(username)}`);
    if (!response.ok) return null;
    return await response.json();
}

async function uploadAvatar(file) {
    const user_id = await getUserIdFromSession();
    if (!user_id) {
        console.error('user_id не найден в cookie!');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    const url = `${serverAddress}api/users/${user_id}/avatar`;
    const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Ошибка загрузки: ${response.status}`);
    }
    return await response.json();
}

function setAvatarEditVisible(show) {
    const img = document.getElementById('user-avatar');
    const btn = document.getElementById('avatar-change-btn');
    if (btn) btn.style.display = show ? 'inline-block' : 'none';
    if (img) {
        img.style.cursor = show ? 'pointer' : 'default';
        img.title = show ? 'Нажмите, чтобы сменить фото' : '';
    }
}

function setupAvatarControls() {
    const img = document.getElementById('user-avatar');
    const input = document.getElementById('avatar-input');
    const btn = document.getElementById('avatar-change-btn');
    if (!img || !input) return;

    const pickFile = () => input.click();
    if (btn) btn.addEventListener('click', pickFile);
    img.addEventListener('click', () => {
        if (!isEditMode) return;
        pickFile();
    });

    setAvatarEditVisible(false);

    input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        input.value = '';
        if (!file || !isEditMode) return;
        if (pendingAvatarObjectUrl) {
            URL.revokeObjectURL(pendingAvatarObjectUrl);
        }
        pendingAvatarFile = file;
        pendingAvatarObjectUrl = URL.createObjectURL(file);
        img.src = pendingAvatarObjectUrl;
    });
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


// Функция для поиска релевантных альбомов и топ-альбомов артиста ( /api/search/mixed/{query} )
async function searchMixed(query) {
    const url = serverAddress + 'api/search/mixed/' + encodeURIComponent(query);
    console.log(`GET: ${url}`);
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) {
        throw new Error(`Ошибка поиска: ${response.status}`);
    }
    return await response.json();
}


// Загрузка альбомов пользователя из базы ( app.get("/api/users/{user_id}/albums/all/", response_model=list[VV_Album]) )
async function loadUserAlbums(userId) {
    try {
        const response = await fetch(`${serverAddress}api/users/${userId}/albums/all/`, { credentials: 'include' });
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

async function loadPublicUserAlbums(username) {
    try {
        const response = await fetch(`${serverAddress}api/profiles/${encodeURIComponent(username)}/albums`);
        const albums = await response.json();

        albumList.innerHTML = '';

        albums.forEach(album => {
            const albumCard = createAlbumCard(album);
            albumList.appendChild(albumCard);
        });
    } catch (error) {
        console.error("Ошибка загрузки публичных альбомов:", error);
    }
}

// Обработчик кнопки Log Out
function setupLogoutButton() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (response.ok || response.redirected) {
                    // Перенаправляем на welcome страницу
                    window.location.href = '/welcome';
                }
            } catch (error) {
                console.error('Ошибка при выходе:', error);
            }
        });
    }
}

function setupShareProfileButton() {
    const shareBtn = document.getElementById('share-profile-btn');
    if (!shareBtn) return;

    shareBtn.addEventListener('click', async () => {
        const profileUrl = new URL(window.location.pathname, window.location.origin).toString();

        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(profileUrl);
                shareBtn.textContent = 'Copied';
                setTimeout(() => {
                    shareBtn.textContent = 'Share';
                }, 1500);
                return;
            }
        } catch (error) {
            console.error('Не удалось скопировать ссылку:', error);
        }

        window.prompt('Ссылка на профиль:', profileUrl);
    });
}

// ... вызов функции при загрузке страницы
document.addEventListener("DOMContentLoaded", async () => {
    const pageType = document.querySelector("meta[name='page-type']")?.content;

    if (pageType === "user") {
        console.log("✅ Это страница пользователя. Загружаем альбомы...");
        currentProfileUsername = document.querySelector("meta[name='profile-username']")?.content || null;
        isOwnProfilePage = document.querySelector("meta[name='is-owner']")?.content === 'true';
        const isAuthenticated = document.querySelector("meta[name='is-authenticated']")?.content === 'true';
        if (!currentProfileUsername) {
            console.error('username профиля не найден на странице');
            return;
        }
        setupShareProfileButton();
        if (isAuthenticated) {
            setupLogoutButton();
        }

        if (isOwnProfilePage) {
            const userId = await getUserIdFromSession(); // Теперь await работает корректно
            if (!userId) {
                console.error('user_id не найден в cookie!');
                return;
            }
            currentProfileUserId = userId;
            await loadUserAlbums(userId);
            setupAvatarControls();
            try {
                const profile = await loadUserProfile();
                if (profile) {
                    currentProfileUserId = profile.user_id || currentProfileUserId;
                    const avatarEl = document.getElementById('user-avatar');
                    if (avatarEl && profile.avatar_url) {
                        avatarEl.src = `${profile.avatar_url}?t=${Date.now()}`;
                    }
                    const nameEl = document.getElementById('profile-username');
                    if (nameEl && profile.username) {
                        nameEl.textContent = profile.username;
                    }
                }
            } catch (e) {
                console.error('Профиль не загружен:', e);
            }
        } else {
            try {
                const profile = await loadPublicProfile(currentProfileUsername);
                if (profile) {
                    currentProfileUserId = profile.user_id || null;
                    const avatarEl = document.getElementById('user-avatar');
                    if (avatarEl && profile.avatar_url) {
                        avatarEl.src = `${profile.avatar_url}?t=${Date.now()}`;
                    }
                    const nameEl = document.getElementById('profile-username');
                    if (nameEl && profile.username) {
                        nameEl.textContent = profile.username;
                    }
                }
            } catch (e) {
                console.error('Публичный профиль не загружен:', e);
            }
            await loadPublicUserAlbums(currentProfileUsername);
        }
    }
});

//--------------------------------------------------------------------------------------------------------- WELCOME PAGE

// Проверка авторизации и обновление UI на welcome странице
async function checkAuthAndUpdateUI() {
    const authButtons = document.getElementById('auth-buttons');
    const userButtons = document.getElementById('user-buttons');
    
    // Если элементов нет на странице, выходим
    if (!authButtons || !userButtons) {
        return;
    }
    
    try {
        const response = await fetch('/api/auth/check', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.is_authenticated) {
            // Пользователь авторизован - показываем кнопки ME и Log Out
            authButtons.style.display = 'none';
            userButtons.style.display = 'flex';
        } else {
            // Пользователь не авторизован - показываем кнопки Log In и SIGN UP
            authButtons.style.display = 'flex';
            userButtons.style.display = 'none';
        }
    } catch (error) {
        console.error('Ошибка при проверке авторизации:', error);
        // В случае ошибки показываем кнопки для неавторизованных
        authButtons.style.display = 'flex';
        userButtons.style.display = 'none';
    }
}

// Инициализация welcome страницы
document.addEventListener("DOMContentLoaded", async () => {
    // Проверяем, есть ли элементы welcome страницы
    const authButtons = document.getElementById('auth-buttons');
    const userButtons = document.getElementById('user-buttons');
    if (authButtons && userButtons) {
        // Это welcome страница - проверяем авторизацию и настраиваем кнопки
        await checkAuthAndUpdateUI();
        setupLogoutButton();
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
    img.src = album.cover_url || (window.__VV_UNFOUND_IMG__ || '/static/data/other/unfound.jpg');
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
    deleteButton.style.display = isEditMode ? 'block' : 'none'; // Скрываем кнопку по умолчанию
    deleteButton.onclick = (event) => {
        event.stopPropagation();
        if (!isEditMode) return;
        pendingDeletes.add(album.album_id);
        li.remove();
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
            const item = document.createElement(albumList ? 'div' : 'a');
            item.className = 'dropdown-item d-flex align-items-center justify-content-between';
            item.style.cursor = 'pointer';
            if (!albumList) {
                item.href = '/explore';
                item.style.textDecoration = 'none';
                item.style.color = 'inherit';
            }

            const textSpan = document.createElement('span');
            textSpan.textContent = `${album.album_name} — ${album.artist_name}`;
            textSpan.style.whiteSpace = 'nowrap';
            textSpan.style.overflow = 'hidden';
            textSpan.style.textOverflow = 'ellipsis';
            textSpan.style.paddingRight = '8px';

            const img = document.createElement('img');
            const cover = album.cover_url || album.cover_url_reserve || (window.__VV_UNFOUND_IMG__ || '/static/data/other/unfound.jpg');
            img.src = cover;
            img.alt = album.album_name;
            img.style.width = '32px';
            img.style.height = '32px';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '4px';
            img.referrerPolicy = 'no-referrer';

            item.appendChild(textSpan);
            item.appendChild(img);

            if (albumList) {
                item.addEventListener('click', () => {
                    const li = createAlbumCard(album);
                    albumList.appendChild(li);
                    albumSearchInput.value = '';
                    sendAlbumToServer(album);
                    LfmSearchDropdownMenu.style.display = 'none';
                });
            }

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
if (albumSearchInput && searchAlbumBtn) {
    albumSearchInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            isSearchButtonClick = true;
            searchAlbumBtn.click();
        }
    });

    searchAlbumBtn.addEventListener('click', async () => {
        const albumName = albumSearchInput.value.trim();
        if (albumName === '') {
            return;
        }

        try {
            const data = await searchMixed(albumName);
            addAlbumBySearchGrouped(data);
            setTimeout(() => {
                isSearchButtonClick = false;
            }, 0);
        } catch (error) {
            console.error('Ошибка при поиске альбомов:', error);
            setTimeout(() => {
                isSearchButtonClick = false;
            }, 0);
        }
    });
}

if (!albumList && albumSearchInput) {
    let welcomeSearchTimer;
    albumSearchInput.addEventListener('input', () => {
        clearTimeout(welcomeSearchTimer);
        const query = albumSearchInput.value.trim();
        welcomeSearchTimer = setTimeout(async () => {
            if (!query) {
                if (LfmSearchDropdownMenu) LfmSearchDropdownMenu.style.display = 'none';
                return;
            }
            try {
                const data = await searchMixed(query);
                addAlbumBySearchGrouped(data);
            } catch (error) {
                console.error('Ошибка при поиске альбомов:', error);
            }
        }, 400);
    });
}

//------------------------------------------------------------------------------------------------- РЕЖИМ РЕДАКТИРОВАНИЯ

function setSearchEnabled(enabled) {
    if (albumSearchInput) albumSearchInput.disabled = !enabled;
    if (searchAlbumBtn) searchAlbumBtn.disabled = !enabled;
    if (!enabled && LfmSearchDropdownMenu) {
        LfmSearchDropdownMenu.style.display = 'none';
    }
}

function enableEditMode() {
    if (!isOwnProfilePage) return;
    isEditMode = true;
    editBtn.style.display = 'none';
    saveCancelControls.style.display = 'flex';
    pendingDeletes = new Set();
    pendingAvatarFile = null;
    const avatarImg = document.getElementById('user-avatar');
    originalAvatarSrc = avatarImg ? avatarImg.src : null;
    
    // Сохраняем оригинальный порядок
    originalOrder = Array.from(albumList.children).map(li => ({
        albumId: li.dataset.albumId,
        element: li
    }));
    
    // Добавляем класс edit-mode к контейнеру альбомов
    albumList.classList.add('edit-mode');
    
    // Делаем альбомы перетаскиваемыми
    makeAlbumsDraggable();
    
    // Показываем кнопки удаления
    showDeleteButtons();

    setAvatarEditVisible(true);
    setSearchEnabled(false);
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
    
    // Скрываем кнопки удаления
    hideDeleteButtons();

    setAvatarEditVisible(false);
    setSearchEnabled(true);
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

// Функция для показа кнопок удаления
function showDeleteButtons() {
    const deleteButtons = albumList.querySelectorAll('.delete-album-button');
    deleteButtons.forEach(button => {
        button.style.display = 'block';
    });
}

// Функция для скрытия кнопок удаления
function hideDeleteButtons() {
    const deleteButtons = albumList.querySelectorAll('.delete-album-button');
    deleteButtons.forEach(button => {
        button.style.display = 'none';
    });
}

// Переменная для отслеживания текущей целевой позиции
let currentTargetIndex = -1;

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
    
    // Сохраняем текущую позицию перетаскиваемого элемента
    currentTargetIndex = Array.from(albumList.children).indexOf(draggedElement);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    
    // Убираем все drag-over классы
    const albumItems = albumList.querySelectorAll('li');
    albumItems.forEach(item => item.classList.remove('drag-over'));
    
    draggedElement = null;
    currentTargetIndex = -1;
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    if (this !== draggedElement && this.tagName === 'LI') {
        const targetIndex = Array.from(albumList.children).indexOf(this);
        
        // Если позиция изменилась, перемещаем элементы в реальном времени
        if (currentTargetIndex !== targetIndex && currentTargetIndex !== -1) {
            currentTargetIndex = targetIndex;
            
            // Создаем временную коллекцию элементов для безопасного перемещения
            const children = Array.from(albumList.children);
            const draggedIndex = children.indexOf(draggedElement);
            
            // Удаляем перетаскиваемый элемент из DOM
            draggedElement.remove();
            
            // Вставляем его на новую позицию
            if (draggedIndex < targetIndex) {
                // Перетаскиваем вниз
                if (targetIndex < children.length - 1) {
                    albumList.insertBefore(draggedElement, children[targetIndex + 1]);
                } else {
                    albumList.appendChild(draggedElement);
                }
            } else {
                // Перетаскиваем вверх
                albumList.insertBefore(draggedElement, this);
            }
        }
    }
}

function handleDragEnter(e) {
    e.preventDefault();
    // Проверяем, что перетаскивание происходит над карточкой (li элементом)
    if (this !== draggedElement && this.tagName === 'LI') {
        this.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    // Убираем рамку только если мы действительно покидаем элемент
    if (!this.contains(e.relatedTarget)) {
        this.classList.remove('drag-over');
    }
}

function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    
    // Финализируем позицию (элемент уже перемещен в handleDragOver)
}

async function saveAlbumOrder() {
    const user_id = currentProfileUserId || await getUserIdFromSession();
    if (!user_id) {
        console.error('user_id не найден в cookie!');
        return;
    }

    // Удаления и порядок уходят одним запросом: при сбое коллекция в базе остаётся прежней
    const layout = {
        deleted_album_ids: [...pendingDeletes],
        order: Array.from(albumList.children).map(li => li.dataset.albumId),
    };

    try {
        const url = `${serverAddress}api/users/${user_id}/albums/layout/`;
        const response = await fetch(url, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(layout),
        });
        if (!response.ok) {
            throw new Error(`Ошибка: ${response.status}`);
        }
        pendingDeletes.clear();
    } catch (error) {
        console.error('Ошибка при сохранении изменений:', error);
        await loadUserAlbums(user_id);
        alert('Не удалось сохранить изменения');
        return;
    }

    if (pendingAvatarFile) {
        try {
            const data = await uploadAvatar(pendingAvatarFile);
            const avatarImg = document.getElementById('user-avatar');
            if (avatarImg && data && data.avatar_url) {
                avatarImg.src = `${data.avatar_url}?t=${Date.now()}`;
            }
        } catch (error) {
            console.error('Ошибка при загрузке аватара:', error);
            alert('Альбомы сохранены, но аватар загрузить не удалось');
        }
    }

    if (pendingAvatarObjectUrl) {
        URL.revokeObjectURL(pendingAvatarObjectUrl);
        pendingAvatarObjectUrl = null;
    }
    pendingAvatarFile = null;
    disableEditMode();
}

function cancelEdit() {
    albumList.innerHTML = '';
    originalOrder.forEach(item => {
        albumList.appendChild(item.element);
    });

    const avatarImg = document.getElementById('user-avatar');
    if (avatarImg && originalAvatarSrc) {
        avatarImg.src = originalAvatarSrc;
    }
    if (pendingAvatarObjectUrl) {
        URL.revokeObjectURL(pendingAvatarObjectUrl);
        pendingAvatarObjectUrl = null;
    }
    pendingAvatarFile = null;
    pendingDeletes = new Set();

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