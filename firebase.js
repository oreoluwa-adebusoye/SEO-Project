// firebase.js
import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";

const firebaseConfig = {
  apiKey: "AIzaSyDu8u6woABOlSENxY43p1ajTzhnURfOn8",
  authDomain: "newprofile-bdeb4.firebaseapp.com",
  databaseURL: "https://newprofile-bdeb4-default-rtdb.firebaseio.com",
  projectId: "newprofile-bdeb4",
  storageBucket: "newprofile-bdeb4.appspot.com",
  messagingSenderId: "480159206992",
  appId: "1:480159206992:web:680d18d0b35e1de1a30b55",
  measurementId: "G-X79SFPKR3Q"
};

const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

export default database;
