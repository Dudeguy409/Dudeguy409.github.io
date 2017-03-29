function goBack() {
  window.history.back();
}
function goBlank() {
  window.location.href="about:blank";
}
function goData() {
  window.location.href="data:text/html,<html><body><h1>data URL big</h1><h5>data URL small</h5></body></html>";
}
function navigate() {
  var url = document.getElementById('navinput').value;
  alert("You are being navigated to the following URL that you entered: " + url);
  window.location.href=url;
}
document.getElementById('navbutton').addEventListener("click", navigate);
document.getElementById('backbutton').addEventListener("click", goBack);
document.getElementById('blankbutton').addEventListener("click", goBlank);
document.getElementById('databutton').addEventListener("click", goData);
