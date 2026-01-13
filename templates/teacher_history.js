
/**
 * SHARED DATA KEY
 * Using a single constant ensures login, logout, and dashboard always stay in sync.
 */
const STORAGE_KEY = 'labHistory';

// --- STUDENT LOGIN (login.html) ---
function handleLogin() {
    const sId = document.getElementById('studentId').value;
    const sSect = document.getElementById('studentSection').value;
    const pcNum = document.getElementById('pcNumber').value;
    const tName = document.getElementById('teacherName').value;

    if (!sId || !pcNum) {
        alert("Student ID and PC Number are required!");
        return;
    }

    const newRecord = {
        id: sId,
        section: sSect,
        pc: pcNum,
        teacher: tName,
        timeIn: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        timeOut: "-",
        timestamp: new Date().getTime(), // Used for sorting and math
        status: "Active"
    };

    let history = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    history.push(newRecord);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));

    window.location.href = 'home.html';
}

// --- STUDENT LOGOUT (logout.html) ---
function handleLogout() {
    const logoutId = document.getElementById('logout-id').value;
    let history = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    
    let found = false;
    history = history.map(record => {
        if (record.id === logoutId && record.status === "Active") {
            found = true;
            return { 
                ...record, 
                timeOut: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), 
                status: "Completed" 
            };
        }
        return record;
    });

    if (!found) {
        alert("No active session found for this ID.");
        return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    window.location.href = 'end_credit.html';
}

// --- TEACHER DASHBOARD (teacher_history.html) ---
document.addEventListener('DOMContentLoaded', () => {
    // Only run if elements exist on the current page
    if (document.getElementById('history-table-body')) {
        syncDashboardData();
    }
});

function syncDashboardData() {
    const history = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    const tableBody = document.getElementById('history-table-body');
    const onlineCountDisplay = document.getElementById('online-count');
    const visitCountDisplay = document.getElementById('visit-count');

    if (!tableBody) return;

    // Reset Table
    tableBody.innerHTML = '';

    // Update Stats
    visitCountDisplay.innerText = history.length;
    const activeSessions = history.filter(item => item.status === "Active");
    onlineCountDisplay.innerText = activeSessions.length;

    if (history.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; opacity: 0.5; padding: 50px;">No records found.</td></tr>`;
        return;
    }

    // Sort: Newest entries (highest timestamp) first
    const sortedHistory = [...history].sort((a, b) => b.timestamp - a.timestamp);

    sortedHistory.forEach(item => {
        const statusClass = item.status === 'Active' ? 'success' : 'warning';
        
        const row = `
            <tr>
                <td>${item.id}</td>
                <td>${item.section || '---'}</td>
                <td>PC-${item.pc}</td>
                <td>${item.timeIn} ${item.timeOut !== '-' ? '➞ ' + item.timeOut : ''}</td>
                <td><span class="badge ${statusClass}">${item.status}</span></td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

function resetLabData() {
    if(confirm("DANGER: This will delete ALL history and stats. Continue?")) {
        localStorage.removeItem(STORAGE_KEY);
        syncDashboardData();
    }
}
