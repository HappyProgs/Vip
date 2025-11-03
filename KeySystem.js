(function() {
  'use strict';

  function GM_getValue(key, defaultValue) {
    const val = localStorage.getItem(key);
    return val === null ? defaultValue : val;
  }
  function GM_setValue(key, value) {
    localStorage.setItem(key, value);
  }

  function generateHWID() {
    let canvas = document.createElement('canvas');
    let ctx = canvas.getContext('2d');
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.fillStyle = "#f60";
    ctx.fillRect(125,1,62,20);
    ctx.fillStyle = "#069";
    ctx.fillText("HWID", 2,15);
    ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
    ctx.fillText("HWID", 4,17);
    let hash = 0;
    let str = canvas.toDataURL();
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return (hash >>> 0).toString(16);
  }

  function getOrCreateHWID() {
    let hwid = GM_getValue('hwid');
    if (!hwid) {
      hwid = generateHWID();
      GM_setValue('hwid', hwid);
    }
    return hwid;
  }

  function parseDuration(durationStr) {
    const match = durationStr?.match(/(\d+)([smhdw]|year)/);
    if (!match) return null;
    const val = parseInt(match[1]);
    const unit = match[2];
    const now = Date.now();
    const ms = {
      s: 1000,
      m: 60 * 1000,
      h: 60 * 60 * 1000,
      d: 24 * 60 * 60 * 1000,
      w: 7 * 24 * 60 * 60 * 1000,
      year: 365 * 24 * 60 * 60 * 1000
    }[unit];
    return now + val * ms;
  }

  function createModal() {
    const modal = document.createElement('div');
    modal.id = 'key-modal';
    modal.innerHTML = `
      <div class="protected-label">Protected BY HappyProgTg</div>
      <h2>Login</h2>
      <input type="text" id="key-input" placeholder="Login">
      <button id="login-btn">Enter</button>
      <p class="key-info">Don't have access? <a href="https://t.me/EWFAQ" target="_blank">Tg - @EWFAQ</a></p>
      <p id="hwid-info" style="font-size: 10px; margin-top: 5px; color: #999;"></p>
    `;
    document.body.appendChild(modal);

    document.getElementById('hwid-info').textContent = `HWID: ${getOrCreateHWID()}`;
    document.getElementById('login-btn').addEventListener('click', checkKey);

    makeDraggable(modal);
  }

  function makeDraggable(element) {
    let offsetX = 0, offsetY = 0, isDown = false;

    element.addEventListener('mousedown', e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.tagName === 'A') return;
      isDown = true;
      offsetX = e.clientX - element.offsetLeft;
      offsetY = e.clientY - element.offsetTop;
      element.style.cursor = 'grabbing';
    });

    document.addEventListener('mouseup', () => {
      isDown = false;
      element.style.cursor = 'grab';
    });

    document.addEventListener('mousemove', e => {
      if (!isDown) return;
      e.preventDefault();
      element.style.left = `${e.clientX - offsetX}px`;
      element.style.top = `${e.clientY - offsetY}px`;
      element.style.transform = 'none';
    });
  }

  function checkKey() {
    const loginInput = document.getElementById('key-input').value.trim();
    const hwid = getOrCreateHWID();

    if (!loginInput) {
      alert('Введите логин');
      return;
    }

    fetch('https://raw.githubusercontent.com/HappyProgs/goida/main/keys.txt')
      .then(res => res.text())
      .then(data => {
        const lines = data.split('\n').map(line => line.trim()).filter(Boolean);
        const now = Date.now();

        for (const line of lines) {
          const [login, keyHWID, durationStr] = line.split(';');
          const expiryTime = parseDuration(durationStr);

          if (login === loginInput) {
            if (keyHWID === 'null') {
              alert('Этот логин ещё не активирован. Связываю HWID...');
              // теоретически тут можно добавить запись на сервер, если бы был API
              GM_setValue('savedLogin', login);
              alert('Активировано. Загрузка...');
              loadMainScript();
              return;
            }

            if (keyHWID !== hwid) {
              alert('Этот логин уже используется другим HWID');
              return;
            }

            if (expiryTime && now > expiryTime) {
              alert('Ключ истёк');
              return;
            }

            GM_setValue('savedLogin', login);
            alert('Успешный вход. Загрузка...');
            loadMainScript();
            return;
          }
        }

        alert('Неверный логин');
      })
      .catch(() => alert('Ошибка загрузки ключей'));
  }

  function loadMainScript() {
    const script = document.createElement('script');
    script.src = "https://ewfaq.ru/script.js";
    script.onload = () => {
      console.log('Main script loaded');
      const modal = document.getElementById('key-modal');
      if (modal) modal.style.display = 'none';
    };
    script.onerror = () => alert('Ошибка загрузки основного скрипта');
    document.body.appendChild(script);
  }

  const style = document.createElement('style');
  style.textContent = `
    #key-modal {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: rgba(47,47,47,0.85);
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
      z-index: 10000;
      font-family: 'Arial', sans-serif;
      color: white;
      width: 320px;
      display: flex;
      flex-direction: column;
      align-items: center;
      user-select: none;
      cursor: grab;
    }
    #key-modal input, #key-modal button {
      width: 100%;
      margin-bottom: 10px;
      padding: 10px;
      border: none;
      border-radius: 6px;
      box-sizing: border-box;
      font-size: 16px;
    }
    #key-modal input {
      background: rgba(60,60,60,0.9);
      color: white;
    }
    #key-modal button {
      background: linear-gradient(90deg, #ff4b2b, #ff9269);
      color: white;
      font-weight: bold;
      cursor: pointer;
    }
  `;
  document.head.appendChild(style);

  createModal();
})();
