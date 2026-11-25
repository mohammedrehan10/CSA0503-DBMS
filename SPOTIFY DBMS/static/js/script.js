/**
 * Spotify Audio Features & Popularity Explorer - Global Interactive UI Script
 * Controls modals, real-time client-side table pagination & search,
 * dropdowns, and range slider bindings.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Flash Alert Dismissals
    document.querySelectorAll(".alert-close").forEach(btn => {
        btn.addEventListener("click", () => {
            const alert = btn.closest(".alert");
            if (alert) alert.remove();
        });
    });

    setTimeout(() => {
        document.querySelectorAll(".alert").forEach(alert => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 500);
        });
    }, 5000);

    // 2. Header Dropdowns (Notifications & User Profile)
    setupDropdown("notifBtn", "notifDropdown");
    setupDropdown("userProfileBtn", "profileDropdown");

    function setupDropdown(triggerId, menuId) {
        const trigger = document.getElementById(triggerId);
        const menu = document.getElementById(menuId);
        if (!trigger || !menu) return;

        trigger.addEventListener("click", (e) => {
            e.stopPropagation();
            // Close other open dropdowns
            document.querySelectorAll(".dropdown-menu.open").forEach(m => {
                if (m !== menu) m.classList.remove("open");
            });
            menu.classList.toggle("open");
        });

        menu.addEventListener("click", (e) => {
            e.stopPropagation();
        });
    }

    document.addEventListener("click", () => {
        document.querySelectorAll(".dropdown-menu.open").forEach(m => {
            m.classList.remove("open");
        });
    });

    // 3. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            sidebar.classList.toggle("mobile-open");
        });

        document.addEventListener("click", (e) => {
            if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
                sidebar.classList.remove("mobile-open");
            }
        });
    }

    // 4. Live Global Search Suggestions
    const globalInput = document.getElementById("globalSearchInput");
    const suggestionsBox = document.getElementById("searchSuggestions");
    if (globalInput && suggestionsBox) {
        let debounceTimer = null;
        globalInput.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const query = globalInput.value.trim();
            if (query.length < 2) {
                suggestionsBox.innerHTML = "";
                suggestionsBox.classList.remove("open");
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(results => {
                        if (!results || results.length === 0) {
                            suggestionsBox.innerHTML = `<div class="suggestion-item muted">No results found for "${query}"</div>`;
                        } else {
                            suggestionsBox.innerHTML = results.map(t => `
                                <a href="/tracks?q=${encodeURIComponent(t.track_name)}" class="suggestion-item">
                                    <span class="sugg-title">${t.track_name}</span>
                                    <span class="sugg-sub">${t.artist_name} • ${t.album_name}</span>
                                    <span class="sugg-badge">${t.popularity} pop</span>
                                </a>
                            `).join("");
                        }
                        suggestionsBox.classList.add("open");
                    })
                    .catch(() => {
                        suggestionsBox.classList.remove("open");
                    });
            }, 250);
        });

        document.addEventListener("click", (e) => {
            if (!globalInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.classList.remove("open");
            }
        });
    }

    // 5. Range Sliders Synchronization with Numeric Badges
    document.querySelectorAll("input[type='range']").forEach(slider => {
        const valSpan = slider.parentElement.querySelector(".range-val");
        if (valSpan) {
            slider.addEventListener("input", () => {
                valSpan.textContent = slider.value;
            });
        }
    });

    // 6. Modal close on backdrop click or ESC key
    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.classList.remove("open");
            }
        });
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            document.querySelectorAll(".modal-overlay.open").forEach(modal => {
                modal.classList.remove("open");
            });
            document.querySelectorAll(".dropdown-menu.open").forEach(m => {
                m.classList.remove("open");
            });
        }
    });

    // 7. Client-side Table Pagination & Live Filtering
    setupTablePaginationAndSearch();
});

// ==============================================================================
// TABLE PAGINATION & FILTERING ENGINE
// ==============================================================================
function setupTablePaginationAndSearch() {
    const tableWrappers = document.querySelectorAll(".table-panel");

    tableWrappers.forEach(panel => {
        const table = panel.querySelector(".custom-table[data-paginate='true']");
        const paginationBox = panel.querySelector(".table-pagination");
        const clientSearch = panel.querySelector("#clientTableSearch");
        if (!table) return;

        const tbody = table.querySelector("tbody");
        if (!tbody) return;

        const allRows = Array.from(tbody.querySelectorAll("tr"));
        if (allRows.length === 0) return;

        const perPage = parseInt(table.getAttribute("data-per-page") || "10", 10);
        let currentPage = 1;
        let visibleRows = allRows;

        function renderPage() {
            const total = visibleRows.length;
            const totalPages = Math.max(1, Math.ceil(total / perPage));

            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIndex = (currentPage - 1) * perPage;
            const endIndex = Math.min(startIndex + perPage, total);

            // Hide all rows, display slice
            allRows.forEach(row => (row.style.display = "none"));
            for (let i = startIndex; i < endIndex; i++) {
                if (visibleRows[i]) visibleRows[i].style.display = "";
            }

            // Update pagination UI
            if (paginationBox) {
                const pageStart = paginationBox.querySelector(".page-start");
                const pageEnd = paginationBox.querySelector(".page-end");
                const pageTotal = paginationBox.querySelector(".page-total");
                const prevBtn = paginationBox.querySelector(".prev-btn");
                const nextBtn = paginationBox.querySelector(".next-btn");
                const numContainer = paginationBox.querySelector(".page-numbers");

                if (pageStart) pageStart.textContent = total === 0 ? 0 : startIndex + 1;
                if (pageEnd) pageEnd.textContent = endIndex;
                if (pageTotal) pageTotal.textContent = total;

                if (prevBtn) prevBtn.disabled = currentPage <= 1;
                if (nextBtn) nextBtn.disabled = currentPage >= totalPages;

                if (numContainer) {
                    numContainer.innerHTML = "";
                    for (let p = 1; p <= totalPages; p++) {
                        const btn = document.createElement("button");
                        btn.type = "button";
                        btn.className = `page-num ${p === currentPage ? "active" : ""}`;
                        btn.textContent = p;
                        btn.addEventListener("click", () => {
                            currentPage = p;
                            renderPage();
                        });
                        numContainer.appendChild(btn);
                    }
                }
            }
        }

        // Attach Previous / Next click handlers
        if (paginationBox) {
            const prevBtn = paginationBox.querySelector(".prev-btn");
            const nextBtn = paginationBox.querySelector(".next-btn");

            if (prevBtn) {
                prevBtn.addEventListener("click", () => {
                    if (currentPage > 1) {
                        currentPage--;
                        renderPage();
                    }
                });
            }

            if (nextBtn) {
                nextBtn.addEventListener("click", () => {
                    const totalPages = Math.ceil(visibleRows.length / perPage);
                    if (currentPage < totalPages) {
                        currentPage++;
                        renderPage();
                    }
                });
            }
        }

        // Instant Search Input
        if (clientSearch) {
            clientSearch.addEventListener("input", (e) => {
                const term = e.target.value.toLowerCase().trim();
                if (!term) {
                    visibleRows = allRows;
                } else {
                    visibleRows = allRows.filter(row => {
                        return row.innerText.toLowerCase().includes(term);
                    });
                }
                currentPage = 1;
                renderPage();
            });
        }

        // Initial render
        renderPage();
    });
}

// Modal Management Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add("open");
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove("open");
    }
}

// Edit Modal Pre-fillers
function editArtist(id, name, country) {
    const form = document.getElementById("editArtistForm");
    if (!form) return;
    form.action = `/artists/edit/${id}`;
    document.getElementById("edit_artist_id").value = id;
    document.getElementById("edit_artist_name").value = name;
    document.getElementById("edit_country").value = country;
    openModal("editArtistModal");
}

function editAlbum(id, name, releaseDate, artistId) {
    const form = document.getElementById("editAlbumForm");
    if (!form) return;
    form.action = `/albums/edit/${id}`;
    document.getElementById("edit_album_id").value = id;
    document.getElementById("edit_album_name").value = name;
    document.getElementById("edit_release_date").value = releaseDate;
    document.getElementById("edit_artist_id").value = artistId;
    openModal("editAlbumModal");
}

function editTrack(id, name, albumId, popularity, durationSec) {
    const form = document.getElementById("editTrackForm");
    if (!form) return;
    form.action = `/tracks/edit/${id}`;
    document.getElementById("edit_track_id").value = id;
    document.getElementById("edit_track_name").value = name;
    document.getElementById("edit_album_id").value = albumId;
    document.getElementById("edit_popularity").value = popularity;
    document.getElementById("edit_duration_sec").value = durationSec;
    
    // Update range badge
    const rangeSpan = document.querySelector("#editTrackModal .range-val");
    if (rangeSpan) rangeSpan.textContent = popularity;
    
    openModal("editTrackModal");
}

function editAudioFeatures(trackId, trackName, d, e, v, tempo, acoustic, loud) {
    const form = document.getElementById("featuresForm");
    if (!form) return;
    document.getElementById("feat_track_id").value = trackId;
    document.getElementById("feat_track_display").textContent = trackName || `Track #${trackId}`;
    
    setSliderVal("feat_danceability", d);
    setSliderVal("feat_energy", e);
    setSliderVal("feat_valence", v);
    setSliderVal("feat_acousticness", acoustic);
    
    document.getElementById("feat_tempo").value = tempo;
    document.getElementById("feat_loudness").value = loud;
    openModal("featuresModal");
}

function setSliderVal(elementId, val) {
    const input = document.getElementById(elementId);
    if (input) {
        input.value = val;
        const span = input.parentElement.querySelector(".range-val");
        if (span) span.textContent = val;
    }
}
