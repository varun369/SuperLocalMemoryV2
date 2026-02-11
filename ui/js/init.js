// SuperLocalMemory V2 - Event Listener Wiring
// Loads LAST — after all module scripts. Connects UI events to module functions.

document.getElementById('memories-tab').addEventListener('shown.bs.tab', loadMemories);
document.getElementById('clusters-tab').addEventListener('shown.bs.tab', loadClusters);
document.getElementById('patterns-tab').addEventListener('shown.bs.tab', loadPatterns);
document.getElementById('timeline-tab').addEventListener('shown.bs.tab', loadTimeline);
document.getElementById('settings-tab').addEventListener('shown.bs.tab', loadSettings);
document.getElementById('search-query').addEventListener('keypress', function(e) { if (e.key === 'Enter') searchMemories(); });

document.getElementById('profile-select').addEventListener('change', function() {
    switchProfile(this.value);
});

document.getElementById('add-profile-btn').addEventListener('click', function() {
    createProfile();
});

var newProfileInput = document.getElementById('new-profile-name');
if (newProfileInput) {
    newProfileInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') createProfile();
    });
}

// v2.5 tabs (graceful — elements may not exist on older installs)
var eventsTab = document.getElementById('events-tab');
if (eventsTab) eventsTab.addEventListener('shown.bs.tab', loadEventStats);

var agentsTab = document.getElementById('agents-tab');
if (agentsTab) agentsTab.addEventListener('shown.bs.tab', loadAgents);
