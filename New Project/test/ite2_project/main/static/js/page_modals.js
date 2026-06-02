function toggleEditProduct(id) {
    const row = document.getElementById(`edit-product-${id}`);
    if (row) row.classList.toggle("hidden");
}
function toggleEditDelivery(id) {
    const row = document.getElementById(`edit-delivery-${id}`);
    if (row) row.classList.toggle("hidden");
}
function toggleEditSupplier(id) {
    const row = document.getElementById(`edit-supplier-${id}`);
    if (row) row.classList.toggle("hidden");
}
function toggleEditSupplierProduct(id) {
    const row = document.getElementById(`edit-supplier-product-${id}`);
    if (row) row.classList.toggle("hidden");
}
function toggleEditSupplierDelivery(id) {
    const row = document.getElementById(`edit-supplier-delivery-${id}`);
    if (row) row.classList.toggle("hidden");
}
function toggleEditCategory(id) {
    const row = document.getElementById(`edit-category-${id}`);
    if (row) row.classList.toggle("hidden");
}
function refreshModalBodyLock() {
    const hasOpenModal = Boolean(document.querySelector(".edit-modal-overlay:not(.hidden)"));
    document.body.classList.toggle("modal-open", hasOpenModal);
}
function openEditModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        refreshModalBodyLock();
    }
}
function closeEditModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        refreshModalBodyLock();
    }
}
document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;

    document.querySelectorAll(".edit-modal-overlay:not(.hidden)").forEach(function (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    });

    refreshModalBodyLock();
});
document.addEventListener("click", function (event) {
    const overlay = event.target.closest(".edit-modal-overlay");

    if (!overlay || event.target !== overlay) return;

    overlay.classList.add("hidden");
    overlay.classList.remove("flex");
    refreshModalBodyLock();
});
