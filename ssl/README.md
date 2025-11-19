# SSL Certificate Setup

This directory should contain your SSL certificates for HTTPS deployment.

## Required Files

- `cert.pem` - SSL certificate file
- `key.pem` - Private key file

## Getting SSL Certificates

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to this directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem key.pem
```

### Option 2: Self-Signed Certificate (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

### Option 3: Commercial Certificate

Upload your commercial SSL certificates here:
- Rename your certificate file to `cert.pem`
- Rename your private key file to `key.pem`

## Security Notes

- Keep the private key (`key.pem`) secure and never share it
- Ensure proper file permissions:
  ```bash
  chmod 600 key.pem
  chmod 644 cert.pem
  ```
- Use certificates from a trusted Certificate Authority in production
- Consider using Let's Encrypt for free, automated SSL certificates
