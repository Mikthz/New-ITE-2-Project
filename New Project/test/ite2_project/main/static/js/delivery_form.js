let selectedDeliveryItems = {};

function showDeliveryFormError(message) {
    const errorBox = document.getElementById("deliveryFormClientError");
    const errorText = document.getElementById("deliveryFormClientErrorText");

    if (!errorBox || !errorText) return;

    errorText.textContent = message;
    errorBox.classList.remove("hidden");
    errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearDeliveryFormError() {
    const errorBox = document.getElementById("deliveryFormClientError");
    const errorText = document.getElementById("deliveryFormClientErrorText");

    if (!errorBox || !errorText) return;

    errorText.textContent = "";
    errorBox.classList.add("hidden");
}

function addDeliveryItem() {
    const select = document.getElementById("productSelect");
    const quantityInput = document.getElementById("productQuantity");
    if (!select || !quantityInput) return;

    const selectedOption = select.options[select.selectedIndex];
    const productId = select.value;
    const quantity = parseInt(quantityInput.value, 10);
    const stock = parseInt(selectedOption?.dataset?.stock || 0, 10);

    if (!productId || quantity < 1 || Number.isNaN(quantity)) {
        showDeliveryFormError("Please select a product and enter a valid quantity.");
        return;
    }

    if (quantity > stock) {
        showDeliveryFormError("Quantity cannot be greater than available stock.");
        return;
    }

    clearDeliveryFormError();

    selectedDeliveryItems[productId] = {
        id: productId,
        name: selectedOption.dataset.name,
        company: selectedOption.dataset.company,
        price: selectedOption.dataset.price,
        image: selectedOption.dataset.image,
        quantity: quantity
    };

    renderSelectedDeliveryItems();

    select.value = "";
    quantityInput.value = 1;
    if (select.tomselect) select.tomselect.clear();
}

function removeDeliveryItem(productId) {
    delete selectedDeliveryItems[productId];
    renderSelectedDeliveryItems();
}

function renderSelectedDeliveryItems() {
    const list = document.getElementById("selectedItemsList");
    const hiddenInputs = document.getElementById("hiddenInputs");
    if (!list || !hiddenInputs) return;

    list.innerHTML = "";
    hiddenInputs.innerHTML = "";

    const items = Object.values(selectedDeliveryItems);

    if (items.length === 0) {
        list.innerHTML = `
            <div id="emptySelectedState" class="flex min-h-[110px] items-center rounded-2xl border border-dashed border-orange-300 bg-white/70 p-5">
                <div class="flex items-center gap-5">
                    <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-orange-100 text-orange-500">
                        <i class="fa-solid fa-box-open text-2xl"></i>
                    </div>
                    <div>
                        <p class="text-base font-bold text-slate-700">No products selected yet</p>
                        <p class="mt-1 text-sm text-slate-400">Add delivery products to build the customer order.</p>
                    </div>
                </div>
            </div>`;
        return;
    }

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
                    <button type="button" onclick="removeDeliveryItem('${item.id}')" class="flex h-9 w-9 items-center justify-center rounded-xl bg-red-100 text-red-500 hover:bg-red-200">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>`;
        hiddenInputs.innerHTML += `
            <input type="hidden" name="product_ids[]" value="${item.id}">
            <input type="hidden" name="quantities[]" value="${item.quantity}">`;
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("multiDeliveryForm");

    if (!form) return;

    form.addEventListener("submit", function (event) {
        if (Object.keys(selectedDeliveryItems).length === 0) {
            event.preventDefault();
            showDeliveryFormError("Please add at least one product before creating the delivery.");
        }
    });
});
