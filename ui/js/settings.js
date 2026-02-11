// SuperLocalMemory V2 - Settings & Backup
// Depends on: core.js, profiles.js (loadProfilesTable)

async function loadSettings() {
    loadProfilesTable();
    loadBackupStatus();
    loadBackupList();
}

async function loadBackupStatus() {
    try {
        var response = await fetch('/api/backup/status');
        var data = await response.json();
        renderBackupStatus(data);
        document.getElementById('backup-interval').value = data.interval_hours <= 24 ? '24' : '168';
        document.getElementById('backup-max').value = data.max_backups || 10;
        document.getElementById('backup-enabled').checked = data.enabled !== false;
    } catch (error) {
        var container = document.getElementById('backup-status');
        var alert = document.createElement('div');
        alert.className = 'alert alert-warning mb-0';
        alert.textContent = 'Auto-backup not available. Update to v2.4.0+.';
        container.textContent = '';
        container.appendChild(alert);
    }
}

function renderBackupStatus(data) {
    var container = document.getElementById('backup-status');
    container.textContent = '';

    var lastBackup = data.last_backup ? formatDateFull(data.last_backup) : 'Never';
    var nextBackup = data.next_backup || 'N/A';
    if (nextBackup === 'overdue') nextBackup = 'Overdue';
    else if (nextBackup !== 'N/A' && nextBackup !== 'unknown') nextBackup = formatDateFull(nextBackup);

    var statusColor = data.enabled ? 'text-success' : 'text-secondary';
    var statusText = data.enabled ? 'Active' : 'Disabled';

    var row = document.createElement('div');
    row.className = 'row g-2 mb-2';

    var stats = [
        { value: statusText, label: 'Status', cls: statusColor },
        { value: String(data.backup_count || 0), label: 'Backups', cls: '' },
        { value: (data.total_size_mb || 0) + ' MB', label: 'Storage', cls: '' }
    ];

    stats.forEach(function(s) {
        var col = document.createElement('div');
        col.className = 'col-4';
        var stat = document.createElement('div');
        stat.className = 'backup-stat';
        var val = document.createElement('div');
        val.className = 'value ' + s.cls;
        val.textContent = s.value;
        var lbl = document.createElement('div');
        lbl.className = 'label';
        lbl.textContent = s.label;
        stat.appendChild(val);
        stat.appendChild(lbl);
        col.appendChild(stat);
        row.appendChild(col);
    });
    container.appendChild(row);

    var details = [
        { label: 'Last backup:', value: lastBackup },
        { label: 'Next backup:', value: nextBackup },
        { label: 'Interval:', value: data.interval_display || '-' }
    ];
    details.forEach(function(d) {
        var div = document.createElement('div');
        div.className = 'small text-muted';
        var strong = document.createElement('strong');
        strong.textContent = d.label + ' ';
        div.appendChild(strong);
        div.appendChild(document.createTextNode(d.value));
        container.appendChild(div);
    });
}

async function saveBackupConfig() {
    try {
        var response = await fetch('/api/backup/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interval_hours: parseInt(document.getElementById('backup-interval').value),
                max_backups: parseInt(document.getElementById('backup-max').value),
                enabled: document.getElementById('backup-enabled').checked
            })
        });
        var data = await response.json();
        renderBackupStatus(data);
        showToast('Backup settings saved');
    } catch (error) {
        console.error('Error saving backup config:', error);
        showToast('Failed to save backup settings');
    }
}

async function createBackupNow() {
    showToast('Creating backup...');
    try {
        var response = await fetch('/api/backup/create', { method: 'POST' });
        var data = await response.json();
        if (data.success) {
            showToast('Backup created: ' + data.filename);
            loadBackupStatus();
            loadBackupList();
        } else {
            showToast('Backup failed');
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        showToast('Backup failed');
    }
}

async function loadBackupList() {
    try {
        var response = await fetch('/api/backup/list');
        var data = await response.json();
        renderBackupList(data.backups || []);
    } catch (error) {
        var container = document.getElementById('backup-list');
        container.textContent = 'Backup list unavailable';
    }
}

function renderBackupList(backups) {
    var container = document.getElementById('backup-list');
    if (!backups || backups.length === 0) {
        showEmpty('backup-list', 'archive', 'No backups yet. Create your first backup above.');
        return;
    }

    var table = document.createElement('table');
    table.className = 'table table-sm';
    var thead = document.createElement('thead');
    var headRow = document.createElement('tr');
    ['Filename', 'Size', 'Age', 'Created'].forEach(function(h) {
        var th = document.createElement('th');
        th.textContent = h;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    backups.forEach(function(b) {
        var row = document.createElement('tr');
        var age = b.age_hours < 48 ? Math.round(b.age_hours) + 'h ago' : Math.round(b.age_hours / 24) + 'd ago';
        var cells = [b.filename, b.size_mb + ' MB', age, formatDateFull(b.created)];
        cells.forEach(function(text) {
            var td = document.createElement('td');
            td.textContent = text;
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    container.textContent = '';
    container.appendChild(table);
}
