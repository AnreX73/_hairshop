document.addEventListener('alpine:init', () => {
    // socketPath можно передать параметром: x-data="supportChat('/ws/chat/operator/<id>/')"
    // Второй параметр — URL загрузки фото.
    Alpine.data('supportChat', (socketPathParam = '', uploadUrlParam = '') => ({
        open: false, connected: false, connecting: false, sending: false,
        uploading: false, operator: false, messages: [], draft: '', error: '',
        status: '', socket: null, socketPath: '', uploadUrl: '', retryTimer: null,
        retries: 0, pending: null,
        init() {
            this.socketPath = socketPathParam || this.$root.dataset.socketPath || '';
            this.uploadUrl = uploadUrlParam || this.$root.dataset.uploadUrl || '';
            this.operator = Boolean(this.socketPath);
            if (!this.operator && new URLSearchParams(location.search).get('chat') === 'open') {
                this.show();
            }
        },
        show() {
            this.open = true;
            this.retries = 0;
            this.connect();
            this.$nextTick(() => this.$refs.input?.focus());
        },
        close() {
            this.open = false;
            this.stop();
            this.$refs.launcher?.focus();
        },
        stop() {
            clearTimeout(this.retryTimer);
            const socket = this.socket;
            this.socket = null;
            socket?.close();
            this.connected = false;
            this.connecting = false;
            this.sending = false;
            this.uploading = false;
        },
        destroy() {
            this.open = false;
            this.stop();
        },
        csrfToken() {
            return document.querySelector('meta[name="csrf-token"]')?.content
                || this.$root.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        },
        ensureUploadUrl() {
            if (this.uploadUrl) return;
            const match = this.socketPath.match(/^\/ws\/chat\/operator\/([^/]+)\/$/);
            this.uploadUrl = match
                ? `/chat/operator/${match[1]}/upload/`
                : '/chat/upload/';
        },
        async connect() {
            if (!this.open || this.connected || this.connecting) return;
            clearTimeout(this.retryTimer);
            this.connecting = true;
            this.error = '';
            this.status = 'Подключаемся…';
            try {
                if (!this.socketPath) {
                    const response = await fetch(this.$root.dataset.startUrl, {
                        method: 'POST', credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken() },
                    });
                    if (response.status === 403) {
                        throw new Error('Сессия устарела. Обновите страницу и попробуйте снова.');
                    }
                    if (!response.ok) {
                        throw new Error(`Не удалось открыть чат (код ${response.status}). Попробуйте ещё раз.`);
                    }
                    this.socketPath = (await response.json()).socket_path;
                }
                this.ensureUploadUrl();
                if (!this.open) return;
                const socket = new WebSocket(
                    `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${this.socketPath}`
                );
                this.socket = socket;
                socket.onmessage = (event) => {
                    if (this.socket !== socket) return;
                    let data;
                    try { data = JSON.parse(event.data); } catch { return; }
                    if (data.type === 'history') {
                        data.messages.forEach(message => this.addMessage(message));
                        this.connected = true;
                        this.connecting = false;
                        this.retries = 0;
                        this.status = '';
                        if (this.pending && !this.messages.some(
                            m => m.client_id === this.pending.client_id && m.is_staff === this.operator
                        )) {
                            this.sending = true;
                            socket.send(JSON.stringify(this.pending));
                        }
                    } else if (data.type === 'message') {
                        this.addMessage(data.message);
                    } else if (data.type === 'error') {
                        this.error = data.message;
                        this.sending = false;
                    }
                };
                socket.onclose = (event) => {
                    if (this.socket !== socket) return;
                    this.socket = null;
                    this.connected = false;
                    this.connecting = false;
                    this.sending = false;
                    this.uploading = false;
                    this.status = 'Соединение прервано';
                    if (event.code !== 1000) {
                        console.warn('[chat] соединение закрыто', event.code, event.reason || '');
                    }
                    if (event.code === 4403 || event.code === 1008) {
                        this.socketPath = this.operator ? this.socketPath : '';
                        this.error = 'Доступ к чату недоступен. Попробуйте подключиться снова.';
                    } else if (this.retries >= 5) {
                        this.error = 'Не удалось подключиться к серверу чата. Обновите страницу.';
                    } else {
                        this.scheduleRetry();
                    }
                };
                socket.onerror = () => { this.status = 'Не удалось подключиться'; };
            } catch (error) {
                this.connecting = false;
                this.error = error.message;
                this.status = 'Чат временно недоступен';
                this.scheduleRetry();
            }
        },
        scheduleRetry() {
            if (!this.open || this.retries >= 5) return;
            const delay = Math.min(1000 * 2 ** this.retries++, 15000);
            this.retryTimer = setTimeout(() => this.connect(), delay);
        },
        addMessage(message) {
            if (!this.messages.some(item => item.id === message.id)) {
                this.messages.push(message);
                this.messages.sort((a, b) => a.id - b.id);
            }
            if (this.pending?.client_id === message.client_id && message.is_staff === this.operator) {
                if (this.draft.trim() === this.pending.text) this.draft = '';
                this.pending = null;
                this.sending = false;
            }
            this.$nextTick(() => {
                if (this.$refs.messages) {
                    this.$refs.messages.scrollTop = this.$refs.messages.scrollHeight;
                }
            });
        },
        newClientId() {
            const bytes = crypto.getRandomValues(new Uint8Array(16));
            bytes[6] = (bytes[6] & 15) | 64;
            bytes[8] = (bytes[8] & 63) | 128;
            const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
            return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
        },
        send() {
            if (!this.connected || this.sending || this.uploading || !this.draft.trim()
                || this.socket?.readyState !== WebSocket.OPEN) return;
            this.error = '';
            const text = this.draft.trim();
            if (!this.pending || this.pending.text !== text) {
                this.pending = { text, client_id: this.newClientId() };
            }
            this.sending = true;
            this.socket.send(JSON.stringify(this.pending));
        },
        compressImage(file, maxPx) {
            return new Promise((resolve, reject) => {
                const image = new Image();
                image.onload = () => {
                    const ratio = Math.min(maxPx / image.width, maxPx / image.height, 1);
                    const canvas = document.createElement('canvas');
                    canvas.width = Math.max(1, Math.round(image.width * ratio));
                    canvas.height = Math.max(1, Math.round(image.height * ratio));
                    const context = canvas.getContext('2d');
                    // Прозрачный PNG при сохранении в JPEG иначе станет чёрным.
                    context.fillStyle = '#fff';
                    context.fillRect(0, 0, canvas.width, canvas.height);
                    context.drawImage(image, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(
                        blob => blob ? resolve(blob) : reject(new Error('Не удалось сжать фото.')),
                        'image/jpeg', 0.82
                    );
                };
                image.onerror = () => reject(new Error('Не удалось прочитать фото.'));
                image.src = URL.createObjectURL(file);
            });
        },
        async sendImage(event) {
            const input = event.target;
            const file = input.files?.[0];
            input.value = '';
            if (!file || !this.connected || this.uploading) return;
            this.error = '';
            this.uploading = true;
            this.status = 'Готовим фото…';
            try {
                this.ensureUploadUrl();
                const blob = await this.compressImage(file, 1600);
                const form = new FormData();
                form.append('image', blob, 'photo.jpg');
                form.append('client_id', this.newClientId());
                this.status = 'Отправляем фото…';
                const response = await fetch(this.uploadUrl, {
                    method: 'POST', credentials: 'same-origin',
                    headers: { 'X-CSRFToken': this.csrfToken() },
                    body: form,
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.error || `Не удалось отправить фото (код ${response.status}).`);
                }
                if (data.message) this.addMessage(data.message);
                this.status = '';
            } catch (error) {
                this.error = error.message;
                this.status = '';
            } finally {
                this.uploading = false;
            }
        },
        formatTime(value) {
            return new Date(value).toLocaleTimeString('ru-RU', {
                hour: '2-digit', minute: '2-digit',
            });
        },
    }));

    // Виджет оператора: живой список диалогов + переписка внутри плавающей панели.
    Alpine.data('operatorInbox', () => ({
        open: false, online: false, selected: null, conversations: [],
        socket: null, retryTimer: null, retries: 0, baseTitle: document.title, audioCtx: null,
        init() {
            this.connect();
            this.$watch('awaiting', (n) => {
                document.title = n ? `(${n}) ${this.baseTitle}` : this.baseTitle;
            });
        },
        destroy() {
            clearTimeout(this.retryTimer);
            const socket = this.socket;
            this.socket = null;
            socket?.close();
        },
        // Диалоги, где последнее сообщение от гостя, т.е. ждут ответа.
        get awaiting() {
            return this.conversations.filter(c => !c.last_is_staff).length;
        },
        // Ожидающие ответа диалоги, кроме того, который открыт сейчас.
        get awaitingOthers() {
            return this.conversations.filter(c => !c.last_is_staff && c.id !== this.selected).length;
        },
        connect() {
            const socket = new WebSocket(
                `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/chat/operator/`
            );
            this.socket = socket;
            socket.onopen = () => { this.online = true; this.retries = 0; };
            socket.onmessage = (event) => {
                if (this.socket !== socket) return;
                let data;
                try { data = JSON.parse(event.data); } catch { return; }
                if (data.type === 'inbox') {
                    this.conversations = data.conversations;
                    this.sortList();
                } else if (data.type === 'update') {
                    this.applyUpdate(data.conversation);
                }
            };
            socket.onclose = (event) => {
                if (this.socket !== socket) return;
                this.socket = null;
                this.online = false;
                if (event.code === 4403) return;
                const delay = Math.min(1000 * 2 ** this.retries++, 30000);
                this.retryTimer = setTimeout(() => this.connect(), delay);
            };
        },
        applyUpdate(item) {
            const watching = this.open && this.selected === item.id && !document.hidden;
            if (!item.last_is_staff && !watching) this.beep();
            this.conversations = this.conversations.filter(c => c.id !== item.id);
            this.conversations.push(item);
            this.sortList();
        },
        sortList() {
            this.conversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        },
        beep() {
            try {
                this.audioCtx = this.audioCtx || new (window.AudioContext || window.webkitAudioContext)();
                const osc = this.audioCtx.createOscillator();
                const gain = this.audioCtx.createGain();
                gain.gain.value = 0.05;
                osc.frequency.value = 880;
                osc.connect(gain);
                gain.connect(this.audioCtx.destination);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.15);
            } catch { /* звук необязателен */ }
        },
        formatTime(value) {
            return new Date(value).toLocaleTimeString('ru-RU', {
                hour: '2-digit', minute: '2-digit',
            });
        },
    }));
});
