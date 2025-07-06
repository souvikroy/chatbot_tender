# Configuration for tender service
# Model tuning parameters

# File processing configuration
MAX_FILES_TO_PROCESS = 5  # Maximum number of files to process before selecting largest ones
TOP_FILES_TO_USE = 5     # Number of largest files to use when exceeding MAX_FILES_TO_PROCESS
CONTEXT_SIZE = 500      # Number of characters to include before and after keywords in text chunking

# Model configuration
TEMPERATURE = 0.7         # Controls randomness in responses (0.0-1.0)
MAX_TOKENS = 50000         # Maximum tokens in the response

# System prompt configuration
SYSTEM_PROMPT = """You are an expert tender document analyzer. Your role is to carefully analyze tender documents and provide accurate, detailed answers to questions about them.


Remember: Accuracy is crucial and answer should be short and summarised as these documents contain important business information."""