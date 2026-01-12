// --- Configuration and State ---
let inventoryData = []; // Full list of loaded inventory items
let filteredData = [];  // Data currently matching the search/filters
let currentPage = 1;
// itemsPerPage is now a string ('5', '10', '25', or 'all')
let itemsPerPage = '5';

// Contact Information
const CONTACT_INFO = {
    email: 'blankcguitars@gmail.com',
    messenger: 'http://m.me/blankcguitars',
    instagram: 'https://ig.me/m/blankc_guitars'
};

// --- DOM Elements (Must be selected *after* content is injected) ---
// Note: These need to be re-assigned or selected inside loadInventory() because 
// the gallery HTML is loaded dynamically. We'll use getElementById within loadInventory.

let galleryContainer, searchInput, itemsPerPageSelect, paginationControls, prevPageBtn, nextPageBtn, pageInfo, loadingIndicator, noResults;

// --- Initialization and Data Loading ---

/**
 * Loads inventory data from 'inventory_data.json' and initializes the gallery.
 * IMPORTANT: This function must be called *after* the gallery.html content is
 * injected into the main page to ensure all DOM elements are present.
 */
function loadInventory() {
    // Re-select DOM elements since the content is dynamically loaded
    galleryContainer = document.getElementById('galleryContainer');
    searchInput = document.getElementById('searchInput');
    itemsPerPageSelect = document.getElementById('itemsPerPageSelect');
    paginationControls = document.getElementById('paginationControls');
    prevPageBtn = document.getElementById('prevPageBtn');
    nextPageBtn = document.getElementById('nextPageBtn');
    pageInfo = document.getElementById('pageInfo');
    loadingIndicator = document.getElementById('loadingIndicator');
    noResults = document.getElementById('noResults');

    // Attach event listeners *only* if elements are found
    if (searchInput) searchInput.addEventListener('input', applyFiltersAndSearch);
    if (prevPageBtn) prevPageBtn.addEventListener('click', handlePrevPage);
    if (nextPageBtn) nextPageBtn.addEventListener('click', handleNextPage);
    if (itemsPerPageSelect) itemsPerPageSelect.addEventListener('change', handleItemsPerPageChange);


    if (loadingIndicator) loadingIndicator.classList.remove('hidden');

    // Fetch the JSON file from the same directory
    fetch('inventory_data.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load inventory_data.json. Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // CRUCIAL: Reverse the data immediately to establish the default "Reverse Loading Order"
            data.reverse();

            // Cleanup and type conversion
            data.forEach(item => {
                // Ensure price is a number
                item.price = parseFloat(item.price) || 0;
            });

            // --- START MODIFIED LOGIC: FETCH IMAGE FILES ---
            // Create an array of promises for fetching all image JSON files concurrently
            const imageFetchPromises = data.map(item => {
                // MODIFIED: Check if the item has the new imageFileJson property defined
                if (item.imageFileJson) {
                    // MODIFIED: Construct the path to the JSON file inside the 'guitars/' directory
                    const imageJsonPath = `guitars/${item.imageFileJson}`;

                    return fetch(imageJsonPath)
                        .then(response => {
                            if (!response.ok) {
                                // MODIFIED: Use the new path variable in the error log
                                console.error(`Failed to load image JSON: ${imageJsonPath}. Status: ${response.status}`);
                                return []; // Return an empty array on error
                            }
                            return response.json();
                        })
                        .then(base64ImageArray => {
                            // Assign the fetched base64 data to the 'imageFiles' property
                            item.imageFiles = base64ImageArray;
                            return item; // Resolve the promise with the updated item
                        })
                        .catch(error => {
                            // MODIFIED: Use the new path variable in the error log
                            console.error(`Error processing image data for ${imageJsonPath}:`, error);
                            item.imageFiles = [];
                            return item;
                        });
                } else {
                    item.imageFiles = []; // No image path, default to empty array
                    return Promise.resolve(item);
                }
            });

            // Wait for all image data fetches to complete
            return Promise.all(imageFetchPromises);
            // --- END MODIFIED LOGIC ---
        })
        .then(mergedData => {
            inventoryData = mergedData; // Store the fully populated data

            // Set initial items per page from dropdown
            itemsPerPage = itemsPerPageSelect ? itemsPerPageSelect.value : '5'; // Store as string '5'

            // Apply default state (which is the reversed and image-loaded data)
            applyFiltersAndSearch();
        })
        .catch(error => {
            console.error("Error loading inventory or merging images:", error);
            if (loadingIndicator) {
                loadingIndicator.textContent = `Error loading inventory data: ${error.message}. Please ensure 'inventory_data.json' and all image JSON files are present.`;
                loadingIndicator.className = 'col-span-full text-center p-10 text-red-600 font-semibold';
            }
            // Disable controls if data loading fails
            if (paginationControls) paginationControls.classList.add('hidden');
            if (searchInput) searchInput.disabled = true;
            if (itemsPerPageSelect) itemsPerPageSelect.disabled = true;
        });
}

// --- Filtering Logic ---

/**
 * Applies the current search and triggers rendering.
 */
function applyFiltersAndSearch() {
    const searchTerm = searchInput.value.toLowerCase().trim();

    // 1. Filter the data based on search term
    filteredData = inventoryData.filter(item => {
        const searchFields = [
            item.serial,
            item.itemHeader,
            item.shortDescription,
            ...(item.keywords || []).join(', ')
        ].join(' ').toLowerCase();

        return searchFields.includes(searchTerm);
    });

    currentPage = 1; // Reset to first page after filter/search change
    renderGalleryPage();
}

// --- Rendering Logic ---

/**
 * Renders the current page of the filtered/sorted gallery.
 */
function renderGalleryPage() {
    if (loadingIndicator) loadingIndicator.classList.add('hidden');
    if (galleryContainer) galleryContainer.innerHTML = ''; // Clear existing cards

    if (filteredData.length === 0) {
        if (noResults) noResults.classList.remove('hidden');
        if (paginationControls) paginationControls.classList.add('hidden');
        return;
    }
    if (noResults) noResults.classList.add('hidden');

    const start = (currentPage - 1) * (itemsPerPage === 'all' ? 0 : parseInt(itemsPerPage));

    // If 'all' is selected, end is the full length of the filtered data
    const end = itemsPerPage === 'all' ? filteredData.length : (start + parseInt(itemsPerPage));

    const itemsToRender = filteredData.slice(start, end);

    itemsToRender.forEach(item => {
        const card = createItemCard(item);
        if (galleryContainer) galleryContainer.appendChild(card);
    });

    updatePaginationControls();
}

/**
 * Creates a single responsive item card element and attaches event listeners.
 * @param {object} item - The inventory item object.
 * @returns {HTMLElement} The created card element.
 */
function createItemCard(item) {
    const card = document.createElement('div');
    // NOTE: Added 'js-item-card' class and data-serial for easy listener selection
    card.className = 'bg-white shadow-xl overflow-hidden transform hover:scale-[1.02] transition duration-300 flex justify-evenlyborder border-gray-100 h-full flex flex-col js-item-card';
    card.setAttribute('data-serial', item.serial);

    // Use the first image from the array, or a NO IMAGE placeholder
    const imageUrl = item.imageFiles && item.imageFiles.length > 0
        ? item.imageFiles[0]
        : 'https://placehold.co/1200x800/f5f5f5/cccccc?text=NO+IMAGE';

    const statusClass = item.isSold ? 'bg-red-500' : 'bg-green-500';
    const statusText = item.isSold ? 'SOLD' : 'AVAILABLE';

    // Encode the email subject for the item inquiry
    const emailSubject = `Inquiry about item ${item.itemHeader} (S/N: ${item.serial})`;

    // Removed the complex inline onclick attribute.
    card.innerHTML = `
        <div class="relative h-48 cursor-pointer js-view-details-trigger">
            <img src="${imageUrl}" alt="${item.itemHeader}" 
                 class="w-full h-full object-cover" 
                 onerror="this.onerror=null; this.src='https://placehold.co/1200x800/f5f5f5/cccccc?text=NO+IMAGE';">
            <span class="absolute top-3 right-3 px-3 py-1 text-xs font-semibold text-white ${statusClass} shadow-md rounded-full">
                ${statusText}
            </span>
        </div>
        <div class="p-5 flex flex-col flex-grow">
            <div class="flex justify-center items-center gap-2">
                <h2 class="text-gray-900 truncate">${item.itemHeader}</h2>
                <p class="text-emerald-600">$${item.price.toFixed(2)}</p>
            </div>
            <p class="text-xs text-gray-700 line-clamp-2 my-3">${item.shortDescription}</p>
            <p class="text-xs text-gray-700 line-clamp-2 text-end mb-2">Serial No: ${item.serial}</p>
            <div class="flex flex-col space-y-3 mt-auto">
                <button class="w-full py-2 bg-blue-600 text-white font-medium hover:bg-blue-600 transition duration-150 mb-2 js-view-details-trigger" aria-label="View details for ${item.itemHeader} serial number ${item.serial}">
                    View Details
                </button>
                
                <label class="text-xs font-medium text-gray-500 text-center">Contact to Purchase <i class="fa fa-arrow-down"></i></label>
                <a class="flex-1 py-2 text-center text-xs font-medium bg-gray-100 text-gray-700 hover:bg-pink-500 hover:text-white transition duration-150" href="mailto:${CONTACT_INFO.email}?subject=${encodeURIComponent(emailSubject)}"><i class="fas fa-envelope me-2"></i>${CONTACT_INFO.email}</a>
                <div class="flex justify-between space-x-2">
                    <a href="${CONTACT_INFO.instagram}" target="_blank"
                       class="flex-1 py-2 text-center text-sm font-medium bg-gray-100 text-gray-700 hover:bg-pink-500 hover:text-white transition duration-150" 
                       title="Contact via Instagram">
                        <i class="fab fa-instagram"></i>
                    </a>
                    <a href="${CONTACT_INFO.messenger}" target="_blank"
                       class="flex-1 py-2 text-center text-sm font-medium bg-gray-100 text-gray-700 hover:bg-blue-500 hover:text-white transition duration-150" 
                       title="Contact via Messenger">
                        <i class="fab fa-facebook-messenger"></i>
                    </a>
                </div>
                
            </div>
        </div>
    `;

    // Step 2: Add the event listener to both elements with the 'js-view-details-trigger' class
    card.querySelectorAll('.js-view-details-trigger').forEach(trigger => {
        trigger.addEventListener('click', () => {
            // Find the item directly using the item object we already have in scope
            openModal(item);
        });
    });

    return card;
}


// --- Pagination Logic ---

/**
 * Updates the state and appearance of the pagination controls.
 */
function updatePaginationControls() {
    if (!paginationControls || !pageInfo || !prevPageBtn || !nextPageBtn) return;

    // If 'all' is selected, treat itemsPerPage as the total length, resulting in 1 page.
    const effectiveItemsPerPage = itemsPerPage === 'all' ? filteredData.length : parseInt(itemsPerPage);
    const totalPages = Math.ceil(filteredData.length / effectiveItemsPerPage);

    if (totalPages > 1) {
        paginationControls.classList.remove('hidden');
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage === totalPages;
    } else {
        // Hide controls if there's only one page (including when "All" is selected)
        paginationControls.classList.add('hidden');
    }
}

function handlePrevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderGalleryPage();
        window.scrollTo({ top: 0, behavior: 'smooth' }); // Scroll to top on page change
    }
}

function handleNextPage() {
    const effectiveItemsPerPage = itemsPerPage === 'all' ? filteredData.length : parseInt(itemsPerPage);
    const totalPages = Math.ceil(filteredData.length / effectiveItemsPerPage);

    if (currentPage < totalPages) {
        currentPage++;
        renderGalleryPage();
        window.scrollTo({ top: 0, behavior: 'smooth' }); // Scroll to top on page change
    }
}

function handleItemsPerPageChange(e) {
    itemsPerPage = e.target.value; // Store as string ('5', '10', '25', 'all')
    applyFiltersAndSearch();
}


// --- Modal Logic (Modal HTML is now in index.html) ---

/**
 * Generates the HTML for the contact links in the modal.
 * @param {object} item - The inventory item object.
 * @returns {string} HTML string for the contact section.
 */
function getModalContactHtml(item) {
    const emailSubject = `Inquiry about item ${item.itemHeader} (S/N: ${item.serial})`;

    return `
        <div class="mt-4 pt-4 border-t border-gray-200">
            <h3 class="text-xl font-semibold text-gray-800 mb-3">Contact to Purchase:</h3>
            <div class="flex justify-evenly">
                <a href="mailto:${CONTACT_INFO.email}?subject=${encodeURIComponent(emailSubject)}"
                   class="text-gray-700 hover:text-red-600 transition duration-150 flex flex-col items-center group" 
                   title="Email: ${CONTACT_INFO.email}">
                    <i class="fas fa-envelope text-3xl group-hover:scale-110"></i>
                    <span class="text-xs mt-1 text-gray-500 group-hover:text-red-600">Email</span>
                </a>
                <a href="${CONTACT_INFO.messenger}" target="_blank"
                   class="text-gray-700 hover:text-blue-600 transition duration-150 flex flex-col items-center group" 
                   title="Facebook Messenger">
                    <i class="fab fa-facebook-messenger text-3xl group-hover:scale-110"></i>
                    <span class="text-xs mt-1 text-gray-500 group-hover:text-blue-600">Messenger</span>
                </a>
                <a href="${CONTACT_INFO.instagram}" target="_blank"
                   class="text-gray-700 hover:text-pink-600 transition duration-150 flex flex-col items-center group" 
                   title="Instagram: @blankc_guitars">
                    <i class="fab fa-instagram text-3xl group-hover:scale-110"></i>
                    <span class="text-xs mt-1 text-gray-500 group-hover:text-pink-600">Instagram</span>
                </a>
            </div>
        </div>
    `;
}

/**
 * Opens the modal with the details of the selected item.
 * NOTE: The modal element (itemModal) is now located in index.html.
 * @param {object} item - The inventory item object.
 */
function openModal(item) {
    const modal = document.getElementById('itemModal');
    if (!modal) return; // Exit if modal isn't loaded yet

    document.getElementById('modalTitle').textContent = item.itemHeader;
    document.getElementById('modalSerial').textContent = item.serial;
    document.getElementById('modalPrice').textContent = `$${item.price.toFixed(2)}`;
    document.getElementById('modalDescription').innerHTML = item.descriptionHTML || '<p class="italic text-gray-400">No detailed description available.</p>';
    document.getElementById('modalKeywords').textContent = (item.keywords || []).join(', ') || 'N/A';

    // Inject contact information
    const modalContactSection = document.getElementById('modalContactSection');
    if (modalContactSection) modalContactSection.innerHTML = getModalContactHtml(item);

    const statusElement = document.getElementById('modalStatus');
    if (statusElement) {
        if (item.isSold) {
            statusElement.textContent = 'SOLD';
            statusElement.className = 'inline-block px-3 py-1 text-sm font-semibold mb-4 bg-red-100 text-red-700 rounded-full';
        } else {
            statusElement.textContent = 'AVAILABLE';
            statusElement.className = 'inline-block px-3 py-1 text-sm font-semibold mb-4 bg-green-100 text-green-700 rounded-full';
        }
    }

    // Image Handling (Base64)
    const mainImage = document.getElementById('modalImage');
    const thumbnailsContainer = document.getElementById('imageThumbnails');
    if (!mainImage || !thumbnailsContainer) return;

    thumbnailsContainer.innerHTML = '';

    const imageFiles = item.imageFiles || [];

    if (imageFiles.length > 0) {
        mainImage.src = imageFiles[0]; // Set first image as default

        imageFiles.forEach((base64, index) => {
            const thumb = document.createElement('img');
            thumb.src = base64;
            thumb.className = 'w-12 h-12 object-cover cursor-pointer flex justify-evenlyborder-2 border-transparent hover:border-blue-500 transition duration-150 rounded-md';

            // Add click listener to change the main image
            thumb.addEventListener('click', () => {
                mainImage.src = base64;
                document.querySelectorAll('#imageThumbnails img').forEach(t => t.classList.remove('border-blue-500'));
                thumb.classList.add('border-blue-500');
            });

            // Highlight the first thumbnail initially
            if (index === 0) {
                thumb.classList.add('border-blue-500');
            }

            thumbnailsContainer.appendChild(thumb);
        });
    } else {
        mainImage.src = 'https://placehold.co/1200x800/f5f5f5/cccccc?text=NO+IMAGE';
    }

    modal.classList.remove('hidden');
}


// --- Global Exports ---
// Expose functions globally so index.html can call them after content injection
window.openModal = openModal;

window.loadInventory = loadInventory; // Exported for index.html
