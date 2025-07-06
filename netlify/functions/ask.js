const { MongoClient } = require('mongodb');

// Environment variables
const MONGODB_URI = process.env.MONGODB_URI;
const MONGODB_DB_NAME = process.env.MONGODB_DB_NAME;
const MONGODB_PROCESSED_COLLECTION = process.env.MONGODB_PROCESSED_COLLECTION;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL;

let cachedDb = null;

async function connectToDatabase() {
  if (cachedDb) {
    return cachedDb;
  }
  
  const client = new MongoClient(MONGODB_URI);
  await client.connect();
  const db = client.db(MONGODB_DB_NAME);
  cachedDb = db;
  return db;
}

async function getTenderById(tenderId) {
  try {
    const db = await connectToDatabase();
    const collection = db.collection(MONGODB_PROCESSED_COLLECTION);
    const tender = await collection.findOne({ tender_id: tenderId });
    return tender;
  } catch (error) {
    console.error('Error retrieving tender:', error);
    return null;
  }
}

async function getGeminiResponse(prompt, systemPrompt) {
  try {
    // For simplicity, we'll use the Google AI API directly
    // In a real implementation, you might want to use the official SDK
    const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [{
          parts: [{
            text: systemPrompt + '\n\n' + prompt
          }]
        }],
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 2048,
        }
      })
    });

    const data = await response.json();
    
    if (data.candidates && data.candidates[0] && data.candidates[0].content) {
      return data.candidates[0].content.parts[0].text;
    } else {
      throw new Error('No valid response from Gemini API');
    }
  } catch (error) {
    console.error('Gemini API error:', error);
    throw error;
  }
}

exports.handler = async (event, context) => {
  // Handle CORS preflight request
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
      body: '',
    };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  try {
    const requestBody = JSON.parse(event.body || '{}');
    const { tender_id, question } = requestBody;

    if (!tender_id || !question) {
      return {
        statusCode: 400,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ error: 'tender_id and question are required' }),
      };
    }

    // Get tender from database
    const tender = await getTenderById(tender_id);
    if (!tender) {
      return {
        statusCode: 404,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          answer: `No tender found with ID: ${tender_id}. Please check the tender ID and try again.` 
        }),
      };
    }

    // Extract and combine file texts
    const fileTexts = tender.file_texts || {};
    let combinedText = '';
    
    if (typeof fileTexts === 'object' && fileTexts !== null) {
      combinedText = Object.values(fileTexts).join('\n\n---\n\n');
    } else if (typeof fileTexts === 'string') {
      combinedText = fileTexts;
    }

    if (!combinedText) {
      return {
        statusCode: 200,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          answer: 'No file texts found for this tender. The document may be empty or not properly processed.' 
        }),
      };
    }

    // System prompt
    const systemPrompt = `You are a helpful assistant that answers questions about tender documents. 
    Please provide accurate, detailed, and helpful responses based on the tender information provided. 
    If you cannot find specific information in the document, please say so clearly.`;

    // Create user prompt
    const userPrompt = `Here is the tender document with ID ${tender_id}:\n\n${combinedText}\n\nQuestion: ${question}`;

    // Get response from Gemini
    const answer = await getGeminiResponse(userPrompt, systemPrompt);

    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ answer }),
    };

  } catch (error) {
    console.error('Error processing request:', error);
    return {
      statusCode: 500,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        answer: 'I encountered an error while processing your request. Please try again later.' 
      }),
    };
  }
};
