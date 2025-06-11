#!/usr/bin/env python3
"""
Docker Hardened Images Migration Tool

This script migrates Dockerfiles from Docker Official Images (DOI) to 
Docker Hardened Images (DHI) following Docker's migration guidelines.

Usage:
    python dhi_migrate.py <dockerfile_path> <dhi_image> [options]

Example:
    python dhi_migrate.py Dockerfile myorg/dhi-node:18-dev --output dhi.dockerfile
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MigrationRule:
    """Represents a transformation rule for Dockerfile migration."""
    pattern: str
    replacement: str
    description: str
    requires_multistage: bool = False

class DockerHardenedImagesMigrator:
    """Main migration tool for converting DOI Dockerfiles to DHI."""
    
    def __init__(self, dhi_image: str, namespace: str = None):
        self.dhi_image = dhi_image
        self.namespace = namespace
        self.migration_log = []
        
        # Define migration rules based on DHI documentation
        self.migration_rules = [
            MigrationRule(
                pattern=r'^FROM\s+([^\s]+)',
                replacement=self._replace_base_image,
                description="Replace base image with DHI equivalent"
            ),
            MigrationRule(
                pattern=r'^EXPOSE\s+([0-9]+)\s*$',
                replacement=self._check_privileged_ports,
                description="Check for privileged ports and update if needed"
            ),
            MigrationRule(
                pattern=r'^(RUN\s+(?:apt-get|yum|apk|pip)\s+.*)$',
                replacement=self._handle_package_installation,
                description="Handle package installation for minimal images",
                requires_multistage=True
            ),
            MigrationRule(
                pattern=r'^(CMD|ENTRYPOINT)\s+(.+)$',
                replacement=self._ensure_exec_form,
                description="Ensure CMD/ENTRYPOINT uses exec form"
            )
        ]
    
    def migrate_dockerfile(self, dockerfile_path: Path) -> Tuple[str, List[str]]:
        """
        Migrate a Dockerfile from DOI to DHI.
        
        Args:
            dockerfile_path: Path to the original Dockerfile
            
        Returns:
            Tuple of (migrated_content, migration_notes)
        """
        if not dockerfile_path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")
        
        original_content = dockerfile_path.read_text()
        lines = original_content.splitlines()
        
        # Analyze Dockerfile to determine migration strategy
        analysis = self._analyze_dockerfile(lines)
        
        # Apply migrations based on analysis
        if analysis['needs_multistage']:
            migrated_content = self._create_multistage_dockerfile(lines, analysis)
        else:
            migrated_content = self._apply_simple_migration(lines, analysis)
        
        return migrated_content, self.migration_log
    
    def _analyze_dockerfile(self, lines: List[str]) -> Dict:
        """Analyze Dockerfile to determine migration requirements."""
        analysis = {
            'original_base': None,
            'language': None,
            'has_package_manager': False,
            'has_build_commands': False,
            'exposed_ports': [],
            'needs_multistage': False,
            'uses_shell_form': False
        }
        
        for line in lines:
            line = line.strip()
            
            # Detect base image
            if line.startswith('FROM'):
                match = re.match(r'FROM\s+([^\s]+)', line)
                if match:
                    analysis['original_base'] = match.group(1)
                    analysis['language'] = self._detect_language(match.group(1))
            
            # Detect package installation
            if re.search(r'(apt-get|yum|apk|pip|npm|yarn)', line):
                analysis['has_package_manager'] = True
                analysis['needs_multistage'] = True
            
            # Detect build commands
            if re.search(r'(make|gcc|g\+\+|javac|go build|cargo build)', line):
                analysis['has_build_commands'] = True
                analysis['needs_multistage'] = True
            
            # Detect exposed ports
            if line.startswith('EXPOSE'):
                ports = re.findall(r'\d+', line)
                analysis['exposed_ports'].extend([int(p) for p in ports])
            
            # Detect shell form usage
            if re.match(r'^(CMD|ENTRYPOINT)\s+[^[]', line):
                analysis['uses_shell_form'] = True
        
        return analysis
    
    def _detect_language(self, base_image: str) -> Optional[str]:
        """Detect programming language from base image."""
        language_patterns = {
            'node': 'javascript',
            'python': 'python',
            'golang': 'go',
            'openjdk': 'java',
            'nginx': 'web',
            'alpine': 'generic'
        }
        
        for pattern, lang in language_patterns.items():
            if pattern in base_image.lower():
                return lang
        return 'generic'
    
    def _create_multistage_dockerfile(self, lines: List[str], analysis: Dict) -> str:
        """Create a multi-stage Dockerfile for complex applications."""
        self._log("Creating multi-stage Dockerfile for better security")
        
        # Determine DHI images for build and runtime
        build_image = self._get_build_image()
        runtime_image = self._get_runtime_image(analysis)
        
        dockerfile_parts = []
        
        # Add file header
        dockerfile_parts.append(self._generate_header())
        
        # Build stage
        dockerfile_parts.extend(self._generate_build_stage(lines, build_image, analysis))
        
        # Runtime stage
        dockerfile_parts.extend(self._generate_runtime_stage(lines, runtime_image, analysis))
        
        return '\n'.join(dockerfile_parts)
    
    def _generate_build_stage(self, lines: List[str], build_image: str, analysis: Dict) -> List[str]:
        """Generate the build stage of a multi-stage Dockerfile."""
        stage_lines = [
            f"# Build stage - using DHI dev image with build tools",
            f"FROM {build_image} AS build-stage",
            "WORKDIR /app"
        ]
        
        # Process original lines for build stage
        in_build_section = False
        for line in lines:
            line = line.strip()
            
            if line.startswith('FROM'):
                continue  # Skip original FROM
            
            if line.startswith('WORKDIR'):
                continue  # Already set
            
            # Include package installation and build commands
            if any(cmd in line for cmd in ['RUN', 'COPY', 'ADD']) and not line.startswith('CMD') and not line.startswith('ENTRYPOINT'):
                # Modify RUN commands for build stage
                if line.startswith('RUN') and any(pkg in line for pkg in ['apt-get', 'yum', 'apk']):
                    # Package installation - keep in build stage
                    stage_lines.append(line)
                    self._log("Moved package installation to build stage")
                elif line.startswith('COPY') or line.startswith('ADD'):
                    # Copy source files
                    stage_lines.append(line)
                elif line.startswith('RUN') and any(build_cmd in line for build_cmd in ['make', 'build', 'compile']):
                    # Build commands
                    stage_lines.append(line)
        
        # Add common build optimizations
        if analysis['language'] == 'go':
            stage_lines.extend([
                "# Build Go binary",
                "RUN CGO_ENABLED=0 GOOS=linux go build -o /app/binary ."
            ])
        elif analysis['language'] == 'javascript':
            stage_lines.extend([
                "# Install dependencies and build",
                "RUN npm ci --omit=dev"
            ])
        
        stage_lines.append("")  # Empty line for separation
        return stage_lines
    
    def _generate_runtime_stage(self, lines: List[str], runtime_image: str, analysis: Dict) -> List[str]:
        """Generate the runtime stage of a multi-stage Dockerfile."""
        stage_lines = [
            f"# Runtime stage - using minimal DHI image",
            f"FROM {runtime_image} AS runtime-stage",
            "",
            "# Create non-root user for security",
            "# DHI images run as nonroot user by default",
            "# Ensure files are accessible to nonroot user"
        ]
        
        # Set working directory
        stage_lines.extend([
            "WORKDIR /app",
            ""
        ])
        
        # Copy artifacts from build stage
        if analysis['language'] == 'go':
            stage_lines.append("COPY --from=build-stage /app/binary /app/binary")
        elif analysis['language'] == 'javascript':
            stage_lines.extend([
                "COPY --from=build-stage /app/node_modules ./node_modules",
                "COPY --from=build-stage /app/package*.json ./"
            ])
        else:
            stage_lines.append("COPY --from=build-stage /app /app")
        
        # Copy application files
        for line in lines:
            if line.strip().startswith('COPY') and 'package' not in line and '--from=' not in line:
                # Copy application files with proper ownership
                copy_line = line.strip()
                if '--chown=' not in copy_line:
                    copy_line = copy_line.replace('COPY', 'COPY --chown=nonroot:nonroot')
                stage_lines.append(copy_line)
        
        # Handle port exposure with privilege check
        for port in analysis['exposed_ports']:
            if port < 1024:
                stage_lines.append(f"# WARNING: Port {port} is privileged. Consider using port >= 1025")
                stage_lines.append(f"# or configure your application to use a higher port internally")
                stage_lines.append(f"EXPOSE {port + 8000}  # Changed from {port} to avoid privilege issues")
                self._log(f"Changed privileged port {port} to {port + 8000}")
            else:
                stage_lines.append(f"EXPOSE {port}")
        
        # Add CMD/ENTRYPOINT with proper form
        for line in lines:
            if line.strip().startswith(('CMD', 'ENTRYPOINT')):
                fixed_line = self._ensure_exec_form_line(line.strip())
                stage_lines.append(fixed_line)
        
        return stage_lines
    
    def _apply_simple_migration(self, lines: List[str], analysis: Dict) -> str:
        """Apply simple migration for basic Dockerfiles."""
        migrated_lines = []
        
        # Add header
        migrated_lines.append(self._generate_header())
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Apply migration rules
            for rule in self.migration_rules:
                if not rule.requires_multistage:
                    if isinstance(rule.replacement, str):
                        if re.match(rule.pattern, line):
                            line = re.sub(rule.pattern, rule.replacement, line)
                    else:
                        # Method-based replacement
                        line = rule.replacement(line)
            
            migrated_lines.append(line if line else original_line)
        
        return '\n'.join(migrated_lines)
    
    def _replace_base_image(self, line: str) -> str:
        """Replace the base image with DHI equivalent."""
        if line.startswith('FROM'):
            # Use the specified DHI image
            stage_name = ""
            if ' AS ' in line:
                stage_name = ' AS ' + line.split(' AS ')[1]
            
            new_line = f"FROM {self.dhi_image}{stage_name}"
            self._log(f"Replaced base image: {line} -> {new_line}")
            return new_line
        return line
    
    def _check_privileged_ports(self, line: str) -> str:
        """Check and update privileged ports."""
        if line.startswith('EXPOSE'):
            ports = re.findall(r'\d+', line)
            updated_ports = []
            
            for port in ports:
                port_num = int(port)
                if port_num < 1024:
                    new_port = port_num + 8000
                    updated_ports.append(str(new_port))
                    self._log(f"Changed privileged port {port} to {new_port}")
                else:
                    updated_ports.append(port)
            
            if updated_ports != ports:
                return f"EXPOSE {' '.join(updated_ports)}"
        
        return line
    
    def _handle_package_installation(self, line: str) -> str:
        """Handle package installation for minimal images."""
        if any(pkg_mgr in line for pkg_mgr in ['apt-get', 'yum', 'apk', 'pip']):
            self._log("Package installation detected - recommend using multi-stage build")
            return f"# NOTE: Move to build stage for DHI\n{line}"
        return line
    
    def _ensure_exec_form(self, line: str) -> str:
        """Ensure CMD/ENTRYPOINT uses exec form."""
        return self._ensure_exec_form_line(line)
    
    def _ensure_exec_form_line(self, line: str) -> str:
        """Convert CMD/ENTRYPOINT to exec form if needed."""
        if line.startswith(('CMD', 'ENTRYPOINT')):
            # Check if already in exec form (starts with [)
            cmd_part = line.split(' ', 1)[1] if ' ' in line else ''
            if not cmd_part.strip().startswith('['):
                # Convert to exec form
                instruction = line.split(' ')[0]
                cmd_args = cmd_part.strip()
                
                # Simple conversion - split on spaces and quote
                args = [f'"{arg}"' for arg in cmd_args.split()]
                exec_form = f"{instruction} [{', '.join(args)}]"
                
                self._log(f"Converted to exec form: {line} -> {exec_form}")
                return exec_form
        
        return line
    
    def _get_build_image(self) -> str:
        """Get the appropriate DHI build image."""
        if self.dhi_image.endswith('-dev'):
            return self.dhi_image
        else:
            # Assume we need to add -dev suffix
            base_name = self.dhi_image.split(':')[0]
            tag = self.dhi_image.split(':')[1] if ':' in self.dhi_image else 'latest'
            return f"{base_name}:{tag}-dev"
    
    def _get_runtime_image(self, analysis: Dict) -> str:
        """Get the appropriate DHI runtime image."""
        if analysis['language'] == 'go' and analysis['has_build_commands']:
            # For compiled Go binaries, use static image
            return "docker/dhi-static:20241121"
        else:
            # Use the non-dev version of the specified image
            if self.dhi_image.endswith('-dev'):
                return self.dhi_image.replace('-dev', '')
            return self.dhi_image
    
    def _generate_header(self) -> str:
        """Generate Dockerfile header with migration info."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# Dockerfile migrated to Docker Hardened Images (DHI)
# Generated by DHI Migration Tool on {timestamp}
# 
# Migration Notes:
# - Updated to use minimal, security-focused DHI base images
# - Configured to run as non-root user for enhanced security
# - Ports adjusted to avoid privilege requirements where needed
# - Multi-stage build implemented to reduce attack surface
#
# For more information about DHI, see:
# https://www.docker.com/products/hardened-images/

"""
    
    def _log(self, message: str):
        """Add a message to the migration log."""
        self.migration_log.append(message)

def main():
    parser = argparse.ArgumentParser(
        description="Migrate Dockerfiles from Docker Official Images to Docker Hardened Images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic migration
  python dhi_migrate.py Dockerfile myorg/dhi-node:18-dev
  
  # Specify output file
  python dhi_migrate.py Dockerfile myorg/dhi-python:3.11-dev --output dhi.dockerfile
  
  # Verbose output with migration notes
  python dhi_migrate.py Dockerfile myorg/dhi-golang:1.21-dev --verbose
        """
    )
    
    parser.add_argument('dockerfile', type=Path, help='Path to the original Dockerfile')
    parser.add_argument('dhi_image', help='DHI image to use (e.g., myorg/dhi-node:18-dev)')
    parser.add_argument('--output', '-o', type=Path, default='dhi.dockerfile',
                       help='Output file path (default: dhi.dockerfile)')
    parser.add_argument('--namespace', '-n', help='Docker Hub namespace for DHI images')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed migration notes')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without writing files')
    
    args = parser.parse_args()
    
    try:
        # Initialize migrator
        migrator = DockerHardenedImagesMigrator(args.dhi_image, args.namespace)
        
        # Perform migration
        print(f"Migrating {args.dockerfile} to DHI...")
        migrated_content, migration_log = migrator.migrate_dockerfile(args.dockerfile)
        
        if args.dry_run:
            print("\n--- Migrated Dockerfile (DRY RUN) ---")
            print(migrated_content)
        else:
            # Write migrated Dockerfile
            args.output.write_text(migrated_content)
            print(f"✅ Migration complete! Generated: {args.output}")
        
        # Show migration notes
        if args.verbose or args.dry_run:
            print(f"\n--- Migration Notes ---")
            for note in migration_log:
                print(f"• {note}")
        
        print(f"\n📋 Migration Summary:")
        print(f"   Source: {args.dockerfile}")
        print(f"   DHI Image: {args.dhi_image}")
        print(f"   Generated: {args.output}")
        print(f"   Notes: {len(migration_log)} changes applied")
        
        print(f"\n⚠️  Important Reminders:")
        print(f"   • Test the migrated Dockerfile thoroughly")
        print(f"   • Verify application works with non-root user")
        print(f"   • Check that all required files are accessible")
        print(f"   • Update port mappings if privileged ports were changed")
        print(f"   • Consider using Docker Debug for troubleshooting")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()