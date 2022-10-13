const myImage = document.querySelector("img");
const h1 = document.querySelector("h1");

h1.onclick = () => {
    alert("TEST");
}

myImage.onclick = () => {
  alert("HELLO");
  const mySrc = myImage.getAttribute("src");
  if (mySrc === "images/firefox-icon.png") {
    myImage.setAttribute("src", "images/firefox2.png");
  } else {
    myImage.setAttribute("src", "images/firefox-icon.png");
  }
};