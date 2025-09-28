#!/usr/bin/env python3
"""
SSL Certificate Generation Script for LUCA

This script generates self-signed SSL certificates for the LUCA Flask application.
It creates both certificate and private key files for HTTPS support.

The script:
- Generates a private key using RSA 2048-bit encryption
- Creates a self-signed certificate valid for 365 days
- Supports multiple domain names and IP addresses
- Places certificates in the ssl/ directory

Usage:
    python scripts/generate_ssl_certs.py [--domain DOMAIN] [--days DAYS]
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_openssl_available() -> bool:
    """
    Check if OpenSSL is available in the system.

    Returns:
        bool: True if OpenSSL is available, False otherwise
    """
    try:
        import subprocess
        result = subprocess.run(['openssl', 'version'],
                              capture_output=True, text=True, check=True)
        logger.info(f"OpenSSL found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("OpenSSL not found. Please install OpenSSL.")
        return False

def generate_ssl_certificate(
    domain: str = "localhost",
    days: int = 365,
    key_size: int = 2048,
    output_dir: str = "ssl"
) -> bool:
    """
    Generate self-signed SSL certificate using OpenSSL.

    Args:
        domain: Primary domain name for the certificate
        days: Certificate validity period in days
        key_size: RSA key size in bits
        output_dir: Output directory for certificate files

    Returns:
        bool: True if generation successful, False otherwise
    """
    try:
        import subprocess

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Define file paths
        key_file = os.path.join(output_dir, "luca.key")
        cert_file = os.path.join(output_dir, "luca.crt")

        # Subject information for the certificate
        subject = f"/C=AR/ST=Buenos Aires/L=Buenos Aires/O=UCA/OU=LUCA/CN={domain}"

        # Subject Alternative Names (SAN) for multiple domains/IPs
        san_domains = [
            f"DNS:{domain}",
            "DNS:localhost",
            "DNS:127.0.0.1",
            "DNS:luca-app",
            "IP:127.0.0.1",
            "IP:::1"
        ]
        san_string = ",".join(san_domains)

        logger.info(f"Generating SSL certificate for domain: {domain}")
        logger.info(f"Certificate validity: {days} days")
        logger.info(f"Key size: {key_size} bits")
        logger.info(f"Output directory: {output_dir}")

        # Generate private key and certificate in one command
        openssl_cmd = [
            'openssl', 'req',
            '-x509',
            '-newkey', f'rsa:{key_size}',
            '-keyout', key_file,
            '-out', cert_file,
            '-days', str(days),
            '-nodes',  # Don't encrypt the private key
            '-subj', subject,
            '-extensions', 'v3_ca',
            '-config', '/dev/stdin'
        ]

        # OpenSSL configuration for extensions
        openssl_config = f"""
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = AR
ST = Buenos Aires
L = Buenos Aires
O = UCA
OU = LUCA
CN = {domain}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[v3_ca]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
{chr(10).join([f"{san.split(':')[0]}.{i+1} = {san.split(':', 1)[1]}" for i, san in enumerate(san_domains)])}
"""

        # Execute OpenSSL command
        process = subprocess.Popen(
            openssl_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=openssl_config)

        if process.returncode != 0:
            logger.error(f"OpenSSL command failed: {stderr}")
            return False

        # Verify files were created
        if not os.path.exists(key_file) or not os.path.exists(cert_file):
            logger.error("Certificate files were not created")
            return False

        # Set appropriate permissions
        os.chmod(key_file, 0o600)  # Private key: owner read/write only
        os.chmod(cert_file, 0o644)  # Certificate: owner read/write, others read

        logger.info(f"✅ SSL certificate generated successfully:")
        logger.info(f"  Private key: {key_file}")
        logger.info(f"  Certificate: {cert_file}")

        # Display certificate info
        cert_info_cmd = ['openssl', 'x509', '-in', cert_file, '-text', '-noout']
        try:
            result = subprocess.run(cert_info_cmd, capture_output=True, text=True, check=True)
            logger.info("Certificate details:")
            for line in result.stdout.split('\n'):
                if 'Subject:' in line or 'DNS:' in line or 'IP:' in line:
                    logger.info(f"  {line.strip()}")
        except subprocess.CalledProcessError:
            logger.warning("Could not display certificate details")

        return True

    except Exception as e:
        logger.error(f"Error generating SSL certificate: {e}")
        return False

def generate_with_cryptography(
    domain: str = "localhost",
    days: int = 365,
    key_size: int = 2048,
    output_dir: str = "ssl"
) -> bool:
    """
    Generate self-signed SSL certificate using Python cryptography library.
    Fallback method if OpenSSL is not available.

    Args:
        domain: Primary domain name for the certificate
        days: Certificate validity period in days
        key_size: RSA key size in bits
        output_dir: Output directory for certificate files

    Returns:
        bool: True if generation successful, False otherwise
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress

        logger.info("Using Python cryptography library to generate certificates")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )

        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Buenos Aires"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Buenos Aires"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "UCA"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "LUCA"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])

        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
                x509.DNSName("luca-app"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1")),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        # Write private key
        key_file = os.path.join(output_dir, "luca.key")
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate
        cert_file = os.path.join(output_dir, "luca.crt")
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Set appropriate permissions
        os.chmod(key_file, 0o600)  # Private key: owner read/write only
        os.chmod(cert_file, 0o644)  # Certificate: owner read/write, others read

        logger.info(f"✅ SSL certificate generated successfully:")
        logger.info(f"  Private key: {key_file}")
        logger.info(f"  Certificate: {cert_file}")
        logger.info(f"  Domain: {domain}")
        logger.info(f"  Valid for: {days} days")

        return True

    except ImportError:
        logger.error("Python cryptography library not available")
        logger.error("Install with: pip install cryptography")
        return False
    except Exception as e:
        logger.error(f"Error generating SSL certificate with cryptography: {e}")
        return False

def main():
    """Main function to generate SSL certificates."""
    parser = argparse.ArgumentParser(description="Generate self-signed SSL certificates for LUCA")
    parser.add_argument("--domain", type=str, default="localhost",
                       help="Primary domain name for certificate (default: localhost)")
    parser.add_argument("--days", type=int, default=365,
                       help="Certificate validity period in days (default: 365)")
    parser.add_argument("--key-size", type=int, default=2048,
                       help="RSA key size in bits (default: 2048)")
    parser.add_argument("--output-dir", type=str, default="ssl",
                       help="Output directory for certificate files (default: ssl)")
    parser.add_argument("--force-cryptography", action="store_true",
                       help="Force use of Python cryptography library instead of OpenSSL")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Make output directory path relative to project root if not absolute
    if not os.path.isabs(args.output_dir):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output_dir = os.path.join(project_root, args.output_dir)

    logger.info(f"Generating SSL certificates for LUCA")
    logger.info(f"Domain: {args.domain}")
    logger.info(f"Validity: {args.days} days")
    logger.info(f"Output directory: {args.output_dir}")

    try:
        success = False

        if not args.force_cryptography and check_openssl_available():
            # Try OpenSSL first
            success = generate_ssl_certificate(
                domain=args.domain,
                days=args.days,
                key_size=args.key_size,
                output_dir=args.output_dir
            )

        if not success:
            # Fallback to Python cryptography
            logger.info("Falling back to Python cryptography library")
            success = generate_with_cryptography(
                domain=args.domain,
                days=args.days,
                key_size=args.key_size,
                output_dir=args.output_dir
            )

        if success:
            logger.info("🎉 SSL certificate generation completed successfully!")
            logger.info("📝 Next steps:")
            logger.info("  1. Update your Flask application to use HTTPS")
            logger.info("  2. Configure Docker to expose port 443")
            logger.info("  3. Access your app at https://localhost")
            logger.info("⚠️  Note: Browser will show security warning for self-signed certificates")
            return 0
        else:
            logger.error("❌ SSL certificate generation failed")
            return 1

    except Exception as e:
        logger.error(f"SSL certificate generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())