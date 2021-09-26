// white-dark mode
function darkwhite() {
  var element = document.body;
  element.classList.toggle("light-mode");
}

// return key input
function keyf()
{
    var input0 = document.getElementById("cardname").value;
    if (!input0.match(/\S/)) {
      document.getElementById("key1").innerHTML = "Please input a Standard card name!";
      document.getElementById("key1").style.color = "red";
    } else {
      document.getElementById("key1").innerHTML = "Card: " + input0
      document.getElementById("key1").style.color = "green";
    }
}

// check if all options are filled
function query0()
{
    var vkey = document.getElementById("key1").style.color;

    if (vkey === "red") {
        alert("Please fill in all fields or keep the default values!");
        return false;
    }
}

// API choice of image
function qnumb()
{
    var input0 = document.getElementById("ncard0").value;
    document.getElementById("ncard1").innerHTML = "Selection: " + input0
}
