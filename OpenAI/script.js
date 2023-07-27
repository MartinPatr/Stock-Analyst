import { config } from 'dotenv';
config();

import { Configuration, OpenAIApi } from "openai";

// Create a new OpenAI API instance with my API key
const openai = new OpenAIApi(new Configuration({
    apiKey: process.env.API_KEY
}));

// Variables of my message and its responses
const message = "What is my name?"

let response;

// Create a chat completion 
openai.createChatCompletion({
    model: "gpt-3.5-turbo",
    messages: [{role: "user", content: message}],
})
.then(res => {
    response =  res.data.choices[0].message.content
    console.log(response)
})


// Outputs an array containing the last three words of the response
function getLastThreeWords(response) {
    if (response) {
        const words = response.split(" ");
        const lastThreeWords = words.slice(-3);
        console.log(lastThreeWords);
    } else {
        console.error("Failed to get a response from OpenAI API");
    }
}


setTimeout(() => {
    getLastThreeWords(response);
}, 45000);