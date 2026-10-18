// API Configuration
// Use relative URL to work with any hostname
const API_BASE_URL = '/api';

// DOM Elements
const contactForm = document.getElementById('contactForm');
const contactsBody = document.getElementById('contactsBody');
const contactsTable = document.getElementById('contactsTable');
const contactsCards = document.getElementById('contactsCards');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const emptyState = document.getElementById('emptyState');
const noResults = document.getElementById('noResults');
const formTitle = document.getElementById('form-title');
const submitBtn = document.getElementById('submitBtn');
const cancelBtn = document.getElementById('cancelBtn');
const contactIdInput = document.getElementById('contactId');
const searchBox = document.getElementById('searchBox');
const searchInput = document.getElementById('searchInput');
const searchCount = document.getElementById('searchCount');
const importForm = document.getElementById('importForm');
const csvFile = document.getElementById('csvFile');
const duplicateStrategy = document.getElementById('duplicateStrategy');
const importBtn = document.getElementById('importBtn');
const importResult = document.getElementById('importResult');
const importSummary = document.getElementById('importSummary');
const importErrorsContainer = document.getElementById('importErrorsContainer');
const importErrorsBody = document.getElementById('importErrorsBody');

// State
let editingContactId = null;
let allContacts = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadContacts();
    contactForm.addEventListener('submit', handleSubmit);
    cancelBtn.addEventListener('click', resetForm);
    searchInput.addEventListener('input', handleSearch);
    importForm.addEventListener('submit', handleImport);
});

// Load all contacts
async function loadContacts() {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/contacts`);

        if (!response.ok) {
            throw new Error('Kontakte konnten nicht geladen werden');
        }

        const contacts = await response.json();
        allContacts = contacts;
        displayContacts(contacts);
        hideLoading();

        // Show search box if there are contacts
        if (contacts.length > 0) {
            searchBox.style.display = 'block';
        } else {
            searchBox.style.display = 'none';
        }
    } catch (err) {
        showError('Fehler beim Laden der Kontakte: ' + err.message);
        hideLoading();
    }
}

// Import contacts from a CSV file
async function handleImport(e) {
    e.preventDefault();

    if (!csvFile.files.length) {
        showError('Bitte wählen Sie eine CSV-Datei aus.');
        return;
    }

    const formData = new FormData();
    formData.append('file', csvFile.files[0]);
    importBtn.disabled = true;
    importBtn.textContent = 'Wird importiert...';
    importResult.hidden = true;

    try {
        const strategy = encodeURIComponent(duplicateStrategy.value);
        const response = await fetch(`${API_BASE_URL}/contacts/import?duplicate_strategy=${strategy}`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'CSV-Datei konnte nicht importiert werden');
        }

        displayImportResult(result);
        importForm.reset();
        await loadContacts();
    } catch (err) {
        showError('Fehler beim CSV-Import: ' + err.message);
    } finally {
        importBtn.disabled = false;
        importBtn.textContent = 'Kontakte importieren';
    }
}

function displayImportResult(result) {
    importResult.hidden = false;
    importSummary.textContent = [
        `${result.total_rows} Zeilen verarbeitet`,
        `${result.created} neu`,
        `${result.updated} aktualisiert`,
        `${result.skipped} übersprungen`,
        `${result.error_count} fehlerhaft`
    ].join(' · ');

    importErrorsBody.innerHTML = '';
    if (!result.errors.length) {
        importErrorsContainer.hidden = true;
        importResult.classList.remove('has-errors');
        return;
    }

    result.errors.forEach(rowError => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(String(rowError.row))}</td>
            <td>${escapeHtml(rowError.name || '–')}</td>
            <td>${escapeHtml(rowError.message)}</td>
        `;
        importErrorsBody.appendChild(row);
    });
    importErrorsContainer.hidden = false;
    importResult.classList.add('has-errors');
}

// Display contacts in table and cards
function displayContacts(contacts) {
    contactsBody.innerHTML = '';
    contactsCards.innerHTML = '';

    if (allContacts.length === 0) {
        contactsTable.style.display = 'none';
        contactsCards.style.display = 'none';
        emptyState.style.display = 'block';
        noResults.style.display = 'none';
        return;
    }

    if (contacts.length === 0) {
        // No results from search
        contactsTable.style.display = 'none';
        contactsCards.style.display = 'none';
        emptyState.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }

    contactsTable.style.display = 'table';
    contactsCards.style.display = 'block';
    emptyState.style.display = 'none';
    noResults.style.display = 'none';

    // Render desktop table view
    contacts.forEach(contact => {
        const row = document.createElement('tr');
        row.dataset.contactId = contact.id;
        row.innerHTML = `
            <td>${escapeHtml(contact.name)}</td>
            <td>${escapeHtml(contact.phone1 || '-')}</td>
            <td>${escapeHtml(contact.phone2 || '-')}</td>
            <td>${escapeHtml(contact.phone3 || '-')}</td>
            <td>
                <button class="btn btn-edit" onclick="editContact(${contact.id})">Bearbeiten</button>
                <button class="btn btn-delete" onclick="deleteContact(${contact.id})">Löschen</button>
            </td>
        `;
        contactsBody.appendChild(row);
    });

    // Render mobile card view
    contacts.forEach(contact => {
        const card = document.createElement('div');
        card.className = 'contact-card';
        card.dataset.contactId = contact.id;

        const phones = [];
        if (contact.phone1) phones.push({ label: 'Telefon 1', number: contact.phone1 });
        if (contact.phone2) phones.push({ label: 'Telefon 2', number: contact.phone2 });
        if (contact.phone3) phones.push({ label: 'Telefon 3', number: contact.phone3 });

        const phonesHtml = phones.length > 0
            ? phones.map(p => `
                <div class="contact-card-phone">
                    <span class="contact-card-phone-label">${p.label}:</span>
                    <span class="contact-card-phone-number">${escapeHtml(p.number)}</span>
                </div>
            `).join('')
            : '<div class="contact-card-phone"><span style="color: #95a5a6;">Keine Telefonnummern</span></div>';

        card.innerHTML = `
            <div class="contact-card-header">
                <div class="contact-card-name">${escapeHtml(contact.name)}</div>
            </div>
            <div class="contact-card-phones">
                ${phonesHtml}
            </div>
            <div class="contact-card-actions">
                <button class="btn btn-edit" onclick="editContact(${contact.id})">Bearbeiten</button>
                <button class="btn btn-delete" onclick="deleteContact(${contact.id})">Löschen</button>
            </div>
        `;
        contactsCards.appendChild(card);
    });

    updateSearchCount(contacts.length);
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('name').value,
        phone1: document.getElementById('phone1').value || null,
        phone2: document.getElementById('phone2').value || null,
        phone3: document.getElementById('phone3').value || null
    };

    try {
        let response;
        if (editingContactId) {
            // Update existing contact
            response = await fetch(`${API_BASE_URL}/contacts/${editingContactId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
        } else {
            // Create new contact
            response = await fetch(`${API_BASE_URL}/contacts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
        }

        if (!response.ok) {
            throw new Error('Kontakt konnte nicht gespeichert werden');
        }

        resetForm();
        loadContacts();
    } catch (err) {
        showError('Fehler beim Speichern des Kontakts: ' + err.message);
    }
}

// Edit contact
async function editContact(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/contacts/${id}`);

        if (!response.ok) {
            throw new Error('Kontakt konnte nicht geladen werden');
        }

        const contact = await response.json();

        // Populate form
        document.getElementById('name').value = contact.name;
        document.getElementById('phone1').value = contact.phone1 || '';
        document.getElementById('phone2').value = contact.phone2 || '';
        document.getElementById('phone3').value = contact.phone3 || '';

        // Update UI state
        editingContactId = id;
        formTitle.textContent = 'Kontakt bearbeiten';
        submitBtn.textContent = 'Kontakt aktualisieren';
        cancelBtn.style.display = 'inline-block';

        // Scroll to form
        contactForm.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        showError('Fehler beim Laden des Kontakts zum Bearbeiten: ' + err.message);
    }
}

// Delete contact
async function deleteContact(id) {
    if (!confirm('Möchten Sie diesen Kontakt wirklich löschen?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/contacts/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Kontakt konnte nicht gelöscht werden');
        }

        loadContacts();
    } catch (err) {
        showError('Fehler beim Löschen des Kontakts: ' + err.message);
    }
}

// Reset form to initial state
function resetForm() {
    contactForm.reset();
    editingContactId = null;
    formTitle.textContent = 'Neuen Kontakt hinzufügen';
    submitBtn.textContent = 'Kontakt hinzufügen';
    cancelBtn.style.display = 'none';
}

// UI helper functions
function showLoading() {
    loading.style.display = 'block';
    error.style.display = 'none';
}

function hideLoading() {
    loading.style.display = 'none';
}

function showError(message) {
    error.textContent = message;
    error.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Search functionality
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase().trim();

    if (!searchTerm) {
        // Show all contacts if search is empty
        displayContacts(allContacts);
        return;
    }

    // Filter contacts based on search term
    const filteredContacts = allContacts.filter(contact => {
        const name = (contact.name || '').toLowerCase();
        const phone1 = (contact.phone1 || '').toLowerCase();
        const phone2 = (contact.phone2 || '').toLowerCase();
        const phone3 = (contact.phone3 || '').toLowerCase();

        return name.includes(searchTerm) ||
               phone1.includes(searchTerm) ||
               phone2.includes(searchTerm) ||
               phone3.includes(searchTerm);
    });

    displayContacts(filteredContacts);
}

// Update search count display
function updateSearchCount(count) {
    if (!searchInput.value.trim()) {
        searchCount.textContent = '';
        return;
    }

    const total = allContacts.length;
    if (count === total) {
        searchCount.textContent = '';
    } else {
        searchCount.textContent = `${count} von ${total}`;
    }
}
