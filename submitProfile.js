import { getDatabase, ref, push } from "firebase/database";
import database from "./firebase.js"; // this connects to your Firebase config

document.getElementById("profileForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const userData = {
    name: document.getElementById("name").value,
    location: document.getElementById("location").value,
    age: document.getElementById("age").value,
    phone: document.getElementById("phone").value,
    interests: document.getElementById("interests").value,
  };

  const dbRef = ref(getDatabase(), "users/");

  push(dbRef, userData)
    .then(() => {
      console.log("✅ Successfully pushed to Firebase");
      window.location.href = "home.html"; // redirect
    })
    .catch((error) => {
      console.error("❌ Firebase push error:", error);
      alert("Error: " + error.message);
    });
});

