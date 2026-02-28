const API_BASE = "http://127.0.0.1:8000/api";

function toast(message, type = "success") {
    const cont = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<i class="fas fa-info-circle"></i><div>${message}</div>`;
    cont.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

// Safe DOM helpers
function el(id) { return document.getElementById(id); }
function setText(id, value) {
    const e = el(id);
    if (!e) return;
    e.textContent = (value === null || value === undefined) ? '' : String(value);
}
function setTextBySelector(selector, value) {
    const e = document.querySelector(selector);
    if (!e) return;
    e.textContent = (value === null || value === undefined) ? '' : String(value);
}
function safeShow(elId) {
    document.querySelectorAll('.container').forEach(c => c.classList.add('hidden'));
    const e = el(elId);
    if (e) e.classList.remove('hidden');
}

function show(elId) { safeShow(elId); }

// create a simple debug panel on the page
function ensureDebugPanel() {
    if (document.getElementById('debugPanel')) return;
    const p = document.createElement('div');
    p.id = 'debugPanel';
    p.style.position = 'fixed';
    p.style.left = '10px';
    p.style.bottom = '10px';
    p.style.maxWidth = '420px';
    p.style.maxHeight = '180px';
    p.style.overflow = 'auto';
    p.style.background = 'rgba(0,0,0,0.6)';
    p.style.color = 'white';
    p.style.fontSize = '12px';
    p.style.padding = '8px';
    p.style.borderRadius = '8px';
    p.style.zIndex = 9999;
    p.innerHTML = '<strong>Debug</strong><div id="debugLog"></div>';
    document.body.appendChild(p);
}

function debug(msg) {
    try { ensureDebugPanel(); } catch (e) { }
    const log = document.getElementById('debugLog');
    if (!log) return;
    const entry = document.createElement('div');
    entry.textContent = `${new Date().toLocaleTimeString()} - ${msg}`;
    log.prepend(entry);
}

// initialize debug panel and capture global errors
try {
    ensureDebugPanel();
    debug('script initialized');
    window.addEventListener('error', (ev) => {
        debug(`ERROR: ${ev.message} at ${ev.filename}:${ev.lineno}`);
    });
    window.addEventListener('unhandledrejection', (ev) => {
        debug(`PromiseRejection: ${ev.reason}`);
    });
} catch (e) {
    console.error('Failed to init debug panel', e);
}

async function studentLogin() {
    const name = document.getElementById('name').value.trim();
    const matric = document.getElementById('matric').value.trim();

    if (!name || !matric) {
        setTextBySelector('#studentError span', 'Enter name and matric');
        const se = el('studentError'); if (se) se.classList.remove('hidden');
        return;
    }

    // Try find user by name; if not exists, create as Student
    try {
        const users = await fetch(`${API_BASE}/users`).then(r => r.json());
        let user = users.find(u => u.name.toLowerCase() === name.toLowerCase());
        if (!user) {
            const res = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, role: 'Student' })
            });
            if (!res.ok) throw new Error(await res.text());
            user = await res.json();
            toast('Student account created', 'success');
        }

        // Save to session
        sessionStorage.setItem('currentUser', JSON.stringify(user));
        setText('studentName', user.name);
        setText('studentMatric', matric);
        show('studentPanel');
        pollStudentStatus();
    } catch (e) {
        console.error(e);
        toast('Login failed', 'error');
    }
}

function showAdminLogin() { show('adminLoginPage'); }
function showStudentLogin() { show('loginPage'); }

function logout() {
    sessionStorage.removeItem('currentUser');
    show('loginPage');
}

async function sendRequest() {
    const user = JSON.parse(sessionStorage.getItem('currentUser') || 'null');
    if (!user) return toast('No student logged in', 'warning');
    const reason = document.getElementById('reason').value.trim();
    if (reason.length < 10) return toast('Please provide at least 10 characters', 'warning');

    // enforce max 1000 words (trim is also applied on input)
    const WORD_LIMIT = 1000;
    const words = countWords(reason);
    if (words > WORD_LIMIT) {
        return toast(`Please reduce your request to ${WORD_LIMIT} words or less.`, 'warning');
    }

    try {
        const res = await fetch(`${API_BASE}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender_id: user.id, title: 'Exit Request', body: reason })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        toast('Request sent', 'success');
        document.getElementById('reason').value = '';
        // update word counter
        setText('wordCount', '0');
        setTimeout(() => pollStudentStatus(), 500);
    } catch (e) {
        console.error(e);
        toast('Failed to send request', 'error');
    }
}

async function pollStudentStatus() {
    const user = JSON.parse(sessionStorage.getItem('currentUser') || 'null');
    if (!user) return;
    try {
        const letters = await fetch(`${API_BASE}/letters`).then(r => r.json());
        const mine = letters.filter(l => l.sender_id === user.id).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        if (!mine.length) {
            setText('status', 'No request yet');
            const rd = el('requestDetails'); if (rd) rd.classList.add('hidden');
            return;
        }
        const latest = mine[0];
        setText('status', latest.status || 'pending');
        setText('requestReasonText', latest.body || '');
        setText('requestTimeText', latest.created_at || '');
        const rd2 = el('requestDetails'); if (rd2) rd2.classList.remove('hidden');
    } catch (e) {
        console.error(e);
    }
}

function adminLogin() {
    const pass = document.getElementById('adminPass').value;
    if (pass === 'admin123') {
        show('adminPanel');
        loadAdminOverview();
    } else {
        setTextBySelector('#adminError span', 'Wrong password');
        const ae = el('adminError'); if (ae) ae.classList.remove('hidden');
    }
}

async function loadAdminOverview() {
    // load pending count and recent activity
    try {
        const letters = await fetch(`${API_BASE}/letters`).then(r => r.json());
        const pendingCount = letters.filter(l => l.status === 'pending').length;
        setText('pendingBadge', pendingCount);
        const log = el('requestLog');
        if (log) log.innerHTML = '';
        letters.slice(0, 10).forEach(l => {
            const el = document.createElement('div');
            el.className = 'log-entry';
            el.innerHTML = `<i class="fas fa-envelope"></i><div><strong>${l.title}</strong> — ${l.sender_name} — ${l.status}</div>`;
            log.appendChild(el);
        });
    } catch (e) { console.error(e); }
}

async function switchAdminTab(tab) {
    document.querySelectorAll('#adminPanel .tab-content').forEach(t => t.classList.add('hidden'));
    document.getElementById(tab + 'Tab').classList.remove('hidden');
    if (tab === 'requests') loadPendingRequest();
    if (tab === 'students') loadStudents();
}

async function loadPendingRequest() {
    try {
        // fetch all letters and pick the first pending
        const letters = await fetch(`${API_BASE}/letters`).then(r => r.json());
        const pending = letters.find(l => l.status === 'pending');
        if (!pending) {
            const np = el('noPendingRequest'); if (np) np.classList.remove('hidden');
            const pr = el('pendingRequest'); if (pr) pr.classList.add('hidden');
            return;
        }
        const np2 = el('noPendingRequest'); if (np2) np2.classList.add('hidden');
        const pr2 = el('pendingRequest'); if (pr2) pr2.classList.remove('hidden');
        setText('requestStudent', pending.sender_name);
        setText('requestMatric', pending.sender_id);
        setText('requestReason', pending.body);
        setText('requestTime', pending.created_at);
        // store current pending id
        sessionStorage.setItem('currentPending', pending.letter_id || pending.id || pending.letter_id);
    } catch (e) { console.error(e); }
}

async function acceptRequest() { await adminAct('approve'); }
async function declineRequest() { await adminAct('reject'); }

// add a standalone comment without changing approval status
async function addComment() {
    const comment = document.getElementById('adminComment').value.trim();
    const rec = document.getElementById('adminRecommendation').value.trim();
    if (!comment && !rec) return toast('Enter comment or recommendation', 'warning');
    await adminAct('comment', comment, rec);
    // clear fields
    document.getElementById('adminComment').value = '';
    document.getElementById('adminRecommendation').value = '';
}

async function adminAct(action, comments = '', recommendations = '') {
    const id = sessionStorage.getItem('currentPending');
    if (!id) return toast('No pending selected', 'warning');
    // ask which role to act as
    const role = prompt('Act as which role?', 'SRC') || 'SRC';
    // if the user is trying to approve/reject but has entered comments/recs,
    // and the action role may not match, treat as a comment instead.
    if ((action === 'approve' || action === 'reject') && (comments || recommendations)) {
        action = 'comment';
        toast('Role mismatch detected; sending as comment only', 'info');
    }
    try {
        const res = await fetch(`${API_BASE}/act`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ letter_id: Number(id), actor_name: 'Admin', actor_role: role, action, comments, recommendations })
        });
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(txt);
        }
        toast('Action submitted', 'success');
        loadAdminOverview();
        loadPendingRequest();
    } catch (e) { console.error(e); toast('Action failed: ' + e.message, 'error'); }
}

async function adminAct(action) {
    const id = sessionStorage.getItem('currentPending');
    if (!id) return toast('No pending selected', 'warning');
    // ask which role to act as
    const role = prompt('Act as which role?', 'SRC') || 'SRC';
    try {
        const res = await fetch(`${API_BASE}/act`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ letter_id: Number(id), actor_name: 'Admin', actor_role: role, action })
        });
        if (!res.ok) throw new Error(await res.text());
        toast('Action submitted', 'success');
        loadAdminOverview();
        loadPendingRequest();
    } catch (e) { console.error(e); toast('Action failed', 'error'); }
}

// Wire some live behaviors
// Word counter helper
function countWords(text) {
    if (!text) return 0;
    return text.trim().split(/\s+/).filter(Boolean).length;
}

document.getElementById('reason')?.addEventListener('input', (e) => {
    const TEXT_WORD_LIMIT = 1000;
    let val = e.target.value || '';
    let words = countWords(val);
    // If over limit, trim the textarea to the first TEXT_WORD_LIMIT words
    if (words > TEXT_WORD_LIMIT) {
        const parts = val.trim().split(/\s+/).slice(0, TEXT_WORD_LIMIT);
        val = parts.join(' ');
        e.target.value = val;
        words = parts.length;
    }
    const wc = el('wordCount');
    if (wc) {
        wc.textContent = words;
        wc.style.color = (words > TEXT_WORD_LIMIT) ? '#ef4444' : '';
    }
});

// initial view
show('loginPage');

// --- Students management ---
async function loadStudents() {
    debug('loadStudents: starting...');
    try {
        debug('loadStudents: fetching /api/users...');
        const users = await fetch(`${API_BASE}/users`).then(r => r.json());
        debug(`loadStudents: got ${users.length ? users.length : 0} users`);
        const students = users.filter(u => u.role && u.role.toLowerCase() === 'student');
        debug(`loadStudents: filtered to ${students.length} students`);
        setText('studentCount', students.length);
        const container = el('studentListContainer');
        if (container) container.innerHTML = '';
        students.forEach(s => {
            const row = document.createElement('div');
            row.className = 'student-item';
            row.innerHTML = `
                <div>${s.name}</div>
                <div>${s.id}</div>
                <div class="student-actions">
                    <button class="reset-btn" onclick="resetPassword(${s.id})">Reset</button>
                    <button class="delete-btn" onclick="deleteStudent(${s.id})">Delete</button>
                </div>
            `;
            container.appendChild(row);
        });
        debug('loadStudents: complete');
    } catch (e) {
        console.error('Failed loading students', e);
        debug(`loadStudents: exception: ${e.message}`);
    }
}

async function addStudent() {
    const name = document.getElementById('newStudentName').value.trim();
    const matric = document.getElementById('newStudentMatric').value.trim();
    if (!name) return toast('Enter student name', 'warning');
    debug(`addStudent: name="${name}"`);
    try {
        debug('addStudent: sending POST...');
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, role: 'Student' })
        });
        debug(`addStudent: response status=${res.status}`);
        const text = await res.text();
        debug(`addStudent: response text length=${text.length}`);
        let created = null;
        try { created = JSON.parse(text); } catch (_) { /* not JSON */ }
        if (!res.ok) {
            console.error('Add student failed', res.status, text);
            debug(`addStudent: FAILED ${res.status}`);
            toast(`Add failed: ${res.status}`, 'error');
            return;
        }
        debug(`addStudent: SUCCESS, calling loadStudents()`);
        console.log('Add student response', res.status, created || text);
        toast('Student added', 'success');
        document.getElementById('newStudentName').value = '';
        document.getElementById('newStudentMatric').value = '';
        debug('addStudent: before loadStudents');
        await loadStudents();
        debug('addStudent: after loadStudents');
    } catch (e) {
        debug(`addStudent: exception: ${e.message}`);
        console.error(e);
        toast('Failed to add student', 'error');
    }
}

// basic stubs for student actions
async function resetPassword(id) {
    debug(`resetPassword: id=${id}`);
    const confirmed = confirm(`Reset password for student ID ${id}?`);
    if (!confirmed) return;
    try {
        debug('resetPassword: PUT request...');
        const res = await fetch(`${API_BASE}/users/${id}/password`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' }
        });
        debug(`resetPassword: status=${res.status}`);
        const data = await res.json();
        if (!res.ok) {
            toast(`Reset failed: ${res.status}`, 'error');
            return;
        }
        toast(`Password reset to: ${data.default_password}`, 'success');
        loadStudents();
    } catch (e) {
        debug(`resetPassword: exception: ${e.message}`);
        toast('Reset failed', 'error');
    }
}

async function deleteStudent(id) {
    debug(`deleteStudent: id=${id}`);
    const confirmed = confirm(`Delete student ID ${id}? This cannot be undone.`);
    if (!confirmed) return;
    try {
        debug('deleteStudent: DELETE request...');
        const res = await fetch(`${API_BASE}/users/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        debug(`deleteStudent: status=${res.status}`);
        if (!res.ok) {
            const err = await res.json();
            toast(`Delete failed: ${err.detail}`, 'error');
            return;
        }
        toast('Student deleted', 'success');
        loadStudents();
    } catch (e) {
        debug(`deleteStudent: exception: ${e.message}`);
        toast('Delete failed', 'error');
    }
}

// load students when opening students tab
document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
    // if students tab selected, refresh list
    if (btn.textContent && btn.textContent.includes('Students')) setTimeout(loadStudents, 200);
}));
