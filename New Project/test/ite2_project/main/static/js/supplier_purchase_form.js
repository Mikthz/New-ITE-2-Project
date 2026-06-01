let selectedSupplierItems = {};

function showSupplierFormError(message) {
    const errorBox = document.getElementById("supplierFormClientError");
    const errorText = document.getElementById("supplierFormClientErrorText");

    if (!errorBox || !errorText) return;

    errorText.textContent = message;
    errorBox.classList.remove("hidden");
    errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}


function getSelectedSupplierId() {
    const items = Object.values(selectedSupplierItems);
    if (items.length === 0) return "";
    return items[0].supplierId || "";
}

function clearSupplierFormError() {
    const errorBox = document.getElementById("supplierFormClientError");
    const errorText = document.getElementById("supplierFormClientErrorText");

    if (!errorBox || !errorText) return;

    errorText.textContent = "";
    errorBox.classList.add("hidden");
}

function selectSuggestedSupplierProduct(id, name, company, price, image, supplierId) {
    const selectedSupplierId = getSelectedSupplierId();

    if (selectedSupplierId && supplierId && selectedSupplierId !== String(supplierId)) {
        showSupplierFormError("Please create one supplier expense per supplier. Remove the current selected items before choosing a different supplier.");
        return;
    }

    selectedSupplierItems[id] = { id, name, company, price, image, supplierId: supplierId || "", quantity: 1 };
    renderSelectedSupplierItems();
    const selectedBox = document.getElementById("selectedItemsBox");
    if (selectedBox) window.scrollTo({ top: selectedBox.offsetTop - 120, behavior: "smooth" });
}

function addSupplierItem() {
    const select = document.getElementById("supplierProductSelect");
    const quantityInput = document.getElementById("supplierQuantity");
    if (!select || !quantityInput) return;
    const selectedOption = select.options[select.selectedIndex];
    const productId = select.value;
    const quantity = parseInt(quantityInput.value, 10);
    const supplierId = selectedOption ? selectedOption.dataset.supplierId : "";
    const selectedSupplierId = getSelectedSupplierId();

    if (selectedSupplierId && supplierId && selectedSupplierId !== supplierId) {
        showSupplierFormError("Only one supplier can be selected when purchasing stocks. Remove the selected items first or create a separate supplier expense.");
        return;
    }

    if (!productId || quantity < 1 || Number.isNaN(quantity)) {
        showSupplierFormError("Please select a supplier product and enter a valid quantity.");
        return;
    }

    clearSupplierFormError();

    selectedSupplierItems[productId] = {
        id: productId,
        name: selectedOption.dataset.name,
        company: selectedOption.dataset.company,
        supplierId: supplierId,
        price: selectedOption.dataset.price,
        image: selectedOption.dataset.image,
        quantity: quantity
    };

    renderSelectedSupplierItems();
    select.value = "";
    quantityInput.value = 1;
    if (select.tomselect) select.tomselect.clear();
}

function removeSupplierItem(productId) {
    delete selectedSupplierItems[productId];
    renderSelectedSupplierItems();
}

function renderSelectedSupplierItems() {
    const box = document.getElementById("selectedItemsBox");
    const list = document.getElementById("selectedItemsList");
    const hiddenInputs = document.getElementById("hiddenInputs");
    if (!box || !list || !hiddenInputs) return;

    list.innerHTML = "";
    hiddenInputs.innerHTML = "";
    const items = Object.values(selectedSupplierItems);

    if (items.length === 0) {
        box.classList.add("hidden");
        return;
    }

    box.classList.remove("hidden");
    items.forEach(function (item) {
        list.innerHTML += `
            <div class="flex flex-col gap-4 rounded-2xl border border-orange-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
                <div class="flex items-center gap-4">
                    <img src="${item.image}" class="h-16 w-16 rounded-2xl border border-orange-200 object-cover shadow-sm" alt="${item.name}">
                    <div>
                        <div class="inline-flex rounded-xl border border-orange-300 bg-orange-50 px-3 py-1 text-sm font-bold text-orange-700">${item.name}</div>
                        <p class="mt-2 text-sm text-slate-500">${item.company} • ₱${item.price}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="rounded-xl bg-orange-100 px-4 py-2 text-sm font-bold text-orange-700">Qty: ${item.quantity}</span>
                    <button type="button" onclick="removeSupplierItem('${item.id}')" class="flex h-9 w-9 items-center justify-center rounded-xl bg-red-100 text-red-500 hover:bg-red-200">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>`;
        hiddenInputs.innerHTML += `
            <input type="hidden" name="supplier_product_ids[]" value="${item.id}">
            <input type="hidden" name="quantities[]" value="${item.quantity}">`;
    });
}


document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("multiPurchaseForm");

    if (!form) return;

    form.addEventListener("submit", function (event) {
        if (Object.keys(selectedSupplierItems).length === 0) {
            event.preventDefault();
            showSupplierFormError("Please add at least one supplier product before creating a supplier expense.");
        }
    });
});
