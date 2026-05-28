function closeAlert(id) {
    const alertBox = document.getElementById(id);
    if (alertBox) alertBox.remove();
}
setTimeout(function () {
    const errorAlert = document.getElementById('errorAlert');
    if (errorAlert) errorAlert.remove();
}, 5000);
