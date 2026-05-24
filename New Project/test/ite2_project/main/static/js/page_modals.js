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
function openEditModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
    }
}
function closeEditModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}
