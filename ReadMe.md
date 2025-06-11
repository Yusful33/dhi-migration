# Docker Hardened Images Migration Tool

🔒 **Automatically migrate your Dockerfiles from Docker Official Images to Docker Hardened Images (DHI)**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This tool automates the migration process from Docker Official Images to Docker Hardened Images, following Docker's official migration guidelines to improve container security through minimal attack surfaces, non-root execution, and reduced dependencies.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/dhi-migration.git
cd dhi-migration

# Run the migration tool
python dhi_migrate.py Dockerfile your-namespace/dhi-node:18-dev
```

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Advanced Options](#advanced-options)
  - [Examples](#examples)
- [How It Works](#-how-it-works)
- [Migration Guidelines](#-migration-guidelines)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **🔄 Automated Migration**: Transforms Dockerfiles following Docker's official DHI migration patterns
- **🏗️ Multi-stage Builds**: Automatically creates multi-stage builds when build tools are detected
- **🔒 Security First**: Configures non-root users, handles privileged ports, ensures proper permissions
- **📦 Smart Package Handling**: Moves package installation to build stages for minimal runtime images
- **🎯 Language Detection**: Automatically detects and optimizes for Node.js, Python, Go, Java applications
- **📝 Detailed Logging**: Comprehensive migration notes explaining all changes
- **🧪 Dry Run Mode**: Preview changes before applying them
- **⚡ Batch Processing**: Process multiple Dockerfiles (coming soon)

## 🛠 Installation

### Prerequisites

- Python 3.8 or higher
- Access to Docker Hardened Images (DHI) in your Docker Hub namespace

### Clone and Setup

```bash
git clone https://github.com/yourusername/dhi-migration.git
cd dhi-migration
chmod +x dhi_migrate.py
```

No additional dependencies required - uses only Python standard library!

## 🎯 Usage

### Basic Usage

```bash
python dhi_migrate.py <dockerfile_path> <dhi_image> [options]
```

**Required Arguments:**
- `dockerfile_path`: Path to your original Dockerfile
- `dhi_image`: The DHI image to use (e.g., `myorg/dhi-node:18-dev`)

### Advanced Options

| Option | Description | Example |
|--------|-------------|---------|
| `--output`, `-o` | Output file path | `-o production.dockerfile` |
| `--namespace`, `-n` | Docker Hub namespace | `-n myorganization` |
| `--verbose`, `-v` | Show detailed migration notes | `-v` |
| `--dry-run` | Preview changes without writing | `--dry-run` |

### Examples

#### Migrate a Node.js Application
```bash
# Basic migration
python dhi_migrate.py Dockerfile myorg/dhi-node:18-dev

# With custom output and verbose logging
python dhi_migrate.py Dockerfile myorg/dhi-node:18-dev \
  --output dhi.dockerfile \
  --verbose
```

#### Migrate a Python Application
```bash
python dhi_migrate.py Dockerfile myorg/dhi-python:3.11-dev \
  --output secure.dockerfile
```

#### Migrate a Go Application
```bash
# Go applications often get optimized to use static images
python dhi_migrate.py Dockerfile myorg/dhi-golang:1.21-dev \
  --verbose
```

#### Preview Changes (Dry Run)
```bash
python dhi_migrate.py Dockerfile myorg/dhi-node:18-dev --dry-run
```

## 🔧 How It Works

The migration tool follows Docker's official DHI migration guidelines:

### 1. **Base Image Replacement**
```dockerfile
# Before
FROM node:18

# After  
FROM myorg/dhi-node:18-dev AS build-stage
```

### 2. **Multi-stage Build Creation**
When package managers or build tools are detected, creates optimized multi-stage builds:

```dockerfile
# Build stage - with dev tools
FROM myorg/dhi-node:18-dev AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

# Runtime stage - minimal image
FROM myorg/dhi-node:18 AS runtime-stage
WORKDIR /app
COPY --from=build-stage --chown=nonroot:nonroot /app /app
USER nonroot
CMD ["node", "server.js"]
```

### 3. **Security Hardening**
- **Non-root User**: Configures applications to run as `nonroot` user
- **Port Security**: Adjusts privileged ports (<1024) to safe alternatives
- **Exec Form**: Converts shell form commands to exec form for proper signal handling
- **File Permissions**: Ensures proper ownership with `--chown` flags

### 4. **Smart Optimizations**
- **Go Applications**: Uses `docker/dhi-static` for compiled binaries
- **Package Management**: Moves `apt-get`, `yum`, `apk`, `pip` to build stages
- **TLS Certificates**: Leverages built-in certificates in DHI images

## 📖 Migration Guidelines

### Before Migration
1. **Access DHI Images**: Ensure you have access to DHI images in your namespace
2. **Review Current Dockerfile**: Understand your application's dependencies
3. **Backup Original**: Keep a copy of your original Dockerfile

### DHI Image Naming Convention
- **Build Images**: Use `-dev` suffix (e.g., `myorg/dhi-node:18-dev`)
- **Runtime Images**: No suffix (e.g., `myorg/dhi-node:18`)
- **Static Images**: For compiled binaries (`docker/dhi-static:20241121`)

### After Migration
1. **Test Thoroughly**: Build and run the migrated image
2. **Check Permissions**: Verify file access with non-root user
3. **Update Port Mappings**: Adjust port mappings if ports were changed
4. **Monitor Performance**: Ensure application performs as expected

## 🔍 Understanding the Output

The tool generates a new Dockerfile with:

```dockerfile
# Dockerfile migrated to Docker Hardened Images (DHI)
# Generated by DHI Migration Tool on 2024-06-11 15:30:45
# 
# Migration Notes:
# - Updated to use minimal, security-focused DHI base images
# - Configured to run as non-root user for enhanced security
# - Ports adjusted to avoid privilege requirements where needed
# - Multi-stage build implemented to reduce attack surface
```

### Migration Log Examples
```
• Replaced base image: FROM node:18 -> FROM myorg/dhi-node:18-dev
• Changed privileged port 80 to 8080
• Converted to exec form: CMD node server.js -> CMD ["node", "server.js"]
• Moved package installation to build stage
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Permission Denied Errors
```bash
# Problem: Application can't write files
# Solution: Ensure directories are owned by nonroot user
RUN mkdir -p /app/logs && chown -R nonroot:nonroot /app/logs
```

#### Port Binding Issues
```bash
# Problem: Can't bind to port < 1024
# Solution: Use higher ports or configure port mapping
# Tool automatically suggests: EXPOSE 8080  # Changed from 80
```

#### Missing Dependencies
```bash
# Problem: Runtime image missing packages
# Solution: Multi-stage build copies dependencies correctly
COPY --from=build-stage /app/node_modules ./node_modules
```

#### Signal Handling Problems
```bash
# Problem: Container doesn't stop gracefully
# Solution: Tool converts to exec form automatically
CMD ["node", "server.js"]  # Instead of: CMD node server.js
```

### Getting Help

1. **Run with `--verbose`**: See detailed migration notes
2. **Use `--dry-run`**: Preview changes before applying
3. **Check Docker Logs**: `docker logs <container_id>`
4. **Use Docker Debug**: For troubleshooting DHI containers

## 🧪 Testing Your Migration

### Build and Test Process
```bash
# 1. Build the migrated image
docker build -f dhi.dockerfile -t myapp:dhi .

# 2. Test basic functionality
docker run --rm myapp:dhi

# 3. Test with port mapping
docker run --rm -p 8080:8080 myapp:dhi

# 4. Test file permissions
docker run --rm -v $(pwd)/data:/app/data myapp:dhi

# 5. Test in production-like environment
docker-compose -f docker-compose.dhi.yml up
```

### Validation Checklist
- [ ] Image builds successfully
- [ ] Application starts without errors
- [ ] Non-root user can access required files
- [ ] Network connectivity works
- [ ] Port mappings function correctly
- [ ] Graceful shutdown works (SIGTERM handling)

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup
```bash
git clone https://github.com/yourusername/dhi-migration.git
cd dhi-migration

# Create test files
mkdir test-cases
# Add your test Dockerfiles here
```

### Running Tests
```bash
# Test migrations on sample Dockerfiles
python dhi_migrate.py test-cases/node.dockerfile myorg/dhi-node:18-dev --dry-run
python dhi_migrate.py test-cases/python.dockerfile myorg/dhi-python:3.11-dev --dry-run
```

### Contribution Guidelines
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for your changes
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Areas for Contribution
- [ ] Add support for more programming languages
- [ ] Implement batch processing for multiple Dockerfiles
- [ ] Add integration with Docker Scout for security scanning
- [ ] Improve language detection algorithms
- [ ] Add support for custom transformation rules
- [ ] Create web interface version

## 📚 Resources

### Docker Hardened Images Documentation
- [Docker DHI Overview](https://www.docker.com/products/hardened-images/)
- [DHI Migration Guide](https://docs.docker.com/hardened-images/migration/)
- [Container Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

### Related Tools
- [Docker Scout](https://docs.docker.com/scout/) - Security scanning
- [Hadolint](https://github.com/hadolint/hadolint) - Dockerfile linting
- [Dive](https://github.com/wagoodman/dive) - Image layer analysis

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Docker team for creating Docker Hardened Images
- Community contributors for feedback and improvements
- Security researchers for container hardening best practices

---

**⚠️ Important**: Always test migrated Dockerfiles thoroughly in your staging environment before deploying to production. DHI migration can change application behavior, especially around file permissions and port bindings.

**🔐 Security Note**: This tool helps improve your container security posture, but security is a continuous process. Regularly update your DHI base images and monitor for security advisories.