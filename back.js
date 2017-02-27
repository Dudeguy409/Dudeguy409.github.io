function goBack() {
  window.history.back();
}
function goBlank() {
  window.location.href="about:blank";
}
function navigate() {
  var url = document.getElementById('navinput').value;
  alert(url);
  window.location.href=url;
}
document.getElementById('navbutton').addEventListener("click", navigate);
document.getElementById('backbutton').addEventListener("click", goBack);
document.getElementById('blankbutton').addEventListener("click", goBlank);
