const functions = require("firebase-functions");
const axios = require('axios');

// auth trigger (new user signup)
exports.newUserSignup = functions.auth.user().onCreate((user) => {
    console.log("user created", user.email, user.uid);
    axios.post("https://1bzul9draj.execute-api.ap-northeast-2.amazonaws.com/user", user.toJSON()).then(res=>{
        console.log(res.status);
        console.log(JSON.stringify(res.data))
    }).catch(err=>{
        console.log(err);
    });
})

// auth trigger (user deleted)
exports.userDeleted = functions.auth.user().onDelete((user) => {
    console.log("user deleted", user.email, user.uid);
    axios.delete(`https://1bzul9draj.execute-api.ap-northeast-2.amazonaws.com/user`, {
        data:{
            uid: user.uid,
            displayName: user.displayName
        }
    }).then(res=>{
        console.log(res.status);
        console.log(JSON.stringify(res.data));
    }).catch(err=>{
        console.log(err);
    });
})
