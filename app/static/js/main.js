/* SmartCare - vanilla JS helpers (no framework) */

document.addEventListener("DOMContentLoaded", function () {
    initPrescriptionRows();
    initPatientAutocomplete();
    initConfirmForms();
    initBmiCalculator();
});

/* ---------------------------------------------------------------------
 * Dynamic prescription medicine rows (doctor consultation form)
 * ------------------------------------------------------------------- */
function initPrescriptionRows() {
    const container = document.getElementById("rx-items-container");
    const addBtn = document.getElementById("add-rx-item");
    if (!container || !addBtn) return;

    addBtn.addEventListener("click", function () {
        const row = buildRxRow();
        container.appendChild(row);
    });

    container.addEventListener("click", function (e) {
        if (e.target.closest(".remove-rx-item")) {
            const rows = container.querySelectorAll(".rx-item-row");
            if (rows.length > 1) {
                e.target.closest(".rx-item-row").remove();
            } else {
                // clear fields instead of removing the last row
                e.target.closest(".rx-item-row").querySelectorAll("input").forEach(i => i.value = "");
            }
        }
    });
}

function buildRxRow() {
    const div = document.createElement("div");
    div.className = "rx-item-row row g-2 align-items-end";
    div.innerHTML = `
        <div class="col-md-3">
            <label class="form-label small mb-1">Medicine Name</label>
            <input type="text" class="form-control form-control-sm" name="medicine_name[]" placeholder="e.g. Paracetamol">
        </div>
        <div class="col-md-2">
            <label class="form-label small mb-1">Dosage</label>
            <input type="text" class="form-control form-control-sm" name="dosage[]" placeholder="e.g. 500mg">
        </div>
        <div class="col-md-2">
            <label class="form-label small mb-1">Frequency</label>
            <input type="text" class="form-control form-control-sm" name="frequency[]" placeholder="e.g. 1-0-1">
        </div>
        <div class="col-md-2">
            <label class="form-label small mb-1">Duration</label>
            <input type="text" class="form-control form-control-sm" name="duration[]" placeholder="e.g. 5 days">
        </div>
        <div class="col-md-2">
            <label class="form-label small mb-1">Instructions</label>
            <input type="text" class="form-control form-control-sm" name="instructions[]" placeholder="e.g. After food">
        </div>
        <div class="col-md-1">
            <button type="button" class="btn btn-sm btn-outline-danger remove-rx-item w-100" title="Remove">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;
    return div;
}

/* ---------------------------------------------------------------------
 * Patient autocomplete search box (receptionist - create appointment)
 * ------------------------------------------------------------------- */
function initPatientAutocomplete() {
    const input = document.getElementById("patient-search-box");
    const hiddenId = document.getElementById("patient_id");
    const resultsBox = document.getElementById("patient-search-results");
    if (!input || !hiddenId || !resultsBox) return;

    let debounceTimer;
    input.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        const q = input.value.trim();
        hiddenId.value = "";
        if (q.length < 2) {
            resultsBox.innerHTML = "";
            resultsBox.classList.add("d-none");
            return;
        }
        debounceTimer = setTimeout(() => {
            fetch(`/reception/patients/lookup?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => renderResults(data))
                .catch(() => { resultsBox.innerHTML = ""; });
        }, 250);
    });

    function renderResults(items) {
        if (!items.length) {
            resultsBox.innerHTML = '<div class="list-group-item text-muted">No matching patients found</div>';
            resultsBox.classList.remove("d-none");
            return;
        }
        resultsBox.innerHTML = items.map(p => `
            <button type="button" class="list-group-item list-group-item-action patient-result"
                    data-id="${p.id}" data-label="${p.label.replace(/"/g, '&quot;')}">
                ${p.label}
            </button>
        `).join("");
        resultsBox.classList.remove("d-none");

        resultsBox.querySelectorAll(".patient-result").forEach(btn => {
            btn.addEventListener("click", function () {
                hiddenId.value = this.dataset.id;
                input.value = this.dataset.label;
                resultsBox.innerHTML = "";
                resultsBox.classList.add("d-none");
            });
        });
    }

    document.addEventListener("click", function (e) {
        if (!resultsBox.contains(e.target) && e.target !== input) {
            resultsBox.classList.add("d-none");
        }
    });
}

/* ---------------------------------------------------------------------
 * Confirm dialogs for destructive actions (cancel appointment, etc.)
 * ------------------------------------------------------------------- */
function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach(form => {
        form.addEventListener("submit", function (e) {
            const msg = form.getAttribute("data-confirm") || "Are you sure?";
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });
    });
}

/* ---------------------------------------------------------------------
 * Live BMI calculation on the vitals form
 * ------------------------------------------------------------------- */
function initBmiCalculator() {
    const weight = document.getElementById("weight");
    const height = document.getElementById("height");
    const bmiOut = document.getElementById("bmi-preview");
    if (!weight || !height || !bmiOut) return;

    function calc() {
        const w = parseFloat(weight.value);
        const h = parseFloat(height.value) / 100;
        if (w > 0 && h > 0) {
            const bmi = (w / (h * h)).toFixed(1);
            bmiOut.textContent = `BMI: ${bmi}`;
        } else {
            bmiOut.textContent = "";
        }
    }
    weight.addEventListener("input", calc);
    height.addEventListener("input", calc);
}
