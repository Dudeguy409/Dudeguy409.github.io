function goBack() {
  window.history.back();
}
function navigate() {
  var url = document.getElementById('navinput').value;
  alert(url);
  window.location.href=url;
}
document.getElementById('navbutton').addEventListener("click", navigate);
document.getElementById('backbutton').addEventListener("click", goBack);
