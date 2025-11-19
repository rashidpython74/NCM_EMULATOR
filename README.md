# Monetx NCM SSH Emulator

A modern, web-based SSH terminal emulator designed for integration with Network Management Systems (NMS). Features a beautiful glassy UI design with real-time WebSocket communication and seamless NMS integration capabilities.

## 🚀 Features

- **Modern Web Interface**: Glassy, responsive design with Monetx branding
- **Real-time Terminal**: WebSocket-based terminal with low latency
- **NMS Integration**: Seamless integration with existing PHP/FastAPI NMS
- **Session Management**: Save/load SSH sessions
- **Quick Commands**: Pre-configured network command shortcuts
- **Audit Logging**: Comprehensive connection and command logging
- **Embedded Mode**: Can be embedded directly in existing NMS interface
- **Docker Support**: Ready for containerized deployment

## 📋 Prerequisites

- Python 3.8+
- Node.js (for development)
- Docker & Docker Compose (for production deployment)

## 🛠️ Installation

### Method 1: Direct Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd NCM_EMULATOR
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Create necessary directories**
```bash
mkdir -p logs uploads
```

4. **Add your Monetx logo**
```bash
# Place your monetx-logo.png in the static/ directory
cp path/to/monetx-logo.png static/
```

5. **Run the application**
```bash
python main.py
```

### Method 2: Docker Deployment

1. **Build and run with Docker Compose**
```bash
# Copy environment file and configure
cp .env.example .env
# Edit .env with your configuration

# Run with Docker Compose
docker-compose up -d
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Application Settings
DEBUG=false
HOST=0.0.0.0
PORT=8001

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# CORS Settings
CORS_ORIGINS=https://your-nms-domain.com

# NMS Integration
NMS_INTEGRATION_ENABLED=true
NMS_BASE_URL=https://your-nms-domain.com
NMS_API_KEY=your-nms-api-key

# SSH Settings
SSH_TIMEOUT=10
SSH_MAX_SESSIONS=100
SSH_SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

## 🔗 NMS Integration

### 1. Standalone Mode

Access the SSH emulator directly at `http://localhost:8001`

### 2. Embedded Mode

Embed the emulator in your existing NMS:

```html
<!-- In your NMS frontend -->
<iframe 
    src="http://localhost:8001/nms/embedded?device_id=123&session_token=xyz&auto_connect=true"
    width="100%" 
    height="600px"
    frameborder="0">
</iframe>
```

### 3. API Integration

Connect from your NMS backend:

```javascript
// Authenticate with NMS
const authResponse = await fetch('/nms/api/auth', {
    method: 'POST',
    headers: {
        'X-NMS-Token': 'your-nms-auth-token'
    }
});

const { session_token } = await authResponse.json();

// Connect to device
const connectResponse = await fetch('/nms/api/device-connect', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': session_token
    },
    body: JSON.stringify({
        device_id: 'device-123',
        device_ip: '192.168.1.1',
        username: 'admin',
        password: 'password'
    })
});

const { session_id } = await connectResponse.json();
```

## 🎨 Customization

### Logo and Branding

1. Replace `static/monetx-logo.png` with your logo
2. Modify `static/style.css` to adjust colors and styling

### Theme Customization

Edit the CSS variables in `static/style.css`:

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #7c3aed;
    --glass-bg: rgba(255, 255, 255, 0.1);
    --glass-border: rgba(255, 255, 255, 0.2);
    /* Add more custom colors */
}
```

## 📁 Project Structure

```
NCM_EMULATOR/
├── app.py                 # FastAPI application and SSH logic
├── main.py                # Application entry point
├── config.py              # Configuration settings
├── integration.py         # NMS integration module
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker deployment configuration
├── Dockerfile            # Docker image configuration
├── static/               # Static frontend assets
│   ├── index.html        # Main SSH emulator interface
│   ├── style.css         # Glassy UI styles
│   ├── script.js         # Frontend JavaScript
│   └── monetx-logo.png   # Monetx logo
├── templates/            # HTML templates
│   └── embedded.html     # Embedded mode template
├── logs/                 # Application logs
├── uploads/              # File upload directory
└── README.md            # This file
```

## 🔐 Security Features

- JWT-based session authentication
- CORS protection
- SSH connection timeout
- Audit logging for all connections
- Secure session management
- Environment-based configuration

## 🐳 Docker Deployment

### Production Deployment

1. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your production settings
```

2. **Deploy with Docker Compose**
```bash
docker-compose -f docker-compose.yml up -d
```

3. **Setup reverse proxy (optional)**
The included Nginx configuration provides SSL termination and load balancing.

### Health Checks

The application includes health checks at `/health` endpoint:

```bash
curl http://localhost:8001/health
```

## 📊 Monitoring and Logging

### Application Logs

Logs are written to `logs/app.log` with configurable levels:

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Audit Logs

All SSH connections and commands are logged for compliance:

```json
{
    "timestamp": "2024-01-01T12:00:00Z",
    "user_id": "admin",
    "device_ip": "192.168.1.1",
    "action": "ssh_connect",
    "session_id": "abc123"
}
```

## 🚀 API Endpoints

### Core Endpoints

- `GET /` - Main SSH emulator interface
- `GET /health` - Health check
- `POST /api/connect` - Establish SSH connection
- `POST /api/disconnect/{session_id}` - Close SSH connection
- `WS /ws/{session_id}` - WebSocket terminal communication

### NMS Integration Endpoints

- `GET /nms/embedded` - Embedded emulator interface
- `POST /nms/api/auth` - NMS authentication
- `POST /nms/api/device-connect` - Connect to specific device
- `GET /nms/api/device-info/{device_id}` - Get device information
- `GET /nms/api/user-sessions` - List user sessions

## 🛠️ Development

### Running in Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
```

### Frontend Development

The frontend files are in the `static/` directory:
- `index.html` - Main interface
- `style.css` - Styling and glass effects
- `script.js` - WebSocket client and terminal logic

### Testing

```bash
# Run tests (when implemented)
python -m pytest tests/
```

## 🔧 Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify host, port, username, and password
   - Check network connectivity
   - Ensure SSH service is running on target device

2. **WebSocket Connection Issues**
   - Check CORS settings
   - Verify firewall rules
   - Ensure WebSocket support in reverse proxy

3. **Embedded Mode Not Working**
   - Verify NMS integration is enabled
   - Check session token validity
   - Ensure proper CORS configuration

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📞 Support

For issues and support:
1. Check the application logs in `logs/app.log`
2. Verify configuration settings
3. Test SSH connectivity manually
4. Check network and firewall settings

## 📄 License

This project is proprietary to Monetx. All rights reserved.

## 🔄 Version History

- **v1.0.0** - Initial release with glassy UI design and NMS integration
  - WebSocket-based terminal communication
  - Embedded mode for NMS integration
  - Docker deployment support
  - Comprehensive audit logging
