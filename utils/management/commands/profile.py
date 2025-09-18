"""
profile.py: Django management command for comprehensive PyInstrument profiling management.
Handles profile generation, syncing, serving, and analysis.
Path: /home/katestheimeno/dev/DRF-starter/utils/management/commands/profile.py
"""

import asyncio
import aiohttp
import argparse
import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, quote
import http.server
import socketserver
import threading
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Comprehensive PyInstrument profiling management tool'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')

        # Profile generation command
        generate_parser = subparsers.add_parser('generate', help='Generate profiles by hitting endpoints')
        generate_parser.add_argument('--config', default=os.getenv('PROFILING_CONFIG_FILE', 'profiling_config.json'), help='Configuration file path')
        generate_parser.add_argument('--base-url', default=os.getenv('PROFILING_BASE_URL', 'http://127.0.0.1:8101'), help='Base URL to test')
        generate_parser.add_argument('--concurrent', type=int, default=int(os.getenv('PROFILING_CONCURRENT_REQUESTS', '3')), help='Concurrent requests')
        generate_parser.add_argument('--requests', type=int, default=int(os.getenv('PROFILING_REQUESTS_PER_ENDPOINT', '2')), help='Requests per endpoint')
        generate_parser.add_argument('--endpoints', help='Comma-separated endpoint groups to test')
        generate_parser.add_argument('--include-disabled', action='store_true', help='Include disabled endpoints')
        generate_parser.add_argument('--email', default=os.getenv('PROFILING_AUTH_EMAIL', 'admin@example.com'), help='Auth email')
        generate_parser.add_argument('--password', default=os.getenv('PROFILING_AUTH_PASSWORD', 'admin'), help='Auth password')

        # Sync profiles command
        sync_parser = subparsers.add_parser('sync', help='Sync profiles from Docker container')
        sync_parser.add_argument('--container', default=os.getenv('PROFILING_CONTAINER_NAME', 'web_profiling'), help='Container name')

        # Serve profiles command
        serve_parser = subparsers.add_parser('serve', help='Serve profiles via HTTP server')
        serve_parser.add_argument('--port', type=int, default=int(os.getenv('PROFILING_SERVE_PORT', '8080')), help='Port to serve on')
        serve_parser.add_argument('--app', help='Filter by app')
        serve_parser.add_argument('--limit', type=str, default=os.getenv('PROFILING_SERVE_LIMIT', '20'), help='Limit profiles shown')
        serve_parser.add_argument('--sort', choices=['time', 'duration', 'size'], default=os.getenv('PROFILING_SERVE_SORT', 'time'))
        serve_parser.add_argument('--no-browser', action='store_true', help='Don\'t open browser')
        serve_parser.add_argument('--auto-sync', action='store_true', help='Auto-sync before serving')

        # HTML dashboard command
        html_parser = subparsers.add_parser('dashboard', help='Generate HTML dashboard')
        html_parser.add_argument('--output', help='Output HTML file path')
        html_parser.add_argument('--auto-sync', action='store_true', help='Auto-sync before generating')

        # Analysis command
        analyze_parser = subparsers.add_parser('analyze', help='Analyze existing profiles')
        analyze_parser.add_argument('--app', help='Filter by app')
        analyze_parser.add_argument('--limit', type=str, default=os.getenv('PROFILING_ANALYZE_LIMIT', '20'), help='Limit profiles shown')
        analyze_parser.add_argument('--sort', choices=['time', 'duration', 'size'], default=os.getenv('PROFILING_ANALYZE_SORT', 'time'))

        # Clean command
        clean_parser = subparsers.add_parser('clean', help='Clean old profiles')
        clean_parser.add_argument('--days', type=int, default=int(os.getenv('PROFILING_CLEAN_DAYS', '7')), help='Keep profiles newer than N days')
        clean_parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')

    def handle(self, *args, **options):
        action = options['action']
        
        if not action:
            self.print_help()
            return

        try:
            if action == 'generate':
                asyncio.run(self.handle_generate(options))
            elif action == 'sync':
                self.handle_sync(options)
            elif action == 'serve':
                self.handle_serve(options)
            elif action == 'dashboard':
                self.handle_dashboard(options)
            elif action == 'analyze':
                self.handle_analyze(options)
            elif action == 'clean':
                self.handle_clean(options)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nOperation cancelled by user'))
        except Exception as e:
            raise CommandError(f'Error: {e}')

    def print_help(self):
        """Print comprehensive help information."""
        help_text = """
Django Profiling Management Tool

Available Commands:
  generate  - Generate profiles by hitting configured endpoints
  sync      - Sync profiles from Docker container to local directory
  serve     - Start HTTP server to view profiles
  dashboard - Generate a modern HTML dashboard
  analyze   - Analyze existing profiles and show statistics
  clean     - Clean old profile files

Examples:
  uv run manage.py profile generate --config profiling_config.json
  uv run manage.py profile generate --endpoints "custom_auth,api_docs"
  uv run manage.py profile generate --include-disabled  # Include health checks
  uv run manage.py profile sync --container web_profiling
  uv run manage.py profile serve --port 8080 --app custom_auth
  uv run manage.py profile dashboard --auto-sync
  uv run manage.py profile analyze --app custom_auth --limit 10
  uv run manage.py profile clean --days 7 --dry-run

Configuration:
  Create a JSON file with endpoint configurations. Example:
  {
    "auth": {
      "login_endpoint": "/api/auth/jwt/create/",
      "email_field": "email",
      "password_field": "password"
    },
    "endpoint_groups": {
      "users": [
        {"endpoint": "/api/users/", "method": "GET", "auth": true},
        {"endpoint": "/api/users/me/", "method": "GET", "auth": true}
      ],
      "posts": [
        {"endpoint": "/api/posts/", "method": "GET", "auth": true}
      ]
    }
  }
        """
        self.stdout.write(help_text)

    async def handle_generate(self, options):
        """Handle profile generation."""
        config_path = Path(options['config'])
        if not config_path.exists():
            self.create_default_config(config_path)
            self.stdout.write(
                self.style.SUCCESS(f'Created default config at {config_path}')
            )
            return

        with open(config_path) as f:
            config = json.load(f)

        runner = ProfileRunner(
            base_url=options['base_url'],
            config=config,
            email=options['email'],
            password=options['password']
        )

        # Determine which endpoint groups to test
        include_disabled = options.get('include_disabled', False)
        
        if options['endpoints']:
            groups = options['endpoints'].split(',')
            endpoints = []
            for group in groups:
                if group.strip() in config['endpoint_groups']:
                    group_endpoints = config['endpoint_groups'][group.strip()]
                    if include_disabled:
                        endpoints.extend(group_endpoints)
                    else:
                        # Filter out disabled endpoints unless explicitly requested
                        endpoints.extend([ep for ep in group_endpoints if ep.get('enabled', True)])
        else:
            endpoints = []
            for group_endpoints in config['endpoint_groups'].values():
                if include_disabled:
                    endpoints.extend(group_endpoints)
                else:
                    # Filter out disabled endpoints by default
                    endpoints.extend([ep for ep in group_endpoints if ep.get('enabled', True)])

        self.stdout.write(f'Starting profile generation with {len(endpoints)} endpoints')

        async with runner:
            results = await runner.run_endpoint_tests(
                endpoints,
                options['concurrent'],
                options['requests']
            )

        runner.print_summary()
        self.stdout.write(self.style.SUCCESS('Profile generation completed!'))

    def handle_sync(self, options):
        """Handle profile syncing from Docker."""
        container = options['container']
        profiles_dir = self.get_profiles_dir()

        self.stdout.write('Syncing profiles from Docker container...')

        try:
            # Check if container is running
            result = subprocess.run([
                'docker-compose', 'ps', '-q', container
            ], capture_output=True, text=True, check=True)

            if not result.stdout.strip():
                self.stdout.write(
                    self.style.WARNING(f'Container {container} not running')
                )
                return

            # Get profile files from container
            result = subprocess.run([
                'docker-compose', 'exec', '-T', container,
                'find', '/app/profiles', '-name', '*.html', '-type', 'f'
            ], capture_output=True, text=True, check=True)

            profile_files = [f for f in result.stdout.strip().split('\n') if f]
            
            if not profile_files:
                self.stdout.write('No profile files found in container')
                return

            copied_count = 0
            for profile_path in profile_files:
                profile_name = Path(profile_path).name
                host_path = profiles_dir / profile_name

                if host_path.exists():
                    continue

                try:
                    subprocess.run([
                        'docker', 'cp', f'{container}:{profile_path}', str(host_path)
                    ], check=True, capture_output=True)
                    copied_count += 1
                    self.stdout.write(f'Synced: {profile_name}')
                except subprocess.CalledProcessError:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to sync: {profile_name}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully synced {copied_count} profiles')
            )

        except subprocess.CalledProcessError as e:
            raise CommandError(f'Docker sync failed: {e}')

    def handle_serve(self, options):
        """Handle profile serving."""
        if options.get('auto_sync'):
            self.handle_sync({'container': 'web_profiling'})

        profiles_dir = self.get_profiles_dir()
        if not profiles_dir.exists() or not list(profiles_dir.glob('*.html')):
            raise CommandError('No profile files found. Run "generate" first.')

        analyzer = ProfileAnalyzer(profiles_dir)
        
        # Parse limit
        limit = None if options['limit'].lower() in ['none', '0'] else int(options['limit'])
        
        # Show analysis
        analyzer.print_summary(options['app'], limit)

        # Start server
        self.start_profile_server(
            profiles_dir,
            options['port'],
            not options['no_browser'],
            analyzer,
            options['app'],
            limit,
            options['sort']
        )

    def handle_dashboard(self, options):
        """Handle dashboard generation."""
        if options.get('auto_sync'):
            self.handle_sync({'container': 'web_profiling'})

        profiles_dir = self.get_profiles_dir()
        if not profiles_dir.exists():
            raise CommandError('No profiles directory found')

        # Debug: Show what files are found
        profile_files = list(profiles_dir.glob('*.html'))
        self.stdout.write(f'📁 Profiles directory: {profiles_dir}')
        self.stdout.write(f'📄 Found {len(profile_files)} HTML files')
        
        if profile_files:
            self.stdout.write('📋 Files found:')
            for i, file in enumerate(profile_files[:10]):  # Show first 10 files
                self.stdout.write(f'  {i+1}. {file.name}')
            if len(profile_files) > 10:
                self.stdout.write(f'  ... and {len(profile_files) - 10} more files')
        else:
            self.stdout.write('❌ No HTML profile files found!')
            self.stdout.write('   Try running: uv run manage.py profile generate')
            self.stdout.write('   Or sync from Docker: uv run manage.py profile sync')
            return

        analyzer = ProfileAnalyzer(profiles_dir)
        
        # Debug: Show analysis results
        self.stdout.write(f'📊 Analyzed {len(analyzer.analyzed_profiles)} profiles')
        self.stdout.write(f'📱 App groups: {list(analyzer.app_groups.keys())}')
        
        output_path = Path(options['output']) if options['output'] else (
            profiles_dir / 'profiling_dashboard.html'
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = self.generate_dashboard_html(analyzer)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.stdout.write(
            self.style.SUCCESS(f'🎨 Dashboard generated: {output_path}')
        )
        self.stdout.write(f'🔗 Open in browser: file://{output_path.absolute()}')
        self.stdout.write('')
        self.stdout.write('💡 TIP: Profile files will open directly from the dashboard')
        self.stdout.write('   No need to run the serve command separately!')
        self.stdout.write('')
        
        try:
            webbrowser.open(f'file://{output_path.absolute()}')
            self.stdout.write('🚀 Dashboard opened in browser')
        except:
            self.stdout.write('⚠️ Could not open browser automatically')

    def handle_analyze(self, options):
        """Handle profile analysis."""
        profiles_dir = self.get_profiles_dir()
        if not profiles_dir.exists():
            raise CommandError('No profiles directory found')

        analyzer = ProfileAnalyzer(profiles_dir)
        limit = None if options['limit'].lower() in ['none', '0'] else int(options['limit'])
        analyzer.print_summary(options['app'], limit)

    def handle_clean(self, options):
        """Handle profile cleanup."""
        profiles_dir = self.get_profiles_dir()
        if not profiles_dir.exists():
            self.stdout.write('No profiles directory found')
            return

        cutoff_time = time.time() - (options['days'] * 24 * 3600)
        files_to_delete = []

        for profile_file in profiles_dir.glob('*.html'):
            if profile_file.stat().st_mtime < cutoff_time:
                files_to_delete.append(profile_file)

        if not files_to_delete:
            self.stdout.write('No old profile files to clean')
            return

        total_size = sum(f.stat().st_size for f in files_to_delete)
        
        self.stdout.write(
            f'Found {len(files_to_delete)} files older than {options["days"]} days '
            f'({total_size / (1024*1024):.1f} MB)'
        )

        if options['dry_run']:
            for file in files_to_delete:
                self.stdout.write(f'Would delete: {file.name}')
        else:
            for file in files_to_delete:
                file.unlink()
                self.stdout.write(f'Deleted: {file.name}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned {len(files_to_delete)} profile files')
            )

    def get_profiles_dir(self) -> Path:
        """Get the profiles directory path."""
        profiles_dir = Path(settings.BASE_DIR) / 'profiles'
        profiles_dir.mkdir(exist_ok=True)
        return profiles_dir

    def create_default_config(self, config_path: Path):
        """Create a default configuration file."""
        default_config = {
            "auth": {
                "login_endpoint": "/api/auth/jwt/create/",
                "email_field": "email",
                "password_field": "password"
            },
            "endpoint_groups": {
                "auth": [
                    {"endpoint": "/api/auth/users/", "method": "GET", "auth": True},
                    {"endpoint": "/api/auth/users/me/", "method": "GET", "auth": True}
                ],
                "admin": [
                    {"endpoint": "/admin/", "method": "GET", "auth": False},
                    {"endpoint": "/api/schema/", "method": "GET", "auth": False}
                ]
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

    def start_profile_server(self, profiles_dir, port, open_browser, analyzer, app_filter, limit, sort_by):
        """Start HTTP server for profiles."""
        os.chdir(profiles_dir)
        
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            self.stdout.write(f'🌐 Server started at http://localhost:{port}')
            self.stdout.write('=' * 80)
            
            # Show filtered profiles
            filtered_profiles = analyzer.get_filtered_profiles(app_filter, limit or 20, sort_by)
        
            if not filtered_profiles:
                self.stdout.write('❌ No profile files found!')
                self.stdout.write('   Try running: uv run manage.py profile generate')
                self.stdout.write('   Or sync from Docker: uv run manage.py profile sync')
                return
            
            self.stdout.write(f'📊 Found {len(filtered_profiles)} profile files')
            self.stdout.write('')
            
            # Group by app for better organization
            app_groups = {}
            for profile in filtered_profiles:
                app = profile['app']
                if app not in app_groups:
                    app_groups[app] = []
                app_groups[app].append(profile)
            
            for app, profiles in app_groups.items():
                self.stdout.write(f'📱 {app.upper()} ({len(profiles)} profiles):')
                self.stdout.write('-' * 60)
                
                for i, profile in enumerate(profiles):
                    encoded_name = quote(profile['filename'])
                    duration_str = f"{profile['duration']:.3f}s" if profile['duration'] else "N/A"
                    endpoint_display = profile['endpoint'].replace('_', '/')
                    size_mb = profile['size'] / (1024 * 1024)
                    
                    self.stdout.write(f'  {i+1:2d}. [{duration_str:>8}] {endpoint_display}')
                    self.stdout.write(f'      📅 {profile["formatted_time"]} | 💾 {size_mb:.2f} MB')
                    self.stdout.write(f'      🔗 http://localhost:{port}/{encoded_name}')
                    self.stdout.write('')
                
                self.stdout.write('')

            # Show summary statistics
            total_size = sum(p['size'] for p in filtered_profiles)
            avg_duration = sum(p['duration'] for p in filtered_profiles if p['duration']) / len([p for p in filtered_profiles if p['duration']]) if any(p['duration'] for p in filtered_profiles) else 0
            
            self.stdout.write('📈 SUMMARY:')
            self.stdout.write(f'   Total files: {len(filtered_profiles)}')
            self.stdout.write(f'   Total size: {total_size / (1024*1024):.2f} MB')
            self.stdout.write(f'   Average duration: {avg_duration:.3f}s')
            
            if analyzer.stats['fastest']:
                self.stdout.write(f'   Fastest: {analyzer.stats["fastest"]["duration"]:.3f}s - {analyzer.stats["fastest"]["endpoint"]}')
            if analyzer.stats['slowest']:
                self.stdout.write(f'   Slowest: {analyzer.stats["slowest"]["duration"]:.3f}s - {analyzer.stats["slowest"]["endpoint"]}')
            
            self.stdout.write('')
            self.stdout.write('💡 TIP: Use the dashboard command for a better UI experience')
            self.stdout.write('   uv run manage.py profile dashboard --auto-sync')
            self.stdout.write('')
            self.stdout.write('Press Ctrl+C to stop the server')

            if open_browser and filtered_profiles:
                latest_profile = filtered_profiles[0]
                encoded_name = quote(latest_profile['filename'])
                url = f'http://localhost:{port}/{encoded_name}'
                webbrowser.open(url)
                self.stdout.write(f'🚀 Opening: {latest_profile["endpoint"]}')
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                self.stdout.write('\n🛑 Server stopped')

    def generate_dashboard_html(self, analyzer):
        """Generate modern HTML dashboard."""
        stats = analyzer.stats
        app_groups = analyzer.app_groups
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyInstrument Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        :root {{
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --accent-color: #f093fb;
            --text-color: #2d3748;
            --text-light: #718096;
            --bg-color: #f7fafc;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --success-color: #48bb78;
            --warning-color: #ed8936;
            --error-color: #f56565;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: var(--text-color);
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .header {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .header h1 {{
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .header p {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 1.1rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
        }}

        .stat-label {{
            color: var(--text-light);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .controls {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}

        .search-input {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            margin-bottom: 1rem;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}

        .filter-tabs {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .filter-tab {{
            padding: 8px 16px;
            border: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-color);
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
            font-weight: 500;
        }}

        .filter-tab:hover,
        .filter-tab.active {{
            background: var(--primary-color);
            color: white;
            transform: translateY(-2px);
        }}

        .content {{
            display: grid;
            gap: 2rem;
        }}

        .app-section {{
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}

        .app-header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.3s ease;
            user-select: none;
        }}

        .app-header:hover {{
            background: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
            transform: translateY(-1px);
        }}

        .app-header.collapsed {{
            background: linear-gradient(135deg, var(--text-light), var(--primary-color));
        }}

        .collapse-icon {{
            font-size: 1.2rem;
            transition: transform 0.3s ease;
            margin-left: 8px;
            opacity: 0.8;
        }}

        .collapse-icon.collapsed {{
            transform: rotate(-90deg);
        }}

        .app-header:hover .collapse-icon {{
            opacity: 1;
        }}

        .app-title {{
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .app-count {{
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.875rem;
        }}

        .profiles-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }}

        .profiles-grid.collapsed {{
            display: none;
        }}

        .profile-card {{
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }}

        .profile-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }}

        .profile-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
            border-color: var(--primary-color);
        }}

        .profile-card:hover::before {{
            transform: scaleX(1);
        }}

        .profile-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}

        .profile-duration {{
            background: linear-gradient(135deg, var(--error-color), #ff6b6b);
            color: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .profile-endpoint {{
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 0.5rem;
            word-break: break-word;
        }}

        .profile-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: var(--text-light);
        }}

        .chart-container {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            .header h1 {{
                font-size: 2rem;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .profiles-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ PyInstrument Dashboard</h1>
            <p>Performance profiling insights for your Django application</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_files']}</div>
                <div class="stat-label">Total Profiles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_size'] / (1024*1024):.1f} MB</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_duration']:.3f}s</div>
                <div class="stat-label">Average Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['fastest']['duration'] if stats['fastest'] else 0:.3f}s</div>
                <div class="stat-label">Fastest</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['slowest']['duration'] if stats['slowest'] else 0:.3f}s</div>
                <div class="stat-label">Slowest</div>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>

        <div class="controls">
            <input type="text" class="search-input" id="searchInput" placeholder="🔍 Search profiles...">
            <div class="filter-tabs">
                <button class="filter-tab active" data-app="all">All Apps</button>
                {self._generate_app_tabs(app_groups)}
                <button class="filter-tab" onclick="expandAllSections()">Expand All</button>
                <button class="filter-tab" onclick="collapseAllSections()">Collapse All</button>
            </div>
        </div>

        <div class="content" id="content">
            {self._generate_app_sections(app_groups)}
        </div>
    </div>

    <script>
        // Initialize performance chart
        const ctx = document.getElementById('performanceChart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {list(app_groups.keys())},
                datasets: [{{
                    label: 'Profile Count',
                    data: {[len(profiles) for profiles in app_groups.values()]},
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false
                        }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Profiles by App',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }}
            }}
        }});

        // Search functionality
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const searchTerm = e.target.value.toLowerCase();
            const sections = document.querySelectorAll('.app-section');
            
            sections.forEach(section => {{
                const cards = section.querySelectorAll('.profile-card');
                let visibleCount = 0;
                
                cards.forEach(card => {{
                    const endpoint = card.querySelector('.profile-endpoint').textContent.toLowerCase();
                    const visible = endpoint.includes(searchTerm);
                    card.style.display = visible ? 'block' : 'none';
                    if (visible) visibleCount++;
                }});
                
                section.style.display = visibleCount > 0 ? 'block' : 'none';
            }});
        }});

        // Filter functionality
        document.querySelectorAll('.filter-tab').forEach(tab => {{
            tab.addEventListener('click', function() {{
                document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                const app = this.dataset.app;
                const sections = document.querySelectorAll('.app-section');
                
                sections.forEach(section => {{
                    section.style.display = app === 'all' || section.dataset.app === app ? 'block' : 'none';
                }});
            }});
        }});

        // Toggle section collapse/expand
        function toggleSection(app) {{
            const content = document.getElementById(`content-${{app}}`);
            const icon = document.getElementById(`icon-${{app}}`);
            const header = icon.parentElement.parentElement;
            
            if (content.classList.contains('collapsed')) {{
                // Expand
                content.classList.remove('collapsed');
                icon.classList.remove('collapsed');
                header.classList.remove('collapsed');
            }} else {{
                // Collapse
                content.classList.add('collapsed');
                icon.classList.add('collapsed');
                header.classList.add('collapsed');
            }}
        }}

        // Collapse all sections by default
        function collapseAllSections() {{
            const sections = document.querySelectorAll('.profiles-grid');
            const icons = document.querySelectorAll('.collapse-icon');
            const headers = document.querySelectorAll('.app-header');
            
            sections.forEach(section => section.classList.add('collapsed'));
            icons.forEach(icon => icon.classList.add('collapsed'));
            headers.forEach(header => header.classList.add('collapsed'));
        }}

        // Expand all sections
        function expandAllSections() {{
            const sections = document.querySelectorAll('.profiles-grid');
            const icons = document.querySelectorAll('.collapse-icon');
            const headers = document.querySelectorAll('.app-header');
            
            sections.forEach(section => section.classList.remove('collapsed'));
            icons.forEach(icon => icon.classList.remove('collapsed'));
            headers.forEach(header => header.classList.remove('collapsed'));
        }}

        // Profile card clicks
        function openProfile(filename) {{
            // Since dashboard is in the same directory as profiles, use relative path
            // Properly encode the filename for URLs
            const encodedFilename = encodeURIComponent(filename);
            const url = `./${{encodedFilename}}`;
            
            // Try to open the file
            const newWindow = window.open(url, '_blank');
            
            // Fallback: if the window fails to load, try alternative approaches
            if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {{
                // Try with a different approach - create a temporary link
                const link = document.createElement('a');
                link.href = url;
                link.target = '_blank';
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }}
        }}
    </script>
</body>
</html>"""

    def _generate_app_tabs(self, app_groups):
        """Generate filter tabs for apps."""
        tabs = []
        for app, profiles in app_groups.items():
            if profiles:
                tabs.append(f'<button class="filter-tab" data-app="{app}">{app.title()} ({len(profiles)})</button>')
        return ''.join(tabs)

    def _generate_app_sections(self, app_groups):
        """Generate app sections for the dashboard."""
        sections = []
        for app, profiles in app_groups.items():
            if not profiles:
                continue
                
            sections.append(f'''
            <div class="app-section" data-app="{app}">
                <div class="app-header" onclick="toggleSection('{app}')">
                    <div class="app-title">📱 {app.replace('_', ' ').title()}</div>
                    <div class="app-count">{len(profiles)} profiles <span class="collapse-icon" id="icon-{app}">▼</span></div>
                </div>
                <div class="profiles-grid" id="content-{app}">
                    {self._generate_profile_cards(profiles)}
                </div>
            </div>''')
        return ''.join(sections)

    def _generate_profile_cards(self, profiles):
        """Generate profile cards for a section."""
        cards = []
        for profile in profiles:
            duration_str = f"{profile['duration']:.3f}s" if profile['duration'] else "N/A"
            size_mb = profile['size'] / (1024 * 1024)
            endpoint_display = profile['endpoint'].replace('_', '/')
            
            # Escape the filename for JavaScript
            escaped_filename = profile['filename'].replace("'", "\\'").replace('"', '\\"')
            
            cards.append(f'''
                <div class="profile-card" onclick="openProfile('{escaped_filename}')">
                    <div class="profile-header">
                        <span class="profile-duration">{duration_str}</span>
                    </div>
                    <div class="profile-endpoint">{endpoint_display}</div>
                    <div class="profile-meta">
                        <span>📅 {profile['formatted_time']}</span>
                        <span>💾 {size_mb:.2f} MB</span>
                    </div>
                </div>''')
        return ''.join(cards)


class ProfileRunner:
    """Handles automated endpoint testing for profile generation."""
    
    def __init__(self, base_url: str, config: Dict, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.config = config
        self.email = email
        self.password = password
        self.session = None
        self.auth_token = None
        self.results = []

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'ProfileRunner/1.0'}
        )
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def authenticate(self):
        """Authenticate using configured credentials."""
        auth_config = self.config.get('auth', {})
        login_endpoint = auth_config.get('login_endpoint', '/api/auth/jwt/create/')
        
        auth_data = {
            auth_config.get('email_field', 'email'): self.email,
            auth_config.get('password_field', 'password'): self.password
        }

        try:
            async with self.session.post(
                f"{self.base_url}{login_endpoint}",
                json=auth_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access")
                    print(f"✅ Authenticated as {self.email}")
                else:
                    print(f"⚠️ Authentication failed: {response.status}")
        except Exception as e:
            print(f"⚠️ Authentication error: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    async def make_request(self, endpoint_config: Dict) -> Dict:
        """Make a single HTTP request and return results."""
        endpoint = endpoint_config["endpoint"]
        method = endpoint_config.get("method", "GET")
        needs_auth = endpoint_config.get("auth", False)
        data = endpoint_config.get("data", None)
        
        # Add profiling parameter
        if "?" in endpoint:
            endpoint += "&profile=1"
        else:
            endpoint += "?profile=1"
        
        url = urljoin(self.base_url, endpoint)
        start_time = time.time()
        
        request_kwargs = {}
        if needs_auth:
            request_kwargs["headers"] = self.get_auth_headers()
        if data and method in ["POST", "PUT", "PATCH"]:
            request_kwargs["json"] = data

        try:
            async with self.session.request(method, url, **request_kwargs) as response:
                content = await response.text()
                duration = time.time() - start_time
                
                result = {
                    'endpoint': endpoint,
                    'method': method,
                    'status': response.status,
                    'duration': duration,
                    'content_length': len(content),
                    'success': 200 <= response.status < 400,
                    'error': None,
                    'auth_used': needs_auth
                }
                
                auth_indicator = "🔐" if needs_auth else "🔓"
                print(f"{auth_indicator} {method} {endpoint} -> {response.status} ({duration:.3f}s)")
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            result = {
                'endpoint': endpoint,
                'method': method,
                'status': 0,
                'duration': duration,
                'content_length': 0,
                'success': False,
                'error': str(e),
                'auth_used': needs_auth
            }
            
            auth_indicator = "🔐" if needs_auth else "🔓"
            print(f"{auth_indicator} {method} {endpoint} -> ERROR: {e}")
            return result

    async def run_endpoint_tests(self, endpoints: List[Dict], concurrent: int = 3, requests_per_endpoint: int = 1):
        """Run tests against specified endpoints."""
        print(f"Starting profile tests with {concurrent} concurrent requests")
        print(f"Testing {len(endpoints)} endpoints, {requests_per_endpoint} requests each")
        
        tasks = []
        for endpoint_config in endpoints:
            for _ in range(requests_per_endpoint):
                task = self.make_request(endpoint_config)
                tasks.append(task)
        
        semaphore = asyncio.Semaphore(concurrent)
        
        async def limited_request(task):
            async with semaphore:
                return await task
        
        start_time = time.time()
        results = await asyncio.gather(*[limited_request(task) for task in tasks])
        total_time = time.time() - start_time
        
        self.results.extend(results)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        avg_duration = sum(r['duration'] for r in results) / len(results) if results else 0
        
        print(f"Completed {len(results)} requests in {total_time:.3f}s")
        print(f"Successful: {successful}, Failed: {failed}")
        print(f"Average duration: {avg_duration:.3f}s")
        
        return results

    def print_summary(self):
        """Print test summary."""
        if not self.results:
            print("No results to summarize")
            return
        
        print("\n" + "="*60)
        print("PROFILE TEST SUMMARY")
        print("="*60)
        
        endpoint_stats = {}
        for result in self.results:
            endpoint = result['endpoint']
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'total_duration': 0,
                    'min_duration': float('inf'),
                    'max_duration': 0,
                    'errors': []
                }
            
            stats = endpoint_stats[endpoint]
            stats['total_requests'] += 1
            stats['total_duration'] += result['duration']
            stats['min_duration'] = min(stats['min_duration'], result['duration'])
            stats['max_duration'] = max(stats['max_duration'], result['duration'])
            
            if result['success']:
                stats['successful_requests'] += 1
            else:
                stats['errors'].append(result['error'])
        
        for endpoint, stats in sorted(endpoint_stats.items()):
            avg_duration = stats['total_duration'] / stats['total_requests']
            success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            auth_used = any(r.get('auth_used', False) for r in self.results if r['endpoint'] == endpoint)
            auth_indicator = "🔐" if auth_used else "🔓"
            
            print(f"\n{auth_indicator} {endpoint}")
            print(f"   Requests: {stats['total_requests']}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Duration: {stats['min_duration']:.3f}s - {stats['max_duration']:.3f}s (avg: {avg_duration:.3f}s)")
            
            if stats['errors']:
                print(f"   Errors: {len(stats['errors'])}")
        
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r['success'])
        total_duration = sum(r['duration'] for r in self.results)
        avg_duration = total_duration / total_requests if total_requests > 0 else 0
        
        print(f"\n📊 OVERALL STATISTICS")
        print(f"   Total Requests: {total_requests}")
        print(f"   Successful: {successful_requests}")
        print(f"   Failed: {total_requests - successful_requests}")
        print(f"   Success Rate: {(successful_requests/total_requests)*100:.1f}%")
        print(f"   Average Duration: {avg_duration:.3f}s")
        print("="*60)


class ProfileAnalyzer:
    """Analyzes PyInstrument profile files."""
    
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profile_files = list(profiles_dir.glob('*.html'))
        self.analyzed_profiles = []
        self.app_groups = defaultdict(list)
        self.stats = {
            'total_files': len(self.profile_files),
            'total_size': 0,
            'avg_duration': 0,
            'fastest': None,
            'slowest': None,
            'apps': defaultdict(int)
        }
        self._analyze_profiles()

    def _analyze_profiles(self):
        """Analyze all profile files."""
        total_duration = 0
        durations = []
        
        for profile_file in self.profile_files:
            analysis = self._parse_filename(profile_file)
            if analysis:
                self.analyzed_profiles.append(analysis)
                self.app_groups[analysis['app']].append(analysis)
                self.stats['total_size'] += analysis['size']
                self.stats['apps'][analysis['app']] += 1
                
                if analysis['duration']:
                    durations.append(analysis['duration'])
                    total_duration += analysis['duration']
                    
                    if not self.stats['fastest'] or analysis['duration'] < self.stats['fastest']['duration']:
                        self.stats['fastest'] = analysis
                    if not self.stats['slowest'] or analysis['duration'] > self.stats['slowest']['duration']:
                        self.stats['slowest'] = analysis
        
        if durations:
            self.stats['avg_duration'] = total_duration / len(durations)

    def _parse_filename(self, profile_file):
        """Parse profile filename to extract metadata."""
        import re
        
        filename = profile_file.name
        
        # Try multiple patterns to match different PyInstrument filename formats
        patterns = [
            # Pattern 1: "0.123s _ endpoint_name ?profile=1 _ 1758190144.html"
            r'^(\d+\.?\d*)s\s+_\s+([^?]+)\s+\?profile=1\s+_\s+(\d+)\.html',
            # Pattern 2: "0.123s _ endpoint_name ?profile=1 1758190144.html"
            r'^(\d+\.?\d*)s\s+_\s+([^?]+)\s+\?profile=1\s+(\d+)\.html',
            # Pattern 3: "0.123s endpoint_name ?profile=1 1758190144.html"
            r'^(\d+\.?\d*)s\s+([^?]+)\s+\?profile=1\s+(\d+)\.html',
            # Pattern 4: "0.123s _ endpoint_name _ 1758190144.html"
            r'^(\d+\.?\d*)s\s+_\s+([^_]+)\s+_\s+(\d+)\.html',
            # Pattern 5: "0.123s endpoint_name 1758190144.html"
            r'^(\d+\.?\d*)s\s+([^\s]+)\s+(\d+)\.html',
            # Pattern 6: Just timestamp - "1758190144.html"
            r'^(\d+)\.html'
        ]
        
        match = None
        duration = None
        endpoint = 'unknown'
        timestamp = None
        
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, filename)
            if match:
                if i == 5:  # Pattern 6: just timestamp
                    timestamp = match.group(1)
                    # Try to extract endpoint from file content or use filename
                    endpoint = filename.replace('.html', '').replace(timestamp, '').strip('_').strip()
                    if not endpoint:
                        endpoint = 'unknown'
                else:
                    duration_str, endpoint, timestamp = match.groups()
                    duration = float(duration_str) if duration_str else None
                    endpoint = endpoint.strip('_').strip()
                break
        
        if not match:
            # Fallback: try to extract any numbers from filename
            numbers = re.findall(r'\d+\.?\d*', filename)
            if numbers:
                duration = float(numbers[0]) if '.' in numbers[0] else None
                timestamp = numbers[-1] if len(numbers) > 1 else None
            
            # Extract endpoint from filename (remove numbers and extensions)
            endpoint = re.sub(r'\d+\.?\d*', '', filename)
            endpoint = re.sub(r'\.html$', '', endpoint)
            endpoint = re.sub(r'[_\s]+', ' ', endpoint).strip()
            if not endpoint:
                endpoint = 'unknown'
        
        app = self._extract_app_from_endpoint(endpoint)
        
        try:
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Use file modification time as fallback
                dt = datetime.fromtimestamp(profile_file.stat().st_mtime)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                timestamp = int(profile_file.stat().st_mtime)
        except:
            formatted_time = 'Unknown'
            timestamp = 0
        
        size = profile_file.stat().st_size
        
        return {
            'file': profile_file,
            'filename': filename,
            'duration': duration,
            'endpoint': endpoint,
            'app': app,
            'timestamp': int(timestamp) if timestamp else 0,
            'formatted_time': formatted_time,
            'size': size,
            'size_mb': round(size / (1024 * 1024), 2)
        }

    def _extract_app_from_endpoint(self, endpoint):
        """Extract app name from endpoint."""
        endpoint_lower = endpoint.lower()
        
        if 'admin' in endpoint_lower:
            return 'admin'
        elif 'api/v1/auth' in endpoint_lower or 'auth' in endpoint_lower:
            return 'auth'
        elif 'schema' in endpoint_lower:
            return 'api_schema'
        elif 'silk' in endpoint_lower:
            return 'profiling_tools'
        elif 'rosetta' in endpoint_lower:
            return 'profiling_tools'
        elif 'static' in endpoint_lower:
            return 'static_media'
        elif 'media' in endpoint_lower:
            return 'static_media'
        elif 'flower' in endpoint_lower:
            return 'celery_monitoring'
        elif 'api/v1' in endpoint_lower:
            # Extract from URL path for API v1 endpoints
            parts = endpoint.strip('/').split('/')
            if len(parts) > 2 and parts[0] == 'api' and parts[1] == 'v1':
                return parts[2] if parts[2] else 'api'
            return 'api'
        elif endpoint_lower in ['/', '']:
            return 'health_checks'
        elif any(error in endpoint_lower for error in ['404', '500', 'error']):
            return 'error_pages'
        else:
            # Try to extract meaningful app name
            parts = endpoint.strip('/').split('/')
            if len(parts) > 1:
                return parts[1]
            return 'other'

    def get_filtered_profiles(self, app_filter=None, limit=None, sort_by='time'):
        """Get filtered and sorted profiles."""
        profiles = self.analyzed_profiles.copy()
        
        if app_filter:
            profiles = [p for p in profiles if p['app'] == app_filter]
        
        if sort_by == 'time':
            profiles.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_by == 'duration':
            profiles.sort(key=lambda x: x['duration'] or 0, reverse=True)
        elif sort_by == 'size':
            profiles.sort(key=lambda x: x['size'], reverse=True)
        
        if limit:
            profiles = profiles[:limit]
        
        return profiles

    def print_summary(self, app_filter=None, limit=None):
        """Print detailed summary."""
        filtered_profiles = self.get_filtered_profiles(app_filter, limit)
        
        print("=" * 80)
        print("📊 PYINSTRUMENT PROFILE ANALYSIS")
        print("=" * 80)
        
        if app_filter:
            print(f"🔍 Filter: {app_filter} app only")
        if limit:
            print(f"📋 Showing: {limit} most recent profiles")
        
        print(f"📁 Total files: {self.stats['total_files']}")
        print(f"💾 Total size: {self.stats['total_size'] / (1024*1024):.1f} MB")
        print(f"⏱️ Average duration: {self.stats['avg_duration']:.3f}s")
        
        if self.stats['fastest']:
            print(f"⚡ Fastest: {self.stats['fastest']['duration']:.3f}s - {self.stats['fastest']['endpoint']}")
        if self.stats['slowest']:
            print(f"🐌 Slowest: {self.stats['slowest']['duration']:.3f}s - {self.stats['slowest']['endpoint']}")
        
        print("\n📱 Apps breakdown:")
        for app, count in sorted(self.stats['apps'].items()):
            print(f"  • {app}: {count} profiles")
        
        print("=" * 80)