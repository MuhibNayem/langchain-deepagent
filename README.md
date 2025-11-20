# TestAgent - Deep Autonomy Agent Framework

A sophisticated AI agent framework built with LangChain, LangGraph, and OpenAI's GLM model for autonomous code analysis, research, and development tasks.

## 🚀 Overview

TestAgent is an advanced autonomous agent system designed to handle complex software engineering tasks including code analysis, file management, web research, and development operations. The framework leverages cutting-edge AI models and a modular tool architecture to provide intelligent automation capabilities.

## ✨ Key Features

### 🤖 Core Agent Capabilities
- **Deep Autonomy**: AI-powered autonomous task execution with planning capabilities
- **Multi-Agent Architecture**: Specialized subagents for different domains (web research, code execution)
- **Conversational Interface**: Interactive CLI for natural language interaction
- **Persistent Memory**: Thread-based conversation persistence with Redis/file-based checkpoints
- **Tool Integration**: Comprehensive set of tools for file operations, web research, and system tasks

### 🛠️ Tool Ecosystem
- **File Management**: Read, write, copy, move, delete files and directories
- **Web Operations**: Web crawling, surfing, and advanced search capabilities
- **System Integration**: Shell command execution, OS information retrieval
- **Weather API**: Real-time weather information
- **Code Processing**: Advanced file replacement with regex support
- **Safety Controls**: Path validation and security boundaries

### 🔧 Technical Architecture
- **LangGraph**: Advanced agent orchestration and workflow management
- **LangChain**: Modular tool integration and LLM connectivity
- **OpenAI GLM-4.5-Flash**: High-performance AI model for reasoning and execution
- **Redis/File Checkpointing**: Persistent conversation state management
- **Poetry**: Modern Python dependency management

## 📁 Project Structure

```
testagent/
├── main.py                    # CLI entry point and conversation interface
├── deep_agent.py             # Core agent configuration and tool setup
├── pyproject.toml            # Project dependencies and configuration
├── config/
│   └── checkpointer.py      # Checkpoint persistence (Redis/File)
├── py_tools/                 # Custom tool implementations
│   ├── registry.py          # Tool registry system
│   ├── os_info.py           # System information tools
│   ├── shell.py             # Shell command execution
│   ├── replace_in_file.py   # Advanced file replacement
│   ├── web_search.py        # Web search with multiple providers
│   ├── web_crawl.py         # Web content crawling
│   ├── weather.py           # Weather API integration
│   └── safety.py            # Security and path validation
├── docs/
│   └── security_analysis_report.md  # Security assessment
├── .env                     # Environment variables
└── langgraph.json           # LangGraph configuration
```

## 🛠️ Installation

### Prerequisites
- Python 3.12 or higher
- Redis server (optional, for checkpoint persistence)
- OpenAI API access (for GLM model)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd testagent
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Configure environment variables**
   Create a `.env` file with the following configuration:
   ```env
   # API Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_API_BASE=https://api.z.ai/api/paas/v4/
   
   # Optional: Redis for persistent checkpoints
   CHECKPOINT_REDIS_URL=redis://localhost:6379
   CHECKPOINT_REDIS_KEY=langgraph:checkpoints
   
   # Optional: Web search APIs
   SERPER_API_KEY=your_serper_api_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_custom_search_engine_id
   
   # Security settings
   ALLOWED_ROOT=/path/to/allowed/directory
   DEBUG_WEB_SEARCH=0
   ```

4. **Run the agent**
   ```bash
   # Start interactive CLI
   python main.py chat
   
   # Resume existing conversation
   python main.py chat --thread <thread-id>
   ```

## 🎯 Usage Examples

### Basic Conversation
```bash
$ python main.py chat
Deep Agent CLI
Type your question and press enter. Commands: /exit, /reset

You> Analyze this codebase for security vulnerabilities
Agent> I'll analyze the codebase for security vulnerabilities. Let me start by exploring the project structure...
```

### File Operations
```bash
You> Create a new Python script for data analysis
Agent> I'll create a Python script for data analysis. Let me start by planning the task...
```

### Web Research
```bash
You> Research the latest trends in AI agent development
Agent> I'll research the latest trends in AI agent development using multiple web sources...
```

### Code Analysis
```bash
You> Review the code quality and suggest improvements
Agent> I'll analyze the codebase for quality issues and provide improvement suggestions...
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GLM model | Yes |
| `OPENAI_API_BASE` | OpenAI API base URL | Yes |
| `CHECKPOINT_REDIS_URL` | Redis URL for persistence | Optional |
| `CHECKPOINT_REDIS_KEY` | Redis key for checkpoints | Optional |
| `ALLOWED_ROOT` | Root directory for file operations | Optional |
| `SERPER_API_KEY` | Serper API key for web search | Optional |
| `GOOGLE_API_KEY` | Google API key for custom search | Optional |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | Optional |
| `DEBUG_WEB_SEARCH` | Enable debug logging for web search | Optional |

### Tool Configuration

The framework uses a modular tool registry system. Tools can be configured in `py_tools/registry.py`:

```python
PY_TOOL_REGISTRY: dict[str, BaseTool] = {
    "os_info": os_info,
    "shell": shell,
    "replace_in_file": replace_in_file,
    "get_weather": get_weather,
    "web_crawl": web_crawl,
    "web_search": web_search,
}
```

## 🎨 Agent Architecture

### Main Agent
The main agent (`deep_agent.py`) orchestrates all operations with:
- **System Prompt**: Guides the agent's behavior and capabilities
- **Tool Registry**: Access to all available tools
- **Subagents**: Specialized assistants for specific tasks
- **Checkpointer**: Persistent conversation state

### Subagents
The framework includes two specialized subagents:

1. **Web Researcher**
   - Deep research and fact gathering
   - Web search and crawling capabilities
   - Citation-rich analysis

2. **Code Executor**
   - File system operations
   - Code analysis and editing
   - Shell command execution
   - System integration

### Tool Categories
- **File Management**: Read, write, copy, move, delete operations
- **Web Operations**: Search, crawl, and content extraction
- **System Integration**: Shell commands and OS information
- **Utilities**: Weather, replacement, and safety tools

## 🔒 Security Considerations

### Implemented Security Controls
- Path validation to prevent directory traversal
- Command timeout mechanisms
- Environment-based configuration
- Input validation for critical operations
- Secure tool boundaries

### Important Security Notes
⚠️ **Critical Security Issues Identified:**
1. **Hardcoded API Keys**: Remove API keys from source code
2. **Shell Command Injection**: Avoid `shell=True` in subprocess calls
3. **Path Traversal**: Strengthen path validation mechanisms
4. **Network Security**: Implement SSL/TLS verification for web requests

For detailed security analysis, see `docs/security_analysis_report.md`.

## 📊 Performance Optimization

### Caching and Persistence
- Redis-based checkpoint persistence for conversations
- File-based fallback for checkpoint storage
- Tool result caching (future enhancement)

### Resource Management
- Command timeout controls
- Memory-efficient streaming
- Connection pooling for web requests

## 🚀 Future Development Roadmap

### Phase 1: Security Hardening (Immediate)
- [ ] Remove hardcoded API keys
- [ ] Implement secure secret management
- [ ] Fix shell command injection vulnerabilities
- [ ] Add SSL/TLS verification for all network requests

### Phase 2: Enhanced Capabilities (Short-term)
- [ ] Add database integration tools
- [ ] Implement automated testing framework
- [ ] Add code quality analysis tools
- [ ] Extend web research capabilities

### Phase 3: Production Features (Medium-term)
- [ ] Add authentication and authorization
- [ ] Implement rate limiting and throttling
- [ ] Add comprehensive logging and monitoring
- [ ] Create web dashboard interface

### Phase 4: Advanced Features (Long-term)
- [ ] Multi-agent collaboration
- [ ] Automated code generation
- [ ] Advanced AI model integration
- [ ] Enterprise deployment options

## 🧪 Testing

### Unit Testing
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_agent.py

# Run with coverage
poetry run pytest --cov=deep_agent
```

### Integration Testing
```bash
# Test agent conversation flow
poetry run python tests/test_conversation.py

# Test tool integration
poetry run python tests/test_tools.py
```

## 📈 Monitoring and Logging

### Current Logging
- Debug logging for web search operations
- Error handling with detailed messages
- Tool execution tracking

### Enhanced Logging (Future)
- Structured logging with JSON format
- Performance metrics collection
- Error rate monitoring
- User interaction analytics

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone the repository
# Create a virtual environment
poetry install --with dev

# Install development dependencies
poetry add --group dev pytest black mypy flake8

# Run pre-commit hooks
poetry run pre-commit install
```

### Code Style
- Follow PEP 8 guidelines
- Use black for code formatting
- Add type hints for all functions
- Include docstrings for all public methods

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🆘 Support and Troubleshooting

### Common Issues

**API Key Issues**
- Verify API keys are correctly set in environment variables
- Check API base URL configuration
- Ensure API key has necessary permissions

**Redis Connection Problems**
- Verify Redis server is running
- Check Redis URL format
- Test Redis connection manually

**Tool Execution Errors**
- Check file permissions
- Verify path accessibility
- Review tool configuration

### Getting Help
- Create an issue on GitHub
- Check the security analysis report
- Review the tool documentation
- Test with simple commands first

## 🔄 Version History

### v0.1.0 (Current)
- Initial release with core agent functionality
- Basic tool ecosystem
- CLI interface
- Security analysis completed

### v0.2.0 (Planned)
- Security hardening
- Enhanced tool capabilities
- Improved error handling
- Documentation updates

## 🎯 Roadmap Summary

The TestAgent framework is designed to evolve from a basic autonomous agent to a comprehensive development assistant. Key focus areas include:

1. **Security First**: Address critical vulnerabilities and implement robust security controls
2. **Enhanced Capabilities**: Expand tool ecosystem and add specialized agents
3. **Production Ready**: Add monitoring, testing, and deployment features
4. **Enterprise Features**: Scale for team usage and advanced requirements

---

**Built with ❤️ using LangChain, LangGraph, and OpenAI's GLM model**

*For the latest updates and documentation, visit the project repository.*