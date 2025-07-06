# 🤖 Tender Information Extraction API

A comprehensive API for extracting and analyzing information from tender documents using AI, supporting both Docker deployment and Netlify serverless functions.

## 🚀 Features

- **AI-Powered Analysis**: Uses Google Gemini AI for intelligent document analysis
- **MongoDB Integration**: Connects to MongoDB for document storage and retrieval
- **Dual Deployment**: Supports both Docker containers and Netlify serverless functions
- **Health Monitoring**: Built-in health checks and monitoring endpoints
- **CORS Enabled**: Ready for web application integration

## 📁 Project Structure

```
chatbot/
├── src/                    # Python FastAPI application
│   ├── main.py            # Application entry point
│   ├── tender_service.py  # Main API logic
│   ├── config.py          # Configuration settings
│   ├── text_chunker.py    # Document processing utilities
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── netlify/               # Netlify serverless functions
│   └── functions/
│       ├── health.js      # Health check endpoint
│       └── ask.js         # Main API endpoint
├── dist/                  # Build output for Netlify
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose setup
├── netlify.toml          # Netlify configuration
├── package.json          # Node.js dependencies for Netlify
└── index.html           # API documentation page
```

## 🐳 Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- MongoDB connection string
- Google Gemini API key

### Quick Start with Docker

1. **Clone and navigate to the project:**
   ```bash
   cd "C:\Users\svk ray\Documents\chatbot"
   ```

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Or build and run manually:**
   ```bash
   # Build the image
   docker build -t tender-api .
   
   # Run the container
   docker run -p 8000:8000 --env-file src/.env tender-api
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - Documentation: http://localhost:8000/docs

### Docker Commands

```bash
# Build the image
docker build -t tender-api .

# Run with environment variables
docker run -p 8000:8000 --env-file src/.env tender-api

# Run in background
docker run -d -p 8000:8000 --env-file src/.env --name tender-api tender-api

# View logs
docker logs tender-api

# Stop the container
docker stop tender-api
```

## ☁️ Netlify Deployment

### Prerequisites
- Netlify account
- Node.js installed
- Netlify CLI installed (`npm install -g netlify-cli`)

### Quick Start with Netlify

1. **Install dependencies:**
   ```bash
   cd "C:\Users\svk ray\Documents\chatbot"
   npm install
   ```

2. **Build the project:**
   ```bash
   npm run build
   ```

3. **Login to Netlify:**
   ```bash
   netlify login
   ```

4. **Initialize Netlify site:**
   ```bash
   netlify init
   ```

5. **Set environment variables in Netlify:**
   ```bash
   netlify env:set MONGODB_URI "your-mongodb-connection-string"
   netlify env:set MONGODB_DB_NAME "tender_analyzer"
   netlify env:set MONGODB_PROCESSED_COLLECTION "OCR_tender_docs"
   netlify env:set GEMINI_MODEL "gemini-2.0-flash"
   netlify env:set GEMINI_API_KEY "your-gemini-api-key"
   ```

6. **Deploy to Netlify:**
   ```bash
   # Deploy to preview
   netlify deploy
   
   # Deploy to production
   netlify deploy --prod
   ```

### Netlify Environment Variables

Set these in your Netlify dashboard or via CLI:

- `MONGODB_URI`: Your MongoDB connection string
- `MONGODB_DB_NAME`: Database name (e.g., "tender_analyzer")
- `MONGODB_PROCESSED_COLLECTION`: Collection name (e.g., "OCR_tender_docs")
- `GEMINI_MODEL`: AI model name (e.g., "gemini-2.0-flash")
- `GEMINI_API_KEY`: Your Google Gemini API key

## 🔧 Local Development

### Python/FastAPI (Docker)

1. **Run locally with Python:**
   ```bash
   cd src
   pip install -r requirements.txt
   python main.py
   ```

2. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Ask a question
   curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"tender_id": "your-tender-id", "question": "What are the requirements?"}'
   ```

### Netlify Functions

1. **Run Netlify dev server:**
   ```bash
   netlify dev
   ```

2. **Test serverless functions:**
   ```bash
   # Health check
   curl http://localhost:8888/api/health
   
   # Ask a question
   curl -X POST http://localhost:8888/api/ask \
     -H "Content-Type: application/json" \
     -d '{"tender_id": "your-tender-id", "question": "What are the requirements?"}'
   ```

## 📡 API Endpoints

### Health Check
- **URL**: `/health` (Docker) or `/api/health` (Netlify)
- **Method**: GET
- **Response**: 
  ```json
  {
    "status": "healthy",
    "message": "Tender Information Extraction API is running"
  }
  ```

### Ask Question
- **URL**: `/ask` (Docker) or `/api/ask` (Netlify)
- **Method**: POST
- **Body**:
  ```json
  {
    "tender_id": "your-tender-id",
    "question": "What are the technical requirements?"
  }
  ```
- **Response**:
  ```json
  {
    "answer": "Based on the tender document, the technical requirements include..."
  }
  ```

## 🛠️ Configuration

### Environment Variables (.env)

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=tender_analyzer
MONGODB_PROCESSED_COLLECTION=OCR_tender_docs
GEMINI_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your-api-key-here
```

### Docker Configuration

- **Port**: 8000 (configurable)
- **Health Checks**: Built-in health monitoring
- **Security**: Non-root user execution
- **Optimization**: Multi-stage build and minimal dependencies

### Netlify Configuration

- **Functions**: Node.js serverless functions in `/netlify/functions`
- **Build**: Static site with API redirects
- **CORS**: Enabled for cross-origin requests

## 🧪 Testing

### Test with curl

```bash
# Docker deployment
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"tender_id":"test","question":"test"}'

# Netlify deployment
curl https://your-site.netlify.app/api/health
curl -X POST https://your-site.netlify.app/api/ask -H "Content-Type: application/json" -d '{"tender_id":"test","question":"test"}'
```

## 🚨 Troubleshooting

### Common Issues

1. **Environment Variables Not Loading**
   - Ensure `.env` file exists in `src/` directory
   - Check file format (no spaces around `=`)
   - For Netlify, set variables in dashboard or CLI

2. **MongoDB Connection Issues**
   - Verify connection string format
   - Check network access and IP whitelist
   - Ensure database and collection exist

3. **Gemini API Errors**
   - Verify API key is correct
   - Check API quotas and limits
   - Ensure model name is correct

4. **Docker Build Issues**
   - Clear Docker cache: `docker system prune`
   - Rebuild without cache: `docker build --no-cache`

## 📝 License

MIT License - feel free to use this project for your own applications.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with ❤️ using FastAPI, MongoDB, Google Gemini AI, Docker, and Netlify**
