function goBack() {
  window.history.back();
}
function goBlank() {
  window.location.href="about:blank";
}
function goData() {
  window.location.href="data:text/html,<html><body><h1>big</h1><h5>small</h5></body></html>";
}
function navigate() {
  var url = document.getElementById('navinput').value;
  alert(url);
  window.location.href=url;
}
document.getElementById('navbutton').addEventListener("click", navigate);
document.getElementById('backbutton').addEventListener("click", goBack);
document.getElementById('blankbutton').addEventListener("click", goBlank);
document.getElementById('databutton').addEventListener("click", goData);
